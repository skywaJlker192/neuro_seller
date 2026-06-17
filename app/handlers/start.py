from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    await state.clear()

    welcome_text = """
👋 Привет! Я ваш виртуальный консультант.

Я помогу подобрать оптимальное решение под ваши задачи. Просто расскажите, что вас интересует!

💬 Я работаю с текстовыми сообщениями. Если отправите фото или голосовое — я вежливо предупрежу, что пока не умею их обрабатывать.

Что вас интересует?
"""
    await message.answer(welcome_text)
    logger.info(f"Пользователь {message.from_user.id} начал диалог")

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработка команды /help"""
    help_text = """
📚 Как со мной общаться:

1️⃣ Просто напишите, что вас интересует
2️⃣ Я задам уточняющие вопросы
3️⃣ Помогу подобрать решение
4️⃣ При необходимости передам вас менеджеру

📝 Команды:
/start — начать диалог заново
/help — эта справка

⚠️ Я работаю только с текстом. Фото, голосовые и документы пока не поддерживаю.
"""
    await message.answer(help_text)

@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext):
    """Сбросить диалог и начать заново"""
    await state.clear()
    await message.answer("🔄 Диалог сброшен. Начнём сначала! Что вас интересует?")
    logger.info(f"Пользователь {message.from_user.id} сбросил диалог")
