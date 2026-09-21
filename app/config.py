from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    bot_token: str
    archive_channel_id: str = "-1004388937618"
    mini_app_url: str = ""
    railway_public_domain: str = ""
    railway_environment_id: str = ""
    # Explicit peers observed in this deployment's Railway access logs, not a
    # claimed provider-wide CIDR. Extend only after verifying new proxy peers.
    security_trusted_proxy_ips: str = "100.64.0.1,100.64.0.4,100.64.0.5,100.64.0.6,100.64.0.8,100.64.0.10,100.64.0.12,100.64.0.13,100.64.0.16,100.64.0.17,100.64.0.18,100.64.0.19,100.64.0.21"
    webapp_version: str = "20260915-2"

    @property
    def webapp_url(self) -> str:
        base = self.mini_app_url or (f"https://{self.railway_public_domain}" if self.railway_public_domain else "")
        if not base:
            return ""
        separator = "&" if "?" in base else "?"
        return f"{base}{separator}v={self.webapp_version}"
    database_url: str = "postgresql+asyncpg://pvp:pvp@localhost:5432/pvp_chat"
    redis_url: str = "redis://localhost:6379/0"
    security_max_concurrent: int = Field(default=100, ge=1)
    security_max_uploads: int = Field(default=4, ge=1)
    db_statement_timeout_ms: int = Field(default=5000, ge=1)
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
