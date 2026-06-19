from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.keyboards.dynamic_keyboard import (
    get_main_keyboard,
    get_back_keyboard,
    get_category_inline_keyboard,
    get_back_inline_keyboard,
    get_services_keyboard
)
from app.niche.loader import load_niche
from app.db.repositories import UserRepository, LeadRepository, DialogRepository
from app.services.google_sheets import sheets_exporter
from app.config import settings
from loguru import logger
from pathlib import Path

router = Router()


# ============================================
# FSM СОСТОЯНИЯ ДЛЯ ФОРМЫ ЗАПИСИ
# ============================================

class ServiceForm(StatesGroup):
    """Состояния формы записи на услугу"""
    name = State()      # Ожидает имя
    contact = State()   # Ожидает телефон
    budget = State()    # Ожидает бюджет


def get_current_niche_name() -> str:
    """Получает текущую нишу"""
    niche_file = Path("current_niche.txt")
    if niche_file.exists():
        return niche_file.read_text(encoding="utf-8").strip()
    return "default"


def get_niche_config():
    """Загружает конфиг текущей ниши"""
    return load_niche(get_current_niche_name())


def cat_to_dict(cat) -> dict:
    """Конвертирует Pydantic объект категории в dict"""
    if cat is None:
        return {}
    if isinstance(cat, dict):
        return cat
    if hasattr(cat, 'model_dump'):
        return cat.model_dump()
    if hasattr(cat, 'dict'):
        return cat.dict()
    if hasattr(cat, '__dict__'):
        return cat.__dict__
    return {}


def get_category_by_id(cat_id: str) -> dict | None:
    """Находит категорию по ID"""
    niche_config = get_niche_config()
    categories = getattr(niche_config, 'categories', []) or []
    for cat in categories:
        cat_dict = cat_to_dict(cat)
        if cat_dict.get('id') == cat_id:
            return cat_dict
    return None


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик /start"""
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал диалог")

    # Очищаем состояние если было
    await state.clear()

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
async def main_menu(event, state: FSMContext):
    """Главное меню"""
    # Очищаем состояние
    await state.clear()

    niche_config = get_niche_config()
    text = f"🏪 <b>{niche_config.business_name}</b>\n\nВыберите категорию:"

    try:
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
    except Exception as e:
        if "message is not modified" in str(e):
            if isinstance(event, CallbackQuery):
                await event.answer()
        else:
            raise


@router.message(F.text == "🔄 Перезапустить")
@router.callback_query(F.data == "restart")
async def restart_bot(event, state: FSMContext):
    """Перезапуск бота"""
    await state.clear()
    if isinstance(event, CallbackQuery):
        await event.message.delete()
        await cmd_start(event.message, state)
        await event.answer("🔄 Бот перезапущен!")
    else:
        await cmd_start(event, state)


# ============================================
# ОБРАБОТКА КАТЕГОРИЙ — ПОКАЗЫВАЕМ УСЛУГИ КНОПКАМИ
# ============================================

async def handle_category(event, cat_id: str, state: FSMContext):
    """Показывает услуги категории кнопками"""
    # Очищаем состояние при выборе категории
    await state.clear()

    category = get_category_by_id(cat_id)

    if not category:
        text = "❌ Категория не найдена"
        keyboard = get_back_inline_keyboard()
    else:
        # Проверяем есть ли услуги в категории
        services = category.get('services', [])

        if services:
            # Есть услуги — показываем их кнопками
            text = category.get('description', 'Выберите услугу:')
            keyboard = get_services_keyboard(cat_id)
        else:
            # Нет услуг — показываем описание с кнопкой назад
            text = category.get('description', 'Нет описания')
            keyboard = get_back_inline_keyboard()

    try:
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await event.answer()
        else:
            await event.answer(
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    except Exception as e:
        if "message is not modified" in str(e):
            if isinstance(event, CallbackQuery):
                await event.answer()
        else:
            raise


# ============================================
# ОБРАБОТКА КНОПОК УСЛУГ (service_*)
# ============================================

@router.callback_query(F.data.startswith("service_"))
async def handle_service_click(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия на услугу.
    Callback формат: service_{category_id}_{service_index}
    """
    # Парсим callback
    parts = callback.data.split("_", 2)
    if len(parts) < 3:
        await callback.answer("❌ Ошибка")
        return

    category_id = parts[1]
    try:
        service_index = int(parts[2])
    except ValueError:
        await callback.answer("❌ Ошибка")
        return

    # Получаем информацию об услуге
    category = get_category_by_id(category_id)
    if not category:
        await callback.answer("❌ Категория не найдена")
        return

    services = category.get('services', [])
    if service_index >= len(services):
        await callback.answer("❌ Услуга не найдена")
        return

    service = services[service_index]
    service_name = service.get('name', 'Услуга')
    price = service.get('price', '')
    duration = service.get('duration', '')

    # Сохраняем данные услуги в FSM
    await state.update_data(
        service_name=service_name,
        category_id=category_id,
        service_index=service_index
    )

    # Показываем форму — просим имя
    text = (
        f"✍️ <b>Запись на услугу</b>\n\n"
        f"📋 <b>Услуга:</b> {service_name}\n"
    )
    if price:
        text += f"💰 <b>Стоимость:</b> {price}\n"
    if duration:
        text += f"⏱️ <b>Длительность:</b> {duration}\n"

    text += "\n👤 Введите ваше <b>имя</b>:"

    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

    # Переходим к состоянию ввода имени
    await state.set_state(ServiceForm.name)


