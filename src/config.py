from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    gemini_api_key: str
    telegram_bot_token: str
    telegram_chat_id: int
    fb_page_access_token: str
    fb_page_id: str


def load_config() -> Config:
    """Load and validate all required environment variables. Fails fast if any are missing."""
    required = [
        "GEMINI_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "FB_PAGE_ACCESS_TOKEN",
        "FB_PAGE_ID",
    ]
    missing = [var for var in required if not os.environ.get(var)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    return Config(
        gemini_api_key=os.environ["GEMINI_API_KEY"],
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=int(os.environ["TELEGRAM_CHAT_ID"]),
        fb_page_access_token=os.environ["FB_PAGE_ACCESS_TOKEN"],
        fb_page_id=os.environ["FB_PAGE_ID"],
    )
