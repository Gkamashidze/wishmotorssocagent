from __future__ import annotations
import logging
import os
from datetime import time, timezone
from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from src.config import load_config, Config
from src.database import get_last_category, set_last_category, save_post, mark_published, mark_skipped
from src.content import next_category, build_text_prompt, build_image_prompt, extract_parts_from_text, clean_text, CONTACT_INFO
from src.gemini_client import generate_post_text, generate_post_image
from src.facebook_client import publish_to_facebook

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# In-memory store for pending approvals: post_id_str → post data
_pending: dict[str, dict[str, Any]] = {}


def _keyboard(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ გამოაქვეყნე", callback_data=f"publish_{post_id}"),
        InlineKeyboardButton("🔄 თავიდან", callback_data=f"regenerate_{post_id}"),
    ]])


async def _generate_post(config: Config, category: str) -> dict[str, Any]:
    """Generate text + image for the given category. Returns post data dict."""
    raw_text = generate_post_text(build_text_prompt(category), config.gemini_api_key)
    part_en, part_ka = extract_parts_from_text(raw_text)
    post_text = clean_text(raw_text)
    full_text = post_text + CONTACT_INFO
    image_path = generate_post_image(build_image_prompt(part_en, part_ka), config.gemini_api_key)
    post_id = save_post(category, full_text, image_path)
    return {"post_id": post_id, "text": full_text, "image_path": image_path, "category": category}


async def _send_for_approval(bot, chat_id: int, post_data: dict[str, Any]) -> None:
    """Send generated post to Telegram with approve/regenerate buttons."""
    _pending[str(post_data["post_id"])] = post_data
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
    config: Config = context.bot_data["config"]
    if update.effective_chat.id != config.telegram_chat_id:
        return  # ignore requests from other chats
    category = next_category(get_last_category())
    await update.message.reply_text(f"⏳ ვქმნი პოსტს ({category})... (1–2 წუთი)")
    try:
        post_data = await _generate_post(config, category)
        post_data["config"] = config
        await _send_for_approval(context.bot, config.telegram_chat_id, post_data)
    except Exception as exc:
        logger.error("Manual generate failed: %s", exc)
        await update.message.reply_text(f"❌ შეცდომა:\n{str(exc)[:300]}")


async def scheduled_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered by scheduler — generate new post and send to Telegram."""
    config: Config = context.bot_data["config"]
    category = next_category(get_last_category())
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


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ✅ გამოაქვეყნე or 🔄 თავიდან button presses."""
    query = update.callback_query
    await query.answer()

    action, post_id_str = query.data.split("_", 1)
    pending = _pending.get(post_id_str)

    if not pending:
        await query.edit_message_caption(caption="⏰ ვადა გავიდა. ახალი ავტომატურად მოვა.")
        return

    config: Config = pending["config"]

    if action == "publish":
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(chat_id=config.telegram_chat_id, text="📤 ვქვეყნებ Facebook-ზე...")
        try:
            publish_to_facebook(
                page_id=config.fb_page_id,
                group_id=config.fb_group_id,
                access_token=config.fb_page_access_token,
                message=pending["text"],
                image_path=pending["image_path"],
            )
            mark_published(pending["post_id"])
            set_last_category(pending["category"])
            _pending.pop(post_id_str, None)
            try:
                os.remove(pending["image_path"])
            except OSError:
                pass
            await context.bot.send_message(
                chat_id=config.telegram_chat_id,
                text="✅ გამოქვეყნდა! Facebook გვერდსა და ჯგუფში.",
            )
        except Exception as exc:
            logger.error("Facebook publish failed: %s", exc)
            await context.bot.send_message(
                chat_id=config.telegram_chat_id,
                text=f"❌ Facebook-ზე ვერ გამოქვეყნდა. შეამოწმე API token.\n{str(exc)[:300]}",
            )

    elif action == "regenerate":
        category = pending["category"]
        old_image = pending.get("image_path")
        mark_skipped(pending["post_id"])
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
        time=time(6, 0, 0, tzinfo=timezone.utc),
        days=(0, 3),
        name="wish_motors_post",
    )

    app.add_handler(CommandHandler("generate", generate_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Wish Motors bot started. Posts scheduled: Mon & Thu 10:00 GEST.")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
