import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from loguru import logger

from app.config import settings
from app.db.database import init_db
from app.handlers import start
from app.handlers import messages
from app.handlers import media
from app.handlers import admin
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

async def main():
    logger.info("Запуск бота...")
    await init_db()
    logger.info("База данных инициализирована")

    proxy_server = TelegramAPIServer.from_base("https://bot.qninq.cn")
    session = AiohttpSession(api=proxy_server)

    bot = Bot(
        token=settings.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()
    dp.include_routers(start.router, messages.router, media.router, admin.router)

    logger.info("✅ Бот запущен через публичный прокси!")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
