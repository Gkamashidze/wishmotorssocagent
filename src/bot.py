from __future__ import annotations
import asyncio
import logging
import os
import time
from datetime import datetime, timezone as _tz
from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from src.config import load_config, Config
from src.database import get_last_category, set_last_category, save_post, mark_published, mark_skipped
from src.content import next_category, build_text_prompt, build_image_prompt, extract_parts_from_text, clean_text, CONTACT_INFO
from src.gemini_client import generate_post_text, generate_post_image
from src.facebook_client import publish_to_facebook, delete_facebook_post

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# In-memory store for pending approvals: post_id_str → post data + timestamp
_pending: dict[str, dict[str, Any]] = {}
_AUTO_PUBLISH_TTL = 24 * 3600  # 24 hours — auto-publish if no user action
_PENDING_TTL = 48 * 3600       # 48 hours — hard expiry after auto-publish window

# In-memory store for published posts: fb_post_id → {text, image_path, _ts}
# Kept for 24h after publish to allow restore after deletion
_published: dict[str, dict[str, Any]] = {}

# Rate limiting for /generate: chat_id → last call timestamp
_last_generate: dict[int, float] = {}
_GENERATE_COOLDOWN = 30  # 30 seconds between manual triggers

# Active generation task (only one at a time)
_active_generation: asyncio.Task | None = None


def _keyboard(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ გამოაქვეყნე", callback_data=f"publish_{post_id}"),
        InlineKeyboardButton("🔄 თავიდან", callback_data=f"regenerate_{post_id}"),
    ]])


def _retry_keyboard(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔁 ხელახლა სცადე", callback_data=f"publish_{post_id}"),
    ]])


def _delete_keyboard(fb_post_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑️ პოსტის წაშლა", callback_data=f"delete_{fb_post_id}"),
    ]])


def _restore_keyboard(fb_post_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("♻️ აღდგენა (24 სთ)", callback_data=f"restore_{fb_post_id}"),
    ]])


async def _generate_post(config: Config, category: str) -> dict[str, Any]:
    """Generate text + image for the given category. Returns post data dict.

    All blocking I/O (Gemini SDK, requests, SQLite) runs in a thread pool so
    the Telegram event loop is never blocked.
    """
    raw_text = await asyncio.to_thread(
        generate_post_text, build_text_prompt(category), config.gemini_api_key
    )
    part_en, part_ka = extract_parts_from_text(raw_text)
    post_text = clean_text(raw_text)
    full_text = post_text + CONTACT_INFO
    image_path = await asyncio.to_thread(
        generate_post_image,
        build_image_prompt(part_en, part_ka),
        config.gemini_api_key,
        part_en=part_en,
        part_ka=part_ka,
    )
    post_id = await asyncio.to_thread(save_post, category, full_text, image_path)
    return {"post_id": post_id, "text": full_text, "image_path": image_path, "category": category}


async def _send_for_approval(bot, chat_id: int, post_data: dict[str, Any]) -> None:
    """Send generated post to Telegram with approve/regenerate buttons."""
    _pending[str(post_data["post_id"])] = {**post_data, "_ts": time.time()}
    with open(post_data["image_path"], "rb") as img:
        await bot.send_photo(
            chat_id=chat_id,
            photo=img,
            caption=post_data["text"][:1024],
            reply_markup=_keyboard(post_data["post_id"]),
        )
    if len(post_data["text"]) > 1024:
        await bot.send_message(chat_id=chat_id, text=f"📝 სრული ტექსტი:\n\n{post_data['text']}")


async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/generate command — manually trigger post generation."""
    global _active_generation
    config: Config = context.bot_data["config"]
    if update.effective_chat.id != config.telegram_chat_id:
        return  # ignore requests from other chats

    # Rate limit: prevent accidental double-triggers
    now = time.time()
    last = _last_generate.get(update.effective_chat.id, 0.0)
    if now - last < _GENERATE_COOLDOWN:
        remaining = int(_GENERATE_COOLDOWN - (now - last))
        await update.message.reply_text(f"⏳ გთხოვ დაელოდო {remaining} წამი.")
        return
    _last_generate[update.effective_chat.id] = now

    category = next_category(await asyncio.to_thread(get_last_category))
    await update.message.reply_text(f"⏳ ვქმნი პოსტს ({category})... (1–2 წუთი)\n\n/stop — გასაჩერებლად")

    async def _run():
        global _active_generation
        try:
            post_data = await _generate_post(config, category)
            post_data["config"] = config
            await _send_for_approval(context.bot, config.telegram_chat_id, post_data)
        except asyncio.CancelledError:
            await context.bot.send_message(chat_id=config.telegram_chat_id, text="🛑 გენერაცია გაჩერდა.")
        except Exception as exc:
            logger.error("Manual generate failed: %s", exc)
            await context.bot.send_message(chat_id=config.telegram_chat_id, text=f"❌ შეცდომა:\n{str(exc)[:300]}")
        finally:
            _active_generation = None

    _active_generation = asyncio.create_task(_run())


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stop command — cancel active generation."""
    global _active_generation
    config: Config = context.bot_data["config"]
    if update.effective_chat.id != config.telegram_chat_id:
        return

    if _active_generation and not _active_generation.done():
        _active_generation.cancel()
        await update.message.reply_text("🛑 გენერაცია გაჩერდა.")
    else:
        await update.message.reply_text("ℹ️ გენერაცია არ მიმდინარეობს.")


