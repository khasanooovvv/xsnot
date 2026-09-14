from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    bot_token: str
    archive_channel_id: str = "-1004388937618"
    mini_app_url: str = ""
    railway_public_domain: str = ""

    @property
    def webapp_url(self) -> str:
        return self.mini_app_url or (f"https://{self.railway_public_domain}" if self.railway_public_domain else "")
    database_url: str = "postgresql+asyncpg://pvp:pvp@localhost:5432/pvp_chat"
    redis_url: str = "redis://localhost:6379/0"
    admin_username: str = "admin"
    admin_password: str = "change-this-now"
    public_bot_username: str = "YourBotUsername"
    default_avatar_url: str = "https://api.dicebear.com/9.x/initials/png?seed=Player"
    terms_version: str = "2026-09-13"
    min_age: int = 18
    referral_daily_share_limit: int = 15
    silver_referral_daily_share_limit: int = 30
    premium_referrals: int = 5
    gold_referrals: int = 50
    reward_days: int = 30

@lru_cache
def settings() -> Settings:
    return Settings()
