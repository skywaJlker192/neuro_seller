from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from app.services.google_sheets import sheets_exporter
from app.config import settings
from loguru import logger
import tempfile
import os
import yaml
from pathlib import Path

router = Router()

NICHES_DIR = Path("niches")


@router.message(Command("check_id"))
async def check_my_id(message: Message):
    """Показывает твой ID"""
    await message.answer(f"Твой ID: {message.from_user.id}\nMANAGER_CHAT_ID: {settings.MANAGER_CHAT_ID}")


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом"""
    admin_id = int(settings.MANAGER_CHAT_ID)
    return user_id == admin_id


@router.message(Command("set_niche"))
async def cmd_set_niche(message: Message):
    """
    Команда для смены ниши: /set_niche beauty_salon
    """
    args = message.text.split()

    if len(args) < 2:
        # Показываем список доступных ниш
        available_niches = get_available_niches()
        text = " **Доступные ниши:**\n\n"

        for niche_file, niche_name in available_niches.items():
            text += f"• `/{'set_niche'} {niche_file.replace('.yaml', '')}` — {niche_name}\n"

        text += "\n**Пример:** `/set_niche beauty_salon`"

        await message.answer(text)
        return

    # Получаем название ниши
    niche_name = args[1].replace(".yaml", "")
    niche_file = f"{niche_name}.yaml"
    niche_path = NICHES_DIR / niche_file

    # Проверяем существует ли файл
    if not niche_path.exists():
        await message.answer(
            f"❌ Ниша '{niche_name}' не найдена.\n"
            f"Файл {niche_file} не существует в папке niches/"
        )
        return

    # Загружаем конфиг для проверки
    try:
        with open(niche_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        business_name = config.get("business_name", niche_name)

        # Сохраняем текущую нишу в файле
        save_current_niche(niche_name)

        logger.info(f"Пользователь {message.from_user.id} сменил нишу на {niche_name}")

        await message.answer(
            f"✅ **Ниша изменена на: {business_name}**\n\n"
            f"Теперь бот работает в режиме '{business_name}'.\n"
            f"Отправьте /start чтобы начать диалог."
        )

    except Exception as e:
        logger.error(f"Ошибка при загрузке ниши {niche_name}: {e}")
        await message.answer(f"❌ Ошибка при загрузке ниши: {e}")


@router.message(Command("current_niche"))
async def cmd_current_niche(message: Message):
    """Показывает текущую нишу"""
    current = get_current_niche()
    await message.answer(f"📌 Текущая ниша: **{current}**")


def get_available_niches() -> dict:
    """Получает список доступных ниш из папки niches/"""
    niches = {}

    if not NICHES_DIR.exists():
        NICHES_DIR.mkdir(parents=True, exist_ok=True)
        return {"default.yaml": "Universal Store (по умолчанию)"}

    for file in NICHES_DIR.glob("*.yaml"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                business_name = config.get("business_name", file.stem)
                niches[file.name] = business_name
        except Exception as e:
            logger.error(f"Ошибка при чтении {file}: {e}")
            niches[file.name] = file.stem

    return niches


def get_current_niche() -> str:
    """Получает текущую нишу из файла"""
    niche_file = Path("current_niche.txt")

    if niche_file.exists():
        return niche_file.read_text(encoding="utf-8").strip()

    return "default"


def save_current_niche(niche_name: str):
    """Сохраняет текущую нишу в файл"""
    niche_file = Path("current_niche.txt")
    niche_file.write_text(niche_name, encoding="utf-8")


@router.message(Command("export_leads"))
async def export_all_leads(message: Message):
    """Экспорт всех лидов в CSV"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа. Эта команда только для админов.")
        return

    await message.answer("📊 Генерирую CSV файл...")

    csv_data = await sheets_exporter.get_leads_csv()

    if csv_data.startswith("Ошибка"):
        await message.answer(f"❌ {csv_data}")
        return

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig') as f:
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
        await message.answer(f"❌ {csv_data}")
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
        await message.answer(" Нет доступа.")
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
        await message.answer(" Нет доступа.")
        return

    stats = sheets_exporter.get_stats()

    if not stats:
        await message.answer("❌ Не удалось получить статистику")
        return

    text = "📊 <b>Статистика лидов</b>\n\n"
    text += f"📈 Всего лидов: {stats.get('total', 0)}\n"
    text += f" За сегодня: {stats.get('today', 0)}\n"
    text += f" За неделю: {stats.get('this_week', 0)}\n"
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