# ============================================
# ОБРАБОТКА ФОРМЫ ЗАПИСИ (FSM)
# ============================================

@router.message(ServiceForm.name)
async def process_name(message: Message, state: FSMContext):
    """Обрабатывает имя клиента"""
    name = message.text.strip()

    if not name or len(name) < 2:
        await message.answer("❌ Пожалуйста, введите корректное имя:")
        return

    # Сохраняем имя
    await state.update_data(name=name)

    await message.answer(
        f"✅ Приятно познакомиться, {name}!\n\n"
        f"📱 Теперь введите ваш <b>номер телефона</b>:\n"
        f"(например: +79991234567)",
        parse_mode="HTML"
    )
    await state.set_state(ServiceForm.contact)


@router.message(ServiceForm.contact)
async def process_contact(message: Message, state: FSMContext):
    """Обрабатывает телефон клиента"""
    contact = message.text.strip()

    # Простая проверка телефона
    import re
    phone_clean = re.sub(r'[^\d+]', '', contact)
    if len(phone_clean) < 10:
        await message.answer(
            "❌ Неверный формат телефона.\n\n"
            "Введите номер в формате: +79991234567"
        )
        return

    # Сохраняем контакт
    await state.update_data(contact=contact)

    await message.answer(
        "💰 Введите ваш <b>бюджет</b> (например: 3000):",
        parse_mode="HTML"
    )
    await state.set_state(ServiceForm.budget)


@router.message(ServiceForm.budget)
async def process_budget_and_create_lead(message: Message, state: FSMContext):
    """Обрабатывает бюджет и создаёт лид"""
    budget = message.text.strip()

    # Получаем все данные из формы
    data = await state.get_data()
    service_name = data.get('service_name', '')
    name = data.get('name', '')
    contact = data.get('contact', '')

    # Очищаем состояние
    await state.clear()

    # Получаем текущего пользователя
    user_repo = UserRepository()
    user = await user_repo.get_or_create(message.from_user.id)

    # Получаем конфиг ниши
    niche_config = get_niche_config()

    # Создаём лид
    lead_repo = LeadRepository()
    lead = await lead_repo.create(
        user_id=user.id,
        name=name,
        interest=f"Запись: {service_name}",
        contact=contact,
        budget=f"бюджет {budget}"
    )

    logger.success(f"✅ ЛИД СОЗДАН ИЗ ФОРМЫ: {lead}")

    # Отправляем менеджеру
    manager_id = settings.MANAGER_CHAT_ID
    if manager_id:
        text = (
            f"🔥 <b>НОВЫЙ ЛИД!</b>\n\n"
            f"📋 <b>Ниша:</b> {niche_config.business_name}\n\n"
            f"<b>Данные клиента:</b>\n"
            f"• Имя: {name}\n"
            f"• Услуга: {service_name}\n"
            f"• Контакт: {contact}\n"
            f"• Бюджет: {budget}\n"
        )
        try:
            await message.bot.send_message(int(manager_id), text, parse_mode="HTML")
            logger.info(f"✅ Лид отправлен менеджеру {manager_id}")
        except Exception as e:
            logger.error(f"Не удалось отправить лид: {e}")

    # Экспорт в Google Sheets
    lead_data = {
        "tg_user_id": message.from_user.id,
        "name": name,
        "interest": service_name,
        "budget": budget,
        "contact": contact
    }

    try:
        await sheets_exporter.add_lead(
            lead_data,
            niche_config.business_name,
            sent_to_manager=True
        )
        logger.info("✅ Лид экспортирован в Google Sheets")
    except Exception as e:
        logger.error(f"Ошибка экспорта в Google Sheets: {e}")

    # Отвечаем клиенту
    await message.answer(
        f"✅ <b>Заявка оформлена!</b>\n\n"
        f"📋 Услуга: {service_name}\n"
        f"👤 Имя: {name}\n"
        f"📱 Телефон: {contact}\n"
        f"💰 Бюджет: {budget}\n\n"
        f"Мы свяжемся с вами в ближайшее время!",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )


# ============================================
# ОБРАБОТЧИКИ ТЕКСТОВЫХ КНОПОК КАТЕГОРИЙ
# ============================================

@router.message(F.text.startswith("💻 ") | F.text.startswith("📱 ") | F.text.startswith("👕 ") |
                F.text.startswith("💄 ") | F.text.startswith("🛋️ ") | F.text.startswith("⚽ ") |
                F.text.startswith("📚 ") | F.text.startswith("🍫 ") | F.text.startswith("🧸 ") |
                F.text.startswith("🚗 ") | F.text.startswith("💇‍♀️ ") | F.text.startswith("🎨 ") |
                F.text.startswith("💅 ") | F.text.startswith("✨ ") | F.text.startswith("🔧 ") |
                F.text.startswith("🛞 ") | F.text.startswith("🛑 ") | F.text.startswith("⚡ "))
