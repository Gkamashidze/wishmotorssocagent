from __future__ import annotations
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

engine = create_engine("sqlite:////tmp/wishmotors.db", connect_args={"check_same_thread": False})
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
