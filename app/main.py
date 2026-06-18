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
    "http://95.140.154.156:1080",      # Russia, elite
    "http://213.27.29.153:51000",      # Russia, SOCKS5
    "http://194.58.37.234:65200",      # Russia, SOCKS5, super fast
    "http://82.114.228.67:1080",       # Russia, elite
    "http://84.47.150.125:1080",       # Russia, elite
    "http://176.12.71.36:1234",        # Iran, elite HTTP
    "http://92.118.112.25:1082",       # Greece, elite HTTP
    "http://62.133.62.231:1081",       # France, elite HTTP
    "http://212.58.132.5:8888",        # UK, HTTP/HTTPS
    "http://178.156.224.42:3128",      # Romania, elite HTTP
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
