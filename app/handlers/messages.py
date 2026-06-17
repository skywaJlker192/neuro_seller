from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.services.dialog_manager import DialogManager
from app.config import settings
from loguru import logger
import os

router = Router()

# Определяем нишу по умолчанию
DEFAULT_NICHE = os.path.join("niches", "default.yaml")

@router.message(F.text)
async def handle_text_message(message: Message, bot: Bot, state: FSMContext):
    """Обработка текстовых сообщений"""
    user_id = message.from_user.id
    user_message = message.text

    logger.info(f"Пользователь {user_id} отправил: {user_message[:50]}...")

    try:
        # Создаем DialogManager
        dialog_manager = DialogManager(bot=bot)

        # Обрабатываем сообщение
        response = await dialog_manager.process_message(
            tg_user_id=user_id,
            user_message=user_message,
            niche_file=DEFAULT_NICHE
        )

        await message.answer(response)
        logger.info(f"Ответ пользователю {user_id}: {response[:50]}...")

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения от {user_id}: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при обработке вашего сообщения. "
            "Пожалуйста, попробуйте ещё раз или напишите позже."
        )
