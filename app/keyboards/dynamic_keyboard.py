from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from app.niche.loader import load_niche
from pathlib import Path
from loguru import logger


def get_current_niche_name() -> str:
    """Получает текущую нишу"""
    niche_file = Path("current_niche.txt")
    if niche_file.exists():
        return niche_file.read_text(encoding="utf-8").strip()
    return "default"


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура — строится динамически из YAML"""
    niche_name = get_current_niche_name()
    niche_config = load_niche(niche_name)

    buttons = []
    row = []

    categories = getattr(niche_config, 'categories', []) or []

    for i, cat in enumerate(categories):
        emoji = cat.get('emoji', '')
        name = cat.get('name', '')
        row.append(KeyboardButton(text=f"{emoji} {name}"))

        # Каждые 2 кнопки — новая строка
        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    # Добавляем общие кнопки
    buttons.append([
        KeyboardButton(text="🔥 Акции"),
        KeyboardButton(text="📦 Все товары")
    ])
    buttons.append([
        KeyboardButton(text="📞 Контакты"),
        KeyboardButton(text="🔄 Перезапустить")
    ])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой 'Назад в меню'"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


def get_category_inline_keyboard(niche_name: str = None) -> InlineKeyboardMarkup:
    """Инлайн-клавиатура с категориями из YAML"""
    if niche_name is None:
        niche_name = get_current_niche_name()

    niche_config = load_niche(niche_name)
    categories = getattr(niche_config, 'categories', []) or []

    buttons = []
    for cat in categories:
        emoji = cat.get('emoji', '')
        name = cat.get('name', '')
        cat_id = cat.get('id', '')
        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} {name}",
                callback_data=cat_id
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_inline_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'Назад'"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
        ]
    )
