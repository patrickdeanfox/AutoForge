"""SQLAlchemy async engine setup and declarative Base for AutoForge."""

import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ============================================================
# CONFIG
# ============================================================
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://autoforge:autoforge@localhost:5432/autoforge",
)

# ============================================================
# ENGINE + SESSION
# ============================================================
engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal: sessionmaker = sessionmaker(  # type: ignore[type-arg]
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all AutoForge ORM models."""

    pass
