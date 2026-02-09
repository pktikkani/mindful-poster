"""Database for tracking generated posts. Supports SQLite (local) and Neon Postgres (production).

Set DATABASE_URL in .env to use Postgres:
  DATABASE_URL=postgresql://user:pass@your-host.neon.tech/neondb?sslmode=require

Leave DATABASE_URL empty to use local SQLite (data/posts.db).
"""
from dotenv import load_dotenv
load_dotenv()
import os
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, Text, select
from sqlalchemy.orm import sessionmaker, declarative_base

# ─── Post Status Enum ────────────────────────────────────────────────────────


class PostStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FAILED = "failed"


# ─── Database Engine Setup ───────────────────────────────────────────────────

Base = declarative_base()


def _get_engine():
    """Create an engine based on DATABASE_URL (Postgres) or fallback to SQLite."""
    database_url = os.environ.get("DATABASE_URL", "")

    if database_url:
        # Neon/Railway sometimes give postgres:// but SQLAlchemy needs postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return create_engine(database_url, pool_pre_ping=True)
    else:
        # Local SQLite
        db_path = Path(__file__).parent.parent / "data" / "posts.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


engine = _get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ─── SQLAlchemy Model ────────────────────────────────────────────────────────


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    theme_id = Column(String, nullable=False)
    theme = Column(String, nullable=False)
    hook = Column(Text, nullable=False)
    caption = Column(Text, nullable=False)
    hashtags = Column(Text, nullable=False)
    alt_text = Column(Text, default="")
    image_prompt = Column(Text, default="")
    cta = Column(Text, default="")
    status = Column(String, nullable=False, default="draft")
    approval_token = Column(String, unique=True)
    created_at = Column(String, nullable=False)
    approved_at = Column(String, nullable=True)
    published_at = Column(String, nullable=True)
    instagram_post_id = Column(String, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    metadata_ = Column("metadata", Text, default="{}")


# Create tables on import
Base.metadata.create_all(bind=engine)


# ─── FastAPI Dependency ──────────────────────────────────────────────────────


def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Helper: row to dict ────────────────────────────────────────────────────


def _post_to_dict(post: Post) -> dict:
    """Convert a Post ORM object to a plain dict."""
    return {
        "id": post.id,
        "theme_id": post.theme_id,
        "theme": post.theme,
        "hook": post.hook,
        "caption": post.caption,
        "hashtags": post.hashtags,
        "alt_text": post.alt_text,
        "image_prompt": post.image_prompt,
        "cta": post.cta,
        "status": post.status,
        "approval_token": post.approval_token,
        "created_at": post.created_at,
        "approved_at": post.approved_at,
        "published_at": post.published_at,
        "instagram_post_id": post.instagram_post_id,
        "rejection_reason": post.rejection_reason,
        "metadata": post.metadata_,
    }


# ─── CRUD Operations ────────────────────────────────────────────────────────


def create_post(
    theme_id: str,
    theme: str,
    hook: str,
    caption: str,
    hashtags: str,
    alt_text: str = "",
    image_prompt: str = "",
    cta: str = "",
    approval_token: str = "",
    metadata: str = "{}",
) -> int:
    """Insert a new post and return its ID."""
    db = SessionLocal()
    try:
        post = Post(
            theme_id=theme_id,
            theme=theme,
            hook=hook,
            caption=caption,
            hashtags=hashtags,
            alt_text=alt_text,
            image_prompt=image_prompt,
            cta=cta,
            status=PostStatus.PENDING_APPROVAL,
            approval_token=approval_token,
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata_=metadata,
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return post.id
    finally:
        db.close()


def get_post(post_id: int) -> dict | None:
    db = SessionLocal()
    try:
        post = db.execute(select(Post).filter(Post.id == post_id)).scalar_one_or_none()
        return _post_to_dict(post) if post else None
    finally:
        db.close()


def get_post_by_token(token: str) -> dict | None:
    db = SessionLocal()
    try:
        post = db.execute(select(Post).filter(Post.approval_token == token)).scalar_one_or_none()
        return _post_to_dict(post) if post else None
    finally:
        db.close()


def update_post_status(
    post_id: int,
    status: PostStatus,
    rejection_reason: str | None = None,
    instagram_post_id: str | None = None,
):
    db = SessionLocal()
    try:
        post = db.execute(select(Post).filter(Post.id == post_id)).scalar_one_or_none()
        if not post:
            return

        now = datetime.now(timezone.utc).isoformat()
        post.status = status

        if status == PostStatus.APPROVED:
            post.approved_at = now
        elif status == PostStatus.PUBLISHED:
            post.published_at = now
            post.instagram_post_id = instagram_post_id
        elif status == PostStatus.REJECTED:
            post.rejection_reason = rejection_reason

        db.commit()
    finally:
        db.close()


def update_post_metadata(post_id: int, metadata: str):
    db = SessionLocal()
    try:
        post = db.execute(select(Post).filter(Post.id == post_id)).scalar_one_or_none()
        if post:
            post.metadata_ = metadata
            db.commit()
    finally:
        db.close()


def get_recent_posts(limit: int = 20) -> list[dict]:
    db = SessionLocal()
    try:
        posts = db.execute(
            select(Post).order_by(Post.created_at.desc()).limit(limit)
        ).scalars().all()
        return [_post_to_dict(p) for p in posts]
    finally:
        db.close()


def get_used_theme_ids(days: int = 30) -> list[str]:
    db = SessionLocal()
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        posts = db.execute(
            select(Post.theme_id).filter(Post.created_at >= cutoff).distinct()
        ).scalars().all()
        return list(posts)
    finally:
        db.close()