from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.keyboards.dynamic_keyboard import (
    get_main_keyboard,
    get_back_keyboard,
    get_category_inline_keyboard,
    get_back_inline_keyboard
)
from app.niche.loader import load_niche
from loguru import logger
from pathlib import Path

router = Router()


def get_current_niche_name() -> str:
    """Получает текущую нишу"""
    niche_file = Path("current_niche.txt")
    if niche_file.exists():
        return niche_file.read_text(encoding="utf-8").strip()
    return "default"


def get_niche_config():
    """Загружает конфиг текущей ниши"""
    return load_niche(get_current_niche_name())


def get_category_by_id(cat_id: str) -> dict | None:
    """Находит категорию по ID"""
    niche_config = get_niche_config()
    categories = getattr(niche_config, 'categories', []) or []
    for cat in categories:
        if cat.get('id') == cat_id:
            return cat
    return None


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик /start"""
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал диалог")

    niche_config = get_niche_config()
    welcome_text = getattr(niche_config, 'welcome_text', None)

    if not welcome_text:
        welcome_text = (
            f"👋 <b>Привет! Я ваш виртуальный консультант {niche_config.business_name}.</b>\n\n"
            f"{niche_config.product_description}\n\n"
            f"Выберите категорию или задайте вопрос:"
        )

    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🏠 Главное меню")
@router.callback_query(F.data == "main_menu")
async def main_menu(event):
    """Главное меню"""
    niche_config = get_niche_config()
    text = f"🏪 <b>{niche_config.business_name}</b>\n\nВыберите категорию:"

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(
            text,
            reply_markup=get_category_inline_keyboard(),
            parse_mode="HTML"
        )
        await event.answer()
    else:
        await event.answer(
            text,
            reply_markup=get_category_inline_keyboard(),
            parse_mode="HTML"
        )


@router.message(F.text == "🔄 Перезапустить")
@router.callback_query(F.data == "restart")
async def restart_bot(event):
    """Перезапуск бота"""
    if isinstance(event, CallbackQuery):
        await event.message.delete()
        await cmd_start(event.message)
        await event.answer("🔄 Бот перезапущен!")
    else:
        await cmd_start(event)


# ============================================
# ОБРАБОТКА КАТЕГОРИЙ ИЗ YAML (универсально)
# ============================================

async def handle_category(event, cat_id: str):
    """Универсальный обработчик категории"""
    category = get_category_by_id(cat_id)

    if not category:
        text = "❌ Категория не найдена"
    else:
        text = category.get('description', 'Нет описания')

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(
            text,
            reply_markup=get_back_inline_keyboard(),
            parse_mode="HTML"
        )
        await event.answer()
    else:
        await event.answer(
            text,
            reply_markup=get_back_inline_keyboard(),
            parse_mode="HTML"
        )


# Обработчики для текстовых кнопок (из ReplyKeyboard)
@router.message(F.text.startswith("💻 ") | F.text.startswith("📱 ") | F.text.startswith("👕 ") |
                F.text.startswith("💄 ") | F.text.startswith("🛋️ ") | F.text.startswith("⚽ ") |
                F.text.startswith("📚 ") | F.text.startswith("🍫 ") | F.text.startswith("🧸 ") |
                F.text.startswith("🚗 ") | F.text.startswith("💇‍♀️ ") | F.text.startswith("🎨 ") |
                F.text.startswith("💅 ") | F.text.startswith("✨ ") | F.text.startswith("🔧 ") |
                F.text.startswith("🛞 ") | F.text.startswith("🛑 ") | F.text.startswith("⚡ "))
async def handle_text_category(message: Message):
    """Обработка текстовых кнопок категорий"""
    text = message.text
    niche_config = get_niche_config()
    categories = getattr(niche_config, 'categories', []) or []

    # Ищем категорию по названию
    for cat in categories:
        emoji = cat.get('emoji', '')
        name = cat.get('name', '')
        if text == f"{emoji} {name}":
            await handle_category(message, cat.get('id'))
            return

    # Если не нашли — показываем описание
    await message.answer(
        text.replace("Выберите категорию:", ""),
        reply_markup=get_back_keyboard()
    )


# Обработчики для callback категорий (из InlineKeyboard)
# UniversalStore категории
@router.callback_query(F.data == "category_laptops")
async def category_laptops(callback: CallbackQuery):
    await handle_category(callback, "category_laptops")

@router.callback_query(F.data == "category_phones")
async def category_phones(callback: CallbackQuery):
    await handle_category(callback, "category_phones")

@router.callback_query(F.data == "category_clothing")
async def category_clothing(callback: CallbackQuery):
    await handle_category(callback, "category_clothing")

@router.callback_query(F.data == "category_cosmetics")
async def category_cosmetics(callback: CallbackQuery):
    await handle_category(callback, "category_cosmetics")

@router.callback_query(F.data == "category_furniture")
async def category_furniture(callback: CallbackQuery):
    await handle_category(callback, "category_furniture")

@router.callback_query(F.data == "category_sports")
async def category_sports(callback: CallbackQuery):
    await handle_category(callback, "category_sports")

@router.callback_query(F.data == "category_books")
async def category_books(callback: CallbackQuery):
    await handle_category(callback, "category_books")

@router.callback_query(F.data == "category_food")
async def category_food(callback: CallbackQuery):
    await handle_category(callback, "category_food")

@router.callback_query(F.data == "category_toys")
async def category_toys(callback: CallbackQuery):
    await handle_category(callback, "category_toys")

@router.callback_query(F.data == "category_auto")
async def category_auto(callback: CallbackQuery):
    await handle_category(callback, "category_auto")

# Beauty Salon категории
@router.callback_query(F.data == "category_haircut")
async def category_haircut(callback: CallbackQuery):
    await handle_category(callback, "category_haircut")

@router.callback_query(F.data == "category_coloring")
async def category_coloring(callback: CallbackQuery):
    await handle_category(callback, "category_coloring")

@router.callback_query(F.data == "category_manicure")
async def category_manicure(callback: CallbackQuery):
    await handle_category(callback, "category_manicure")

@router.callback_query(F.data == "category_makeup")
async def category_makeup(callback: CallbackQuery):
    await handle_category(callback, "category_makeup")

@router.callback_query(F.data == "category_care")
async def category_care(callback: CallbackQuery):
    await handle_category(callback, "category_care")

# Auto Service категории
@router.callback_query(F.data == "category_maintenance")
async def category_maintenance(callback: CallbackQuery):
    await handle_category(callback, "category_maintenance")

@router.callback_query(F.data == "category_engine")
async def category_engine(callback: CallbackQuery):
    await handle_category(callback, "category_engine")

@router.callback_query(F.data == "category_suspension")
async def category_suspension(callback: CallbackQuery):
    await handle_category(callback, "category_suspension")

@router.callback_query(F.data == "category_brakes")
async def category_brakes(callback: CallbackQuery):
    await handle_category(callback, "category_brakes")

@router.callback_query(F.data == "category_electric")
async def category_electric(callback: CallbackQuery):
    await handle_category(callback, "category_electric")


# ============================================
# ОБЩИЕ КНОПКИ
# ============================================

@router.message(F.text == "🔥 Акции")
@router.callback_query(F.data == "promotions")
async def promotions(event):
    """Акции и скидки"""
    niche_config = get_niche_config()

    # Универсальные акции
    text = (
        "🔥 <b>Акции и скидки</b>\n\n"
        "🎁 При заказе от 5 000₽ — подарок!\n"
        "💰 Скидка 10% для новых клиентов\n"
        "👥 Приведи друга — получи бонус\n\n"
        "Акции действуют до конца месяца!"
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(
            text,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
        await event.answer()
    else:
        await event.answer(text, reply_markup=get_back_keyboard(), parse_mode="HTML")


@router.message(F.text == "📦 Все товары")
@router.callback_query(F.data == "all_products")
async def all_products(event):
    """Все товары/услуги"""
    niche_config = get_niche_config()

    # Формируем список из категорий
    categories = getattr(niche_config, 'categories', []) or []

    text = f"📦 <b>{niche_config.business_name}</b>\n\nУ нас есть:\n\n"

    for cat in categories:
        emoji = cat.get('emoji', '')
        name = cat.get('name', '')
        text += f"{emoji} {name}\n"

    text += "\nНапишите, что вас интересует — помогу выбрать!"

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(
            text,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
        await event.answer()
    else:
        await event.answer(text, reply_markup=get_back_keyboard(), parse_mode="HTML")


@router.message(F.text == "📞 Контакты")
@router.callback_query(F.data == "contacts")
async def contacts(event):
    """Контакты"""
    niche_config = get_niche_config()

    text = (
        f"📞 <b>Контакты {niche_config.business_name}</b>\n\n"
        f"📱 Телефон: +7 (999) 123-45-67\n"
        f"📧 Email: info@{niche_config.business_name.lower().replace(' ', '')}.ru\n"
        f"🕐 Время работы: 10:00 - 20:00\n\n"
        f"Мы всегда на связи!"
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(
            text,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
        await event.answer()
    else:
        await event.answer(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
