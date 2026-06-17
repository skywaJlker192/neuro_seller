from aiogram import Router, F
from aiogram.types import Message, ContentType
from loguru import logger

router = Router()

@router.message(F.photo)
async def handle_photo(message: Message):
    """Обработка фотографий (ТЗ п.6)"""
    await message.answer(
        "📸 Я пока не умею анализировать фотографии. "
        "Пожалуйста, опишите ваш вопрос текстом — я с радостью помогу! "
        "Если нужно показать что-то конкретное — просто опишите это словами."
    )
    logger.info(f"Пользователь {message.from_user.id} отправил фото (не поддерживается)")

@router.message(F.voice)
async def handle_voice(message: Message):
    """Обработка голосовых сообщений (ТЗ п.6)"""
    await message.answer(
        "🎤 Я пока не умею прослушивать голосовые сообщения. "
        "Пожалуйста, напишите ваш вопрос текстом — так я смогу быстрее вам помочь!"
    )
    logger.info(f"Пользователь {message.from_user.id} отправил голосовое (не поддерживается)")

@router.message(F.audio)
async def handle_audio(message: Message):
    """Обработка аудиофайлов"""
    await message.answer(
        "🎵 Я не работаю с аудиофайлами. "
        "Пожалуйста, напишите ваш вопрос текстом."
    )
    logger.info(f"Пользователь {message.from_user.id} отправил аудио (не поддерживается)")

@router.message(F.document)
async def handle_document(message: Message):
    """Обработка документов"""
    await message.answer(
        "📄 Я не могу открывать документы. "
        "Пожалуйста, скопируйте текст или опишите ваш вопрос своими словами."
    )
    logger.info(f"Пользователь {message.from_user.id} отправил документ (не поддерживается)")

@router.message(F.video)
async def handle_video(message: Message):
    """Обработка видео"""
    await message.answer(
        "🎥 Я не работаю с видео. "
        "Пожалуйста, опишите ваш вопрос текстом."
    )
    logger.info(f"Пользователь {message.from_user.id} отправил видео (не поддерживается)")

@router.message(F.sticker)
async def handle_sticker(message: Message):
    """Обработка стикеров"""
    await message.answer(
        "😊 Стикеры я понимаю, но ответить могу только на текстовые сообщения. "
        "Напишите ваш вопрос текстом!"
    )
    logger.info(f"Пользователь {message.from_user.id} отправил стикер (не поддерживается)")