async def handle_text_category(message: Message, state: FSMContext):
    """Обработка текстовых кнопок категорий"""
    # Если пользователь в состоянии формы — не обрабатываем категорию
    current_state = await state.get_state()
    if current_state is not None:
        return

    text = message.text
    niche_config = get_niche_config()
    categories = getattr(niche_config, 'categories', []) or []

    for cat in categories:
        cat_dict = cat_to_dict(cat)
        emoji = cat_dict.get('emoji', '')
        name = cat_dict.get('name', '')
        cat_id = cat_dict.get('id', '')

        if text == f"{emoji} {name}":
            await handle_category(message, cat_id, state)
            return

    await message.answer(
        text.replace("Выберите категорию:", ""),
        reply_markup=get_back_keyboard()
    )


# ============================================
# ОБРАБОТЧИКИ CALLBACK КАТЕГОРИЙ (все ниши)
# ============================================

# UniversalStore категории
@router.callback_query(F.data == "category_laptops")
async def category_laptops(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_laptops", state)

@router.callback_query(F.data == "category_phones")
async def category_phones(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_phones", state)

@router.callback_query(F.data == "category_clothing")
async def category_clothing(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_clothing", state)

@router.callback_query(F.data == "category_cosmetics")
async def category_cosmetics(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_cosmetics", state)

@router.callback_query(F.data == "category_furniture")
async def category_furniture(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_furniture", state)

@router.callback_query(F.data == "category_sports")
async def category_sports(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_sports", state)

@router.callback_query(F.data == "category_books")
async def category_books(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_books", state)

@router.callback_query(F.data == "category_food")
async def category_food(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_food", state)

@router.callback_query(F.data == "category_toys")
async def category_toys(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_toys", state)

@router.callback_query(F.data == "category_auto")
async def category_auto(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_auto", state)

# Beauty Salon категории
@router.callback_query(F.data == "category_haircut")
async def category_haircut(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_haircut", state)

@router.callback_query(F.data == "category_coloring")
async def category_coloring(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_coloring", state)

@router.callback_query(F.data == "category_manicure")
async def category_manicure(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_manicure", state)

@router.callback_query(F.data == "category_makeup")
async def category_makeup(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_makeup", state)

@router.callback_query(F.data == "category_care")
async def category_care(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_care", state)

# Auto Service категории
@router.callback_query(F.data == "category_maintenance")
async def category_maintenance(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_maintenance", state)

@router.callback_query(F.data == "category_engine")
async def category_engine(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_engine", state)

@router.callback_query(F.data == "category_suspension")
async def category_suspension(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_suspension", state)

@router.callback_query(F.data == "category_brakes")
async def category_brakes(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_brakes", state)

@router.callback_query(F.data == "category_electric")
async def category_electric(callback: CallbackQuery, state: FSMContext):
    await handle_category(callback, "category_electric", state)


# ============================================
# ОБЩИЕ КНОПКИ
# ============================================

@router.message(F.text == "🔥 Акции")
@router.callback_query(F.data == "promotions")
async def promotions(event):
    """Акции и скидки"""
    niche_config = get_niche_config()

    text = (
        "🔥 <b>Акции и скидки</b>\n\n"
        "🎁 При заказе от 5 000₽ — подарок!\n"
        "💰 Скидка 10% для новых клиентов\n"
        "👥 Приведи друга — получи бонус\n\n"
        "Акции действуют до конца месяца!"
    )

    try:
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(
                text,
                reply_markup=get_back_keyboard(),
                parse_mode="HTML"
            )
            await event.answer()
        else:
            await event.answer(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e):
            if isinstance(event, CallbackQuery):
                await event.answer()
        else:
            raise


@router.message(F.text == "📦 Все товары")
@router.callback_query(F.data == "all_products")
async def all_products(event):
    """Все товары/услуги"""
    niche_config = get_niche_config()
    categories = getattr(niche_config, 'categories', []) or []

    text = f"📦 <b>{niche_config.business_name}</b>\n\nУ нас есть:\n\n"

    for cat in categories:
        cat_dict = cat_to_dict(cat)
        emoji = cat_dict.get('emoji', '')
        name = cat_dict.get('name', '')
        text += f"{emoji} {name}\n"

    text += "\nНапишите, что вас интересует — помогу выбрать!"

    try:
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(
                text,
                reply_markup=get_back_keyboard(),
                parse_mode="HTML"
            )
            await event.answer()
        else:
            await event.answer(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e):
            if isinstance(event, CallbackQuery):
                await event.answer()
        else:
            raise


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

    try:
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(
                text,
                reply_markup=get_back_keyboard(),
                parse_mode="HTML"
            )
            await event.answer()
        else:
            await event.answer(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e):
            if isinstance(event, CallbackQuery):
                await event.answer()
        else:
            raise
