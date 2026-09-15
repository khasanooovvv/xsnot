from sqlalchemy import text
from app.migrations import widen_telegram_ids
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.config import settings
from app.models import Base

engine = create_async_engine(settings().database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db() -> None:
    async with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            await connection.execute(text("SELECT pg_advisory_xact_lock(730021)"))
        await connection.run_sync(Base.metadata.create_all)
        if connection.dialect.name == "postgresql":
            await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS silver_verified BOOLEAN NOT NULL DEFAULT FALSE"))
            await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS muted_until TIMESTAMPTZ"))
            await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS archive_consent_at TIMESTAMPTZ"))
            await connection.execute(text("ALTER TABLE matches ADD COLUMN IF NOT EXISTS archive_consent BOOLEAN NOT NULL DEFAULT FALSE"))
            await connection.execute(text("ALTER TABLE match_queue ADD COLUMN IF NOT EXISTS archive_consent BOOLEAN NOT NULL DEFAULT FALSE"))
            await connection.run_sync(widen_telegram_ids)