async def scheduled_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered by scheduler — generate new post and send to Telegram."""
    config: Config = context.bot_data["config"]
    category = next_category(await asyncio.to_thread(get_last_category))
    logger.info("Scheduled post triggered: category=%s", category)
    try:
        await context.bot.send_message(
            chat_id=config.telegram_chat_id,
            text=f"⏳ ვქმნი პოსტს ({category})... (1–2 წუთი)",
        )
        post_data = await _generate_post(config, category)
        post_data["config"] = config
        await _send_for_approval(context.bot, config.telegram_chat_id, post_data)
    except Exception as exc:
        logger.error("Scheduled post failed: %s", exc)
        await context.bot.send_message(
            chat_id=config.telegram_chat_id,
            text=f"❌ შეცდომა პოსტის შექმნისას:\n{str(exc)[:300]}",
        )


async def auto_publish_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs every 30 minutes — auto-publishes posts that have been pending for over 24 hours."""
    config: Config = context.bot_data["config"]
    now = time.time()
    expired = [
        (pid, data) for pid, data in list(_pending.items())
        if now - data.get("_ts", 0) >= _AUTO_PUBLISH_TTL
    ]
    for post_id_str, pending in expired:
        logger.info("Auto-publishing post %s (pending >24h)", post_id_str)
        await context.bot.send_message(
            chat_id=config.telegram_chat_id,
            text="⏰ 24 საათი გავიდა — ავტომატურად ვაქვეყნებ პოსტს...",
        )
        try:
            result = await asyncio.to_thread(
                publish_to_facebook,
                page_id=config.fb_page_id,
                page_access_token=config.fb_page_access_token,
                message=pending["text"],
                image_path=pending["image_path"],
            )
            await asyncio.to_thread(mark_published, pending["post_id"])
            await asyncio.to_thread(set_last_category, pending["category"])
            _published[result["page_post_id"]] = {
                "text": pending["text"],
                "image_path": pending["image_path"],
                "_ts": time.time(),
            }
            _pending.pop(post_id_str, None)
            page_line = "✅ ავტომატურად გამოქვეყნდა"
            if result.get("page_url"):
                page_line += f"\n🔗 {result['page_url']}"
            await context.bot.send_message(
                chat_id=config.telegram_chat_id,
                text=page_line,
                reply_markup=_delete_keyboard(result["page_post_id"]),
            )
        except Exception as exc:
            logger.error("Auto-publish failed for post %s: %s", post_id_str, exc)
            await context.bot.send_message(
                chat_id=config.telegram_chat_id,
                text=f"❌ ავტომატური გამოქვეყნება ვერ მოხდა.\n{str(exc)[:300]}",
                reply_markup=_retry_keyboard(pending["post_id"]),
            )


async def cleanup_published(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs every hour — removes published post cache entries older than 24h and deletes their images."""
    cutoff = time.time() - 24 * 3600
    expired = [pid for pid, data in list(_published.items()) if data.get("_ts", 0) < cutoff]
    for pid in expired:
        data = _published.pop(pid)
        try:
            os.remove(data["image_path"])
        except OSError:
            pass
        logger.info("Cleaned up published post cache: %s", pid)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ✅ გამოაქვეყნე or 🔄 თავიდან button presses."""
    query = update.callback_query
    await query.answer()

    # Guard against malformed callback data
    parts = query.data.split("_", 1)
    if len(parts) != 2:
        logger.warning("Unexpected callback data: %r", query.data)
        return
    action, post_id_str = parts

    # Delete action does not use _pending — handle it before the pending check
    if action == "delete":
        config: Config = context.bot_data["config"]
        await query.edit_message_reply_markup(reply_markup=None)
        try:
            deleted = await asyncio.to_thread(
                delete_facebook_post, post_id_str, config.fb_page_access_token
            )
            if deleted:
                restore_markup = None
                if post_id_str in _published:
                    restore_markup = _restore_keyboard(post_id_str)
                await context.bot.send_message(
                    chat_id=config.telegram_chat_id,
                    text="🗑️ პოსტი წაიშალა Facebook გვერდიდან.",
                    reply_markup=restore_markup,
                )
            else:
                await context.bot.send_message(
                    chat_id=config.telegram_chat_id, text="⚠️ პოსტი ვერ წაიშალა — შეიძლება უკვე წაშლილია."
                )
        except Exception as exc:
            logger.error("Facebook delete failed: %s", exc)
            await context.bot.send_message(
                chat_id=config.telegram_chat_id,
                text=f"❌ წაშლა ვერ მოხდა.\n{str(exc)[:300]}",
            )
        return

    # Restore action — republish deleted post from _published cache
    if action == "restore":
        config: Config = context.bot_data["config"]
        saved = _published.get(post_id_str)
        await query.edit_message_reply_markup(reply_markup=None)
        if not saved:
            await context.bot.send_message(
                chat_id=config.telegram_chat_id,
                text="⏰ 24 საათი გავიდა — აღდგენა შეუძლებელია.",
            )
            return
        await context.bot.send_message(chat_id=config.telegram_chat_id, text="♻️ ვაღდგენ პოსტს Facebook-ზე...")
        try:
            result = await asyncio.to_thread(
                publish_to_facebook,
                page_id=config.fb_page_id,
                page_access_token=config.fb_page_access_token,
                message=saved["text"],
                image_path=saved["image_path"],
            )
            _published.pop(post_id_str, None)
            _published[result["page_post_id"]] = {
                "text": saved["text"],
                "image_path": saved["image_path"],
                "_ts": time.time(),
            }
            page_line = "✅ პოსტი აღდგა Facebook გვერდზე"
            if result.get("page_url"):
                page_line += f"\n🔗 {result['page_url']}"
            await context.bot.send_message(
                chat_id=config.telegram_chat_id,
                text=page_line,
                reply_markup=_delete_keyboard(result["page_post_id"]),
            )
        except Exception as exc:
            logger.error("Restore failed: %s", exc)
            await context.bot.send_message(
                chat_id=config.telegram_chat_id,
                text=f"❌ აღდგენა ვერ მოხდა.\n{str(exc)[:300]}",
            )
        return

    pending = _pending.get(post_id_str)

    # Expire stale pending entries (older than _PENDING_TTL)
    if pending and time.time() - pending.get("_ts", 0) > _PENDING_TTL:
        _pending.pop(post_id_str, None)
        pending = None

    if not pending:
        await query.edit_message_caption(caption="⏰ ვადა გავიდა. ახალი ავტომატურად მოვა.")
        return

    config: Config = pending["config"]

    if action == "publish":
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(chat_id=config.telegram_chat_id, text="📤 ვაქვეყნებ Facebook-ზე...")
        try:
            result = await asyncio.to_thread(
                publish_to_facebook,
                page_id=config.fb_page_id,
                page_access_token=config.fb_page_access_token,
                message=pending["text"],
                image_path=pending["image_path"],
            )
            await asyncio.to_thread(mark_published, pending["post_id"])
            await asyncio.to_thread(set_last_category, pending["category"])
            _published[result["page_post_id"]] = {
                "text": pending["text"],
                "image_path": pending["image_path"],
                "_ts": time.time(),
            }
            _pending.pop(post_id_str, None)

            page_line = "✅ გვერდი: გამოქვეყნდა"
            if result.get("page_url"):
                page_line += f"\n🔗 {result['page_url']}"
            await context.bot.send_message(
                chat_id=config.telegram_chat_id,
                text=page_line,
                reply_markup=_delete_keyboard(result["page_post_id"]),
            )
        except Exception as exc:
            logger.error("Facebook publish failed: %s", exc)
            await context.bot.send_message(
                chat_id=config.telegram_chat_id,
                text=f"❌ Facebook-ზე ვერ გამოქვეყნდა.\n\nშეცდომა: {str(exc)[:400]}",
                reply_markup=_retry_keyboard(pending["post_id"]),
            )

    elif action == "regenerate":
        category = pending["category"]
        old_image = pending.get("image_path")
        await asyncio.to_thread(mark_skipped, pending["post_id"])
        _pending.pop(post_id_str, None)
        if old_image:
            try:
                os.remove(old_image)
            except OSError:
                pass
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(chat_id=config.telegram_chat_id, text="🔄 ვქმნი ახალ ვარიანტს...")
        try:
            post_data = await _generate_post(config, category)
            post_data["config"] = config
            await _send_for_approval(context.bot, config.telegram_chat_id, post_data)
        except Exception as exc:
            logger.error("Regeneration failed: %s", exc)
            await context.bot.send_message(
                chat_id=config.telegram_chat_id,
                text=f"❌ შეცდომა. სცადე ხელახლა.\n{str(exc)[:300]}",
            )


def main() -> None:
    config = load_config()
    app = Application.builder().token(config.telegram_bot_token).build()
    app.bot_data["config"] = config

    # Monday=0, Thursday=3 at 10:00 Tbilisi (UTC+4) = 06:00 UTC
    app.job_queue.run_daily(
        callback=scheduled_post,
        time=datetime.now(_tz.utc).replace(hour=6, minute=0, second=0, microsecond=0).timetz(),
        days=(0, 3),
        name="wish_motors_post",
        job_kwargs={"misfire_grace_time": 60},
    )

    app.job_queue.run_repeating(
        callback=auto_publish_check,
        interval=1800,  # check every 30 minutes
        first=60,
        name="auto_publish_check",
    )

    app.job_queue.run_repeating(
        callback=cleanup_published,
        interval=3600,  # check every hour
        first=120,
        name="cleanup_published",
    )

    app.add_handler(CommandHandler("generate", generate_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Wish Motors bot started. Posts scheduled: Mon & Thu 10:00 GEST.")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
