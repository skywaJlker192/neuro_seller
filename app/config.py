from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    BOT_TOKEN: str
    MANAGER_CHAT_ID: int | str

    # YandexGPT настройки
    YANDEX_API_KEY: str
    YANDEX_FOLDER_ID: str
    YANDEX_MODEL: str = "yandexgpt-lite"

    # БД
    DB_URL: str = "sqlite+aiosqlite:///./bot.db"
    MAX_CONTEXT_MESSAGES: int = 12

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
