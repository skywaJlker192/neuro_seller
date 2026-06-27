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


def get_categories_from_config(niche_config) -> list:
    """Безопасно извлекает категории из конфига"""
    categories = getattr(niche_config, 'categories', None)

    if not categories:
        logger.warning(f"Категории не найдены в конфиге {niche_config.business_name}")
        return []

    result = []
    for cat in categories:
        if isinstance(cat, dict):
            result.append(cat)
        elif hasattr(cat, 'model_dump'):
            result.append(cat.model_dump())
        elif hasattr(cat, 'dict'):
            result.append(cat.dict())
        elif hasattr(cat, '__dict__'):
            result.append(cat.__dict__)
        else:
            logger.warning(f"Неизвестный формат категории: {type(cat)}")

    logger.info(f"Загружено {len(result)} категорий: {[c.get('name', '?') for c in result]}")
    return result


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура — строится динамически из YAML"""
    niche_name = get_current_niche_name()
    logger.info(f"Загружаю клавиатуру для ниши: {niche_name}")

    try:
        niche_config = load_niche(niche_name)
    except Exception as e:
        logger.error(f"Ошибка загрузки ниши: {e}")
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔥 Акции"), KeyboardButton(text="📦 Все товары")],
                [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="🔄 Перезапустить")]
            ],
            resize_keyboard=True
        )

    buttons = []
    row = []

    categories = get_categories_from_config(niche_config)
    logger.info(f"Создаю клавиатуру с {len(categories)} категориями")

    for cat in categories:
        emoji = cat.get('emoji', '')
        name = cat.get('name', '')

        if emoji and name:
            row.append(KeyboardButton(text=f"{emoji} {name}"))

            if len(row) == 2:
                buttons.append(row)
                row = []

    if row:
        buttons.append(row)

    buttons.append([
        KeyboardButton(text="🔥 Акции"),
        KeyboardButton(text="📦 Все товары")
    ])
    buttons.append([
        KeyboardButton(text="📞 Контакты"),
        KeyboardButton(text="🔄 Перезапустить")
    ])

    logger.info(f"Клавиатура создана: {len(buttons)} строк")

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

    try:
        niche_config = load_niche(niche_name)
    except Exception as e:
        logger.error(f"Ошибка загрузки ниши: {e}")
        return InlineKeyboardMarkup(
            # inline_keyboard=[
            #     [InlineKeyboardButton(text="🏠 Главное меню", callback_data="all_products")]
            # ]
        )

    categories = get_categories_from_config(niche_config)

    buttons = []
    for cat in categories:
        emoji = cat.get('emoji', '')
        name = cat.get('name', '')
        cat_id = cat.get('id', '')

        if emoji and name and cat_id:
            buttons.append([
                InlineKeyboardButton(
                    text=f"{emoji} {name}",
                    callback_data=cat_id
                )
            ])

    # buttons.append([
    #     InlineKeyboardButton(text="🏠 Главное меню", callback_data="all_products")
    # ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_inline_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'Назад'"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
        ]
    )


# ============================================
# КЛАВИАТУРА С УСЛУГАМИ
# ============================================

def get_services_keyboard(category_id: str, niche_name: str = None) -> InlineKeyboardMarkup:
    """
    Создаёт инлайн-клавиатуру с услугами выбранной категории.
    Каждая услуга — отдельная кнопка.
    🔧 ИСПРАВЛЕНО: используется :: как разделитель в callback_data
    """
    if niche_name is None:
        niche_name = get_current_niche_name()

    try:
        niche_config = load_niche(niche_name)
    except Exception as e:
        logger.error(f"Ошибка загрузки ниши: {e}")
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
            ]
        )

    categories = get_categories_from_config(niche_config)

    # Ищем категорию по ID
    target_category = None
    for cat in categories:
        if cat.get('id') == category_id:
            target_category = cat
            break

    if not target_category:
        logger.warning(f"Категория {category_id} не найдена")
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
            ]
        )

    # Получаем услуги из категории
    services = target_category.get('services', [])

    # Если услуг нет — используем description как fallback
    if not services:
        logger.warning(f"Услуги не найдены в категории {category_id}")
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
            ]
        )

    # 🔧 ИСПРАВЛЕНО: используем :: как разделитель
    buttons = []
    for i, service in enumerate(services):
        service_name = service.get('name', f'Услуга {i+1}')
        price = service.get('price', '')

        # Формируем текст кнопки
        button_text = service_name
        if price:
            button_text = f"{service_name} — {price}"

        # 🔧 ВАЖНО: разделитель :: вместо _
        callback_data = f"svc::{category_id}::{i}"

        buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=callback_data
            )
        ])

    # Кнопка назад
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="main_menu")
    ])

    logger.info(f"Создана клавиатура с {len(services)} услугами для категории {category_id}")

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_service_info(category_id: str, service_index: int, niche_name: str = None) -> dict | None:
    """
    Получает информацию об услуге по индексу.
    Возвращает dict с полями: name, price, duration, description
    """
    if niche_name is None:
        niche_name = get_current_niche_name()

    try:
        niche_config = load_niche(niche_name)
    except Exception as e:
        logger.error(f"Ошибка загрузки ниши: {e}")
        return None

    categories = get_categories_from_config(niche_config)

    # Ищем категорию
    for cat in categories:
        if cat.get('id') == category_id:
            services = cat.get('services', [])
            if 0 <= service_index < len(services):
                return services[service_index]

    return None


def get_category_info(category_id: str, niche_name: str = None) -> dict | None:
    """Получает информацию о категории по ID"""
    if niche_name is None:
        niche_name = get_current_niche_name()

    try:
        niche_config = load_niche(niche_name)
    except Exception as e:
        logger.error(f"Ошибка загрузки ниши: {e}")
        return None

    categories = get_categories_from_config(niche_config)

    for cat in categories:
        if cat.get('id') == category_id:
            return cat

    return None
