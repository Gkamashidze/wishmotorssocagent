from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)


def _resolve_db_url() -> str:
    if url := os.environ.get("DATABASE_URL"):
        return url
    if os.path.isdir("/data"):
        return "sqlite:////data/wishmotors.db"
    logger.warning(
        "No persistent storage found — using /tmp/wishmotors.db. "
        "Data will be lost on restart. Mount a Railway Volume at /data to persist."
    )
    return "sqlite:////tmp/wishmotors.db"


engine = create_engine(_resolve_db_url(), connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False)
    text_content = Column(Text, nullable=False)
    image_path = Column(String(500))
    status = Column(String(20), default="pending")  # pending, published, skipped
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    published_at = Column(DateTime, nullable=True)


class AppState(Base):
    __tablename__ = "app_state"
    key = Column(String(50), primary_key=True)
    value = Column(String(500))


Base.metadata.create_all(engine)


def get_last_category() -> str:
    with Session() as session:
        state = session.get(AppState, "last_category")
        return state.value if state else "electrical"  # first post will be maintenance


def set_last_category(category: str) -> None:
    with Session() as session:
        state = session.get(AppState, "last_category")
        if state:
            state.value = category
        else:
            session.add(AppState(key="last_category", value=category))
        session.commit()


def save_post(category: str, text: str, image_path: str) -> int:
    with Session() as session:
        post = Post(category=category, text_content=text, image_path=image_path)
        session.add(post)
        session.commit()
        logger.info("Post saved: id=%d category=%s", post.id, category)
        return post.id


def mark_published(post_id: int) -> None:
    with Session() as session:
        post = session.get(Post, post_id)
        if post:
            post.status = "published"
            post.published_at = datetime.now(timezone.utc)
            session.commit()


def mark_skipped(post_id: int) -> None:
    with Session() as session:
        post = session.get(Post, post_id)
        if post:
            post.status = "skipped"
            session.commit()


def get_used_topics(category: str, limit: int = 5) -> list[str]:
    with Session() as session:
        state = session.get(AppState, f"used_topics_{category}")
        if not state:
            return []
        try:
            return json.loads(state.value)[:limit]
        except (json.JSONDecodeError, TypeError):
            return []


def save_used_topic(category: str, topic_ka: str, limit: int = 5) -> None:
    with Session() as session:
        key = f"used_topics_{category}"
        state = session.get(AppState, key)
        topics: list[str] = []
        if state:
            try:
                topics = json.loads(state.value)
            except (json.JSONDecodeError, TypeError):
                topics = []
        if topic_ka not in topics:
            topics.insert(0, topic_ka)
        topics = topics[:limit]
        value = json.dumps(topics, ensure_ascii=False)
        if state:
            state.value = value
        else:
            session.add(AppState(key=key, value=value))
        session.commit()


def get_last_pending_post() -> dict | None:
    """Return the most recent pending post, or None if there is none."""
    with Session() as session:
        post = (
            session.query(Post)
            .filter_by(status="pending")
            .order_by(Post.id.desc())
            .first()
        )
        if not post:
            return None
        return {
            "post_id": post.id,
            "text": post.text_content,
            "image_path": post.image_path,
            "category": post.category,
        }
