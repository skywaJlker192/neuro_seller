import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from loguru import logger

# Явно импортируем каждый модуль
from app.handlers import start
from app.handlers import messages
from app.handlers import media
from app.handlers import admin

from app.config import settings
from app.db.database import init_db


# Рабочие прокси (попробуй по очереди если один не работает):
PROXY_URLS = [
    "http://37.49.224.15:3128",
    "http://47.84.204.82:80",
    "http://85.192.28.62:7443",
    "http://185.200.188.234:10001",
]


async def main():
    # Инициализация базы данных
    await init_db()
    logger.info("База данных инициализирована")

    # Пробуем прокси по очереди
    working_session = None
    working_proxy = None

    logger.info("Проверка прокси...")

    for proxy_url in PROXY_URLS:
        try:
            # Создаем сессию с прокси
            session = AiohttpSession(proxy=proxy_url)

            # Создаем бота
            bot = Bot(
                token=settings.BOT_TOKEN,
                session=session,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            # Проверяем соединение
            await bot.me()

            working_session = session
            working_proxy = proxy_url
            logger.success(f"✅ Прокси работает: {proxy_url}")
            break

        except Exception as e:
            logger.warning(f"❌ Прокси не работает {proxy_url}: {type(e).__name__}")
            continue

    if not working_session:
        logger.error("❌ Ни один прокси не работает! Попробуйте позже или используйте VPN")
        sys.exit(1)

    # Создаем бота с рабочим прокси
    bot = Bot(
        token=settings.BOT_TOKEN,
        session=working_session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Создаем диспетчер
    dp = Dispatcher()

    # Подключаем роутеры (admin первым!)
    dp.include_routers(
        admin.router,      # Админские команды
        start.router,      # /start
        messages.router,   # Текстовые сообщения
        media.router,      # Медиа
    )

    logger.info("✅ Бот запущен через прокси!")
    logger.info(f"🌐 Прокси: {working_proxy}")

    # Запускаем polling
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
