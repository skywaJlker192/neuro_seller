from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню с кнопками"""
    builder = ReplyKeyboardBuilder()

    # Категории товаров
    builder.button(text="💻 Ноутбуки", callback_data="category_laptops")
    builder.button(text="📱 Смартфоны", callback_data="category_phones")
    builder.button(text="👕 Одежда", callback_data="category_clothing")
    builder.button(text="💄 Косметика", callback_data="category_cosmetics")
    builder.button(text="🛋️ Мебель", callback_data="category_furniture")
    builder.button(text="⚽ Спорттовары", callback_data="category_sports")
    builder.button(text="📚 Книги", callback_data="category_books")
    builder.button(text="🍫 Продукты", callback_data="category_food")
    builder.button(text="🧸 Игрушки", callback_data="category_toys")
    builder.button(text="🚗 Автозапчасти", callback_data="category_auto")

    # Дополнительные кнопки
    builder.button(text="🔥 Акции", callback_data="promotions")
    builder.button(text="📦 Все товары", callback_data="all_products")

    # Сервисные кнопки
    builder.button(text="📞 Контакты", callback_data="contacts")
    builder.button(text="🔄 Перезапустить", callback_data="restart")

    # Располагаем кнопки: 2 в ряд
    builder.adjust(2)

    return builder.as_markup(resize_keyboard=True)


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой назад"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔙 Назад в меню", callback_data="main_menu")
    builder.button(text="🔄 Перезапустить бота", callback_data="restart")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)
