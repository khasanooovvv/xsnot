from sqlalchemy import text
from app.migrations import widen_telegram_ids
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.config import settings
from app.models import Base
from app import direct_models  # Register private-chat tables for create_all.

engine = create_async_engine(settings().database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db() -> None:
    async with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            await connection.execute(text("SELECT pg_advisory_xact_lock(730021)"))
        await connection.run_sync(Base.metadata.create_all)
        if connection.dialect.name == "postgresql":
            # Older private-chat deployments used *_id column names while the
            # current ORM models use user_one/user_two.  Rename in place so
            # existing chats remain available after an upgrade.
            await connection.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='direct_chats' AND column_name='user_one_id')
                       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='direct_chats' AND column_name='user_one') THEN
                        ALTER TABLE direct_chats RENAME COLUMN user_one_id TO user_one;
                    END IF;
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='direct_chats' AND column_name='user_two_id')
                       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='direct_chats' AND column_name='user_two') THEN
                        ALTER TABLE direct_chats RENAME COLUMN user_two_id TO user_two;
                    END IF;
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='direct_chats' AND column_name='updated_at')
                       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='direct_chats' AND column_name='created_at') THEN
                        ALTER TABLE direct_chats RENAME COLUMN updated_at TO created_at;
                    END IF;
                END $$;
            """))
            await connection.execute(text("ALTER TABLE direct_chats ADD COLUMN IF NOT EXISTS last_message_at TIMESTAMPTZ"))
            await connection.execute(text("ALTER TABLE direct_chats ADD COLUMN IF NOT EXISTS revision BIGINT NOT NULL DEFAULT 0"))
            await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS silver_verified BOOLEAN NOT NULL DEFAULT FALSE"))
            await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS muted_until TIMESTAMPTZ"))
            await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS gender VARCHAR(16)"))
            await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS app_username VARCHAR(24)"))
            await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS short_username_access BOOLEAN NOT NULL DEFAULT FALSE"))
            await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS short_username_min_length INTEGER NOT NULL DEFAULT 0"))
            await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio VARCHAR(300)"))
            await connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_app_username ON users (app_username)"))
            await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS archive_consent_at TIMESTAMPTZ"))
            await connection.execute(text("ALTER TABLE matches ADD COLUMN IF NOT EXISTS archive_consent BOOLEAN NOT NULL DEFAULT FALSE"))
            await connection.execute(text("ALTER TABLE match_queue ADD COLUMN IF NOT EXISTS archive_consent BOOLEAN NOT NULL DEFAULT FALSE"))
            await connection.execute(text("ALTER TABLE referral_history ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE"))
            await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_referral_history_referrer_active ON referral_history (referrer_id, active)"))
            await connection.execute(text("ALTER TABLE mini_messages ADD COLUMN IF NOT EXISTS image_data BYTEA"))
            await connection.execute(text("ALTER TABLE mini_messages ADD COLUMN IF NOT EXISTS image_type VARCHAR(64)"))
            await connection.execute(text("ALTER TABLE mini_messages ADD COLUMN IF NOT EXISTS image_name VARCHAR(255)"))
            await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_mini_messages_match_id_id ON mini_messages (match_id, id)"))
            await connection.run_sync(widen_telegram_ids)
