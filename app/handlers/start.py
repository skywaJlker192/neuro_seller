from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.keyboards.main_keyboard import get_main_keyboard, get_back_keyboard
from app.keyboards.inline_keyboard import (
    get_laptops_keyboard,
    get_phones_keyboard,
    get_back_inline_keyboard
)
from loguru import logger

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик /start"""
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал диалог")

    await message.answer(
        "👋 <b>Привет! Я ваш виртуальный консультант UniversalStore.</b>\n\n"
        "Я помогу подобрать любой товар под ваши задачи.\n"
        "У нас есть: электроника, одежда, косметика, мебель, спорттовары, книги, продукты, игрушки, автозапчасти.\n\n"
        "Выберите категорию или задайте вопрос:",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    """Главное меню"""
    await callback.message.edit_text(
        "🏪 <b>Выберите категорию:</b>",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "restart")
async def restart_bot(callback: CallbackQuery):
    """Перезапуск бота"""
    await callback.message.delete()
    await cmd_start(callback.message)
    await callback.answer("🔄 Бот перезапущен!")

@router.callback_query(F.data == "category_laptops")
async def category_laptops(callback: CallbackQuery):
    """Категория: Ноутбуки"""
    await callback.message.edit_text(
        "💻 <b>Ноутбуки</b>\n\n"
        "У нас большой выбор:\n"
        "• MacBook Pro 14 M3: 120 000 - 150 000₽\n"
        "• MacBook Air M2: 90 000 - 110 000₽\n"
        "• ASUS ROG: 80 000 - 120 000₽\n"
        "• Lenovo Legion: 70 000 - 100 000₽\n"
        "• HP Pavilion: 50 000 - 70 000₽\n\n"
        "Выберите подкатегорию:",
        reply_markup=get_laptops_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "category_phones")
async def category_phones(callback: CallbackQuery):
    """Категория: Смартфоны"""
    await callback.message.edit_text(
        "📱 <b>Смартфоны</b>\n\n"
        "Популярные модели:\n"
        "• iPhone 15 Pro Max: 120 000 - 150 000₽\n"
        "• iPhone 15 Pro: 100 000 - 120 000₽\n"
        "• iPhone 15: 80 000 - 100 000₽\n"
        "• Samsung Galaxy S24: 80 000 - 100 000₽\n"
        "• Xiaomi 13: 50 000 - 70 000₽\n\n"
        "Выберите подкатегорию:",
        reply_markup=get_phones_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "category_clothing")
async def category_clothing(callback: CallbackQuery):
    """Категория: Одежда"""
    await callback.message.edit_text(
        "👕 <b>Одежда и обувь</b>\n\n"
        "Популярные товары:\n"
        "• Куртка зимняя: 5 000 - 15 000₽\n"
        "• Джинсы Levi's: 4 000 - 8 000₽\n"
        "• Кроссовки Nike: 6 000 - 15 000₽\n"
        "• Кроссовки Adidas: 5 000 - 12 000₽\n"
        "• Платье вечернее: 3 000 - 10 000₽\n"
        "• Костюм деловой: 8 000 - 20 000₽\n\n"
        "Что вас интересует?",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "category_cosmetics")
async def category_cosmetics(callback: CallbackQuery):
    """Категория: Косметика"""
    await callback.message.edit_text(
        "💄 <b>Косметика</b>\n\n"
        "Популярные товары:\n"
        "• Крем для лица Nivea: 300 - 800₽\n"
        "• Шампунь Pantene: 400 - 900₽\n"
        "• Парфюм Chanel: 8 000 - 15 000₽\n"
        "• Помада MAC: 1 500 - 2 500₽\n"
        "• Тушь Maybelline: 500 - 1 200₽\n\n"
        "Что вас интересует?",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "category_furniture")
async def category_furniture(callback: CallbackQuery):
    """Категория: Мебель"""
    await callback.message.edit_text(
        "🛋️ <b>Мебель</b>\n\n"
        "Популярные товары:\n"
        "• Диван угловой: 25 000 - 60 000₽\n"
        "• Кровать двуспальная: 15 000 - 40 000₽\n"
        "• Стол обеденный: 8 000 - 20 000₽\n"
        "• Шкаф-купе: 20 000 - 50 000₽\n"
        "• Кресло офисное: 5 000 - 15 000₽\n\n"
        "Что вас интересует?",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "category_sports")
async def category_sports(callback: CallbackQuery):
    """Категория: Спорт"""
    await callback.message.edit_text(
        "⚽ <b>Спорттовары</b>\n\n"
        "Популярные товары:\n"
        "• Велосипед горный: 15 000 - 40 000₽\n"
        "• Беговая дорожка: 20 000 - 60 000₽\n"
        "• Гантели набор: 2 000 - 8 000₽\n"
        "• Коврик для йоги: 1 000 - 3 000₽\n"
        "• Палатка туристическая: 5 000 - 15 000₽\n\n"
        "Что вас интересует?",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "category_books")
async def category_books(callback: CallbackQuery):
    """Категория: Книги"""
    await callback.message.edit_text(
        "📚 <b>Книги</b>\n\n"
        "Популярные товары:\n"
        "• Книга бестселлер: 500 - 1 500₽\n"
        "• Учебник: 800 - 2 500₽\n"
        "• Энциклопедия: 1 500 - 4 000₽\n\n"
        "Что вас интересует?",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "category_food")
async def category_food(callback: CallbackQuery):
    """Категория: Продукты"""
    await callback.message.edit_text(
        "🍫 <b>Продукты</b>\n\n"
        "Популярные товары:\n"
        "• Кофе в зернах 1кг: 800 - 2 000₽\n"
        "• Чай элитный 100г: 500 - 1 500₽\n"
        "• Шоколад премиум: 300 - 800₽\n"
        "• Вино хорошее: 1 000 - 3 000₽\n\n"
        "Что вас интересует?",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "category_toys")
async def category_toys(callback: CallbackQuery):
    """Категория: Игрушки"""
    await callback.message.edit_text(
        "🧸 <b>Игрушки</b>\n\n"
        "Популярные товары:\n"
        "• LEGO набор: 2 000 - 8 000₽\n"
        "• Кукла Barbie: 1 500 - 3 000₽\n"
        "• Машинка на радиоуправлении: 2 000 - 5 000₽\n"
        "• Настольная игра: 1 000 - 3 000₽\n\n"
        "Что вас интересует?",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "category_auto")
async def category_auto(callback: CallbackQuery):
    """Категория: Автозапчасти"""
    await callback.message.edit_text(
        "🚗 <b>Автозапчасти</b>\n\n"
        "Популярные товары:\n"
        "• Масло моторное 4л: 2 000 - 4 000₽\n"
        "• Шины летние R16: 4 000 - 8 000₽\n"
        "• Шины зимние R16: 5 000 - 10 000₽\n"
        "• Аккумулятор: 5 000 - 10 000₽\n"
        "• Видеорегистратор: 3 000 - 8 000₽\n\n"
        "Что вас интересует?",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "promotions")
async def promotions(callback: CallbackQuery):
    """Акции и скидки"""
    await callback.message.edit_text(
        "🔥 <b>Акции и скидки</b>\n\n"
        "🎁 При покупке от 50 000₽ — подарок!\n"
        "💰 Скидка 10% на электронику при trade-in\n"
        "👕 Скидка 15% на одежду при покупке от 3 вещей\n"
        "🛋️ Бесплатная доставка мебели\n\n"
        "Акции действуют до конца месяца!",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "all_products")
async def all_products(callback: CallbackQuery):
    """Все товары"""
    await callback.message.edit_text(
        "📦 <b>Весь ассортимент</b>\n\n"
        "У нас есть:\n"
        "💻 Электроника: 500 - 250 000₽\n"
        "👕 Одежда: 1 000 - 20 000₽\n"
        "💄 Косметика: 300 - 15 000₽\n"
        "🛋️ Мебель: 5 000 - 60 000₽\n"
        "⚽ Спорттовары: 1 000 - 60 000₽\n"
        "📚 Книги: 500 - 4 000₽\n"
        "🍫 Продукты: 300 - 3 000₽\n"
        "🧸 Игрушки: 1 000 - 8 000₽\n"
        "🚗 Автозапчасти: 2 000 - 10 000₽\n\n"
        "Напишите, что вас интересует — помогу выбрать!",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "contacts")
async def contacts(callback: CallbackQuery):
    """Контакты"""
    await callback.message.edit_text(
        "📞 <b>Наши контакты</b>\n\n"
        "📍 Адрес: г. Москва, ул. Примерная, 123\n"
        "📱 Телефон: +7 (999) 123-45-67\n"
        "📧 Email: info@universalstore.ru\n"
        "🕐 Время работы: 10:00 - 20:00\n\n"
        "Мы всегда на связи!",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# Обработчики подкатегорий ноутбуков
@router.callback_query(F.data.startswith("laptop_"))
async def laptop_subcategory(callback: CallbackQuery):
    """Подкатегории ноутбуков"""
    subcat = callback.data.replace("laptop_", "")

    texts = {
        "work": "💼 <b>Ноутбуки для работы</b>\n\n"
                "• MacBook Air M2: 90 000 - 110 000₽\n"
                "• Dell XPS 13: 100 000 - 130 000₽\n"
                "• HP Pavilion: 50 000 - 70 000₽\n"
                "• Lenovo ThinkPad: 80 000 - 120 000₽",
        "gaming": "🎮 <b>Игровые ноутбуки</b>\n\n"
                  "• ASUS ROG Strix: 80 000 - 120 000₽\n"
                  "• Lenovo Legion 5: 70 000 - 100 000₽\n"
                  "• MSI Katana: 90 000 - 130 000₽",
        "budget_50": "💰 <b>Бюджетные ноутбуки до 50к</b>\n\n"
                     "• HP Pavilion 15: 45 000 - 50 000₽\n"
                     "• Lenovo IdeaPad: 40 000 - 48 000₽\n"
                     "• ASUS VivoBook: 42 000 - 50 000₽",
        "premium": "💎 <b>Премиум ноутбуки</b>\n\n"
                   "• MacBook Pro 16 M3: 200 000 - 250 000₽\n"
                   "• Dell XPS 15: 150 000 - 180 000₽\n"
                   "• ASUS ZenBook Pro: 130 000 - 160 000₽",
        "macbook": "🍎 <b>MacBook</b>\n\n"
                   "• MacBook Air M2: 90 000 - 110 000₽\n"
                   "• MacBook Pro 14 M3: 120 000 - 150 000₽\n"
                   "• MacBook Pro 16 M3: 200 000 - 250 000₽",
        "windows": "🪟 <b>Windows ноутбуки</b>\n\n"
                   "• ASUS ROG: 80 000 - 120 000₽\n"
                   "• Lenovo Legion: 70 000 - 100 000₽\n"
                   "• Dell XPS: 100 000 - 180 000₽\n"
                   "• HP Pavilion: 50 000 - 70 000₽"
    }

    text = texts.get(subcat, "Выберите подкатегорию")
    await callback.message.edit_text(
        text,
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# Обработчики подкатегорий смартфонов
@router.callback_query(F.data.startswith("phone_"))
async def phone_subcategory(callback: CallbackQuery):
    """Подкатегории смартфонов"""
    subcat = callback.data.replace("phone_", "")

    texts = {
        "iphone": "🍎 <b>iPhone</b>\n\n"
                  "• iPhone 15 Pro Max: 120 000 - 150 000₽\n"
                  "• iPhone 15 Pro: 100 000 - 120 000₽\n"
                  "• iPhone 15: 80 000 - 100 000₽\n"
                  "• iPhone 14 Pro: 90 000 - 110 000₽\n"
                  "• iPhone 14: 70 000 - 90 000₽",
        "samsung": "📱 <b>Samsung</b>\n\n"
                   "• Galaxy S24 Ultra: 120 000 - 140 000₽\n"
                   "• Galaxy S24: 80 000 - 100 000₽\n"
                   "• Galaxy S23: 60 000 - 80 000₽\n"
                   "• Galaxy A54: 35 000 - 45 000₽",
        "xiaomi": "📱 <b>Xiaomi</b>\n\n"
                  "• Xiaomi 13: 50 000 - 70 000₽\n"
                  "• Xiaomi 12: 40 000 - 55 000₽\n"
                  "• Redmi Note 13: 25 000 - 35 000₽",
        "budget_30": "💰 <b>Смартфоны до 30к</b>\n\n"
                     "• Redmi Note 13: 25 000 - 30 000₽\n"
                     "• Realme 11: 22 000 - 28 000₽\n"
                     "• Samsung A24: 20 000 - 25 000₽",
        "budget_50": "💰 <b>Смартфоны 30-50к</b>\n\n"
                     "• Xiaomi 13 Lite: 35 000 - 45 000₽\n"
                     "• Samsung A54: 35 000 - 45 000₽\n"
                     "• Nothing Phone 2: 45 000 - 50 000₽",
        "flagship": "💎 <b>Флагманы</b>\n\n"
                    "• iPhone 15 Pro Max: 120 000 - 150 000₽\n"
                    "• Samsung S24 Ultra: 120 000 - 140 000₽\n"
                    "• Xiaomi 13 Ultra: 90 000 - 110 000₽"
    }

    text = texts.get(subcat, "Выберите подкатегорию")
    await callback.message.edit_text(
        text,
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
