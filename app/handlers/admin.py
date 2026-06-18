from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from app.services.google_sheets import sheets_exporter
from app.config import settings
from loguru import logger
import tempfile
import os

router = Router()

@router.message(Command("check_id"))
async def check_my_id(message: Message):
    """Показывает твой ID"""
    await message.answer(f"Твой ID: {message.from_user.id}\nMANAGER_CHAT_ID: {settings.MANAGER_CHAT_ID}")

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом"""
    admin_id = int(settings.MANAGER_CHAT_ID)  # Преобразуем в int
    return user_id == admin_id


@router.message(Command("export_leads"))
async def export_all_leads(message: Message):
    """Экспорт всех лидов в CSV"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа. Эта команда только для админов.")
        return

    await message.answer(" Генерирую CSV файл...")

    csv_data = await sheets_exporter.get_leads_csv()

    if csv_data.startswith("Ошибка"):
        await message.answer(f"❌ {csv_data}")
        return

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(csv_data)
        temp_file = f.name

    try:
        file = FSInputFile(temp_file)
        await message.answer_document(
            document=file,
            caption=f"📊 Экспорт всех лидов\nВсего записей: {len(csv_data.split(chr(10))) - 1}"
        )
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


@router.message(Command("export_leads_today"))
async def export_today_leads(message: Message):
    """Экспорт лидов за сегодня"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа.")
        return

    await message.answer("📊 Генерирую CSV за сегодня...")

    csv_data = await sheets_exporter.get_leads_csv(days=1)

    if csv_data.startswith("Ошибка"):
        await message.answer(f" {csv_data}")
        return

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(csv_data)
        temp_file = f.name

    try:
        file = FSInputFile(temp_file)
        await message.answer_document(
            document=file,
            caption="📊 Лиды за сегодня"
        )
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


@router.message(Command("export_leads_week"))
async def export_week_leads(message: Message):
    """Экспорт лидов за неделю"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа.")
        return

    await message.answer("📊 Генерирую CSV за неделю...")

    csv_data = await sheets_exporter.get_leads_csv(days=7)

    if csv_data.startswith("Ошибка"):
        await message.answer(f"❌ {csv_data}")
        return

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(csv_data)
        temp_file = f.name

    try:
        file = FSInputFile(temp_file)
        await message.answer_document(
            document=file,
            caption="📊 Лиды за неделю"
        )
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


@router.message(Command("leads_stats"))
async def leads_statistics(message: Message):
    """Статистика по лидам"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа.")
        return

    stats = sheets_exporter.get_stats()

    if not stats:
        await message.answer("❌ Не удалось получить статистику")
        return

    text = " <b>Статистика лидов</b>\n\n"
    text += f" Всего лидов: {stats.get('total', 0)}\n"
    text += f"📅 За сегодня: {stats.get('today', 0)}\n"
    text += f"📆 За неделю: {stats.get('this_week', 0)}\n"
    text += f"✅ Отправлено менеджеру: {stats.get('sent_to_manager', 0)}\n\n"

    if stats.get('by_niche'):
        text += "<b>По нишам:</b>\n"
        for niche, count in stats['by_niche'].items():
            text += f"• {niche}: {count}\n"

    await message.answer(text, parse_mode="HTML")


@router.message(Command("leads_search"))
async def search_leads(message: Message):
    """Поиск лидов по ключевому слову"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа.")
        return

    query = message.text.replace("/leads_search", "").strip()
    if not query:
        await message.answer("❌ Укажите поисковый запрос. Пример: /leads_search iPhone")
        return

    await message.answer(f"🔍 Ищу лиды по запросу: {query}...")

    csv_data = await sheets_exporter.get_leads_csv()

    if csv_data.startswith("Ошибка"):
        await message.answer(f"❌ {csv_data}")
        return

    lines = csv_data.split('\n')
    header = lines[0]
    matching_lines = [header]

    for line in lines[1:]:
        if query.lower() in line.lower():
            matching_lines.append(line)

    if len(matching_lines) <= 1:
        await message.answer(f"❌ Ничего не найдено по запросу '{query}'")
        return

    result_csv = '\n'.join(matching_lines)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(result_csv)
        temp_file = f.name

    try:
        file = FSInputFile(temp_file)
        await message.answer_document(
            document=file,
            caption=f" Найдено лидов: {len(matching_lines) - 1}\nПоиск: {query}"
        )
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
