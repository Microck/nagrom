from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Integer,
    Text,
)
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Discord user ID
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Settings (future use)
    wants_pings: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    theme: Mapped[str] = mapped_column(Text, default="default", nullable=False)

    # Optional reputation / scoring
    reputation_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class Guild(Base):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Discord guild ID

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    required_role_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )  # role required to use bot, if any
    ping_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_thread: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    daily_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reset: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class FactCheck(Base):
    __tablename__ = "fact_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    guild_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    source_message_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )
    response_message_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )

    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    raw_response: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

class ConfigPreset(Base):
    __tablename__ = "config_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    fallback_models: Mapped[str] = mapped_column(Text, default="", nullable=False) # Comma-separated
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

class DatabaseManager:
    def __init__(self, url: str):
        self.engine = create_async_engine(url, future=True)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def init_models(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)