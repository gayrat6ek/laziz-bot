from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_CHAT_ID: int
    DATABASE_PATH: str = "bot_database.db"
    PROXY_URL: Optional[str] = None  # Optional: socks5://user:pass@host:port or http://host:port
    CHANNEL_CHAT_ID: Optional[int] = None  # Channel to send test results to

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()

