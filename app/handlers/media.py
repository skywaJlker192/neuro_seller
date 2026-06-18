from aiogram import Router, F
from aiogram.types import Message
from app.services.product_info import ProductInfoSearcher
from app.services.lead_collector import LeadCollector
from app.db.repositories import DialogRepository, UserRepository
from app.niche.loader import load_niche
from loguru import logger

router = Router()


@router.message(F.photo)
async def handle_photo(message: Message):
    """Обрабатывает фото товара"""
    logger.info(f"Пользователь {message.from_user.id} отправил фото")

    # Получаем фото (наивысшее качество)
    photo = message.photo[-1]
    file_id = photo.file_id

    # Скачиваем информацию о файле
    file = await message.bot.get_file(file_id)
    file_path = file.file_path

    logger.info(f"Фото получено: {file_path}")

    # Сохраняем диалог
    dialog_repo = DialogRepository()
    user_repo = UserRepository()
    user = await user_repo.get_or_create(message.from_user.id)

    # Сохраняем сообщение
    await dialog_repo.save_message(
        user_id=user.id,
        role="user",
        content="[Фото товара]"
    )

    # Пытаемся распознать что на фото или спрашиваем
    await message.answer(
        "Фото получил. Подскажи, что это за товар?\n"
        "Напиши название (например: iPhone 15, MacBook Pro, кроссовки Nike)",
        reply_to_message_id=message.message_id
    )


@router.message(F.text & F.reply_to_message)
async def handle_reply_to_photo(message: Message):
    """Обрабатывает ответ на фото с названием товара"""
    if not message.reply_to_message.photo:
        return

    logger.info(f"Пользователь {message.from_user.id} указал название товара на фото")

    product_name = message.text.strip()
    logger.info(f"Товар на фото: {product_name}")

    # Сохраняем диалог
    dialog_repo = DialogRepository()
    user_repo = UserRepository()
    user = await user_repo.get_or_create(message.from_user.id)
    niche_config = load_niche("default")

    await dialog_repo.save_message(
        user_id=user.id,
        role="user",
        content=f"[Фото] {product_name}"
    )

    # Ищем информацию о товаре (используем твой ProductInfoSearcher)
    searcher = ProductInfoSearcher()
    product_info = await searcher.search_product_info(product_name)

    if product_info:
        # Нашли информацию
        await message.answer(product_info)

        # Сохраняем ответ
        await dialog_repo.save_message(
            user_id=user.id,
            role="assistant",
            content=product_info
        )

        # Создаём лид
        await _create_lead_from_photo(
            user_id=user.id,
            product_name=product_name,
            dialog_repo=dialog_repo
        )
    else:
        # Не нашли - используем LLM напрямую
        from app.llm.yandex_client import YandexGPTClient
        from app.services.prompt_builder import PromptBuilder

        llm = YandexGPTClient()
        prompt_builder = PromptBuilder(niche_config)
        system_prompt = prompt_builder.build_system_prompt()

        prompt = f"Клиент отправил фото товара: {product_name}. Дай информацию о цене и характеристиках."

        try:
            response = await llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=500
            )

            await message.answer(response)

            await dialog_repo.save_message(
                user_id=user.id,
                role="assistant",
                content=response
            )

            # Создаём лид
            await _create_lead_from_photo(
                user_id=user.id,
                product_name=product_name,
                dialog_repo=dialog_repo
            )

        except Exception as e:
            logger.error(f"Ошибка LLM: {e}")
            await message.answer(
                f"Не удалось найти информацию о '{product_name}'.\n"
                "Попробуй уточнить название или задай вопрос."
            )


async def _create_lead_from_photo(user_id: int, product_name: str, dialog_repo):
    """Создаёт лид из фото"""
    lead_collector = LeadCollector()

    # Формируем историю
    history = [
        {"role": "user", "content": f"[Фото] {product_name}"},
        {"role": "assistant", "content": f"Информация о {product_name}"}
    ]

    # Пытаемся собрать лид
    lead = await lead_collector.check_and_collect_lead(
        user_id=user_id,
        history=history
    )

    if lead:
        logger.info(f"Создан лид из фото: {lead}")
