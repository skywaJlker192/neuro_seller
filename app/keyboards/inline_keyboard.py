from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_laptops_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для ноутбуков"""
    builder = InlineKeyboardBuilder()

    builder.button(text="💼 Для работы", callback_data="laptop_work")
    builder.button(text="🎮 Игровые", callback_data="laptop_gaming")
    builder.button(text="💰 Бюджетные до 50к", callback_data="laptop_budget_50")
    builder.button(text="💎 Премиум", callback_data="laptop_premium")
    builder.button(text="🍎 MacBook", callback_data="laptop_macbook")
    builder.button(text="🪟 Windows", callback_data="laptop_windows")

    builder.button(text="🔙 Назад", callback_data="main_menu")
    builder.adjust(2, 2, 2, 1)

    return builder.as_markup()


def get_phones_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для смартфонов"""
    builder = InlineKeyboardBuilder()

    builder.button(text="🍎 iPhone", callback_data="phone_iphone")
    builder.button(text="📱 Samsung", callback_data="phone_samsung")
    builder.button(text="📱 Xiaomi", callback_data="phone_xiaomi")
    builder.button(text="💰 До 30к", callback_data="phone_budget_30")
    builder.button(text="💰 30-50к", callback_data="phone_budget_50")
    builder.button(text="💎 Флагманы", callback_data="phone_flagship")

    builder.button(text="🔙 Назад", callback_data="main_menu")
    builder.adjust(2, 2, 2, 1)

    return builder.as_markup()


def get_back_inline_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад (inline)"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад в меню", callback_data="main_menu")
    return builder.as_markup()
