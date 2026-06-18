import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger
from app.config import settings
from app.db.database import async_session
from app.db.models import Lead
from sqlalchemy import select
import json


class GoogleSheetsExporter:
    """Экспорт лидов в Google Таблицы"""

    def __init__(self):
        self.credentials_file = "credentials.json"
        self.spreadsheet_name = "TechStore Leads"
        self.client = None
        self.spreadsheet = None
        self.worksheet = None

    def connect(self) -> bool:
        """Подключение к Google Таблицам"""
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]

            creds = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_file,
                scope
            )

            self.client = gspread.authorize(creds)

            # Пробуем открыть существующую таблицу
            try:
                self.spreadsheet = self.client.open(self.spreadsheet_name)
                self.worksheet = self.spreadsheet.sheet1

                # Проверяем, есть ли заголовки
                first_row = self.worksheet.row_values(1)
                if not first_row or not first_row[0]:
                    # Заголовков нет - добавляем
                    headers = [
                        "ID", "Дата", "Время", "Telegram ID", "Имя",
                        "Интерес", "Бюджет", "Контакт", "Ниша",
                        "Отправлено менеджеру"
                    ]
                    self.worksheet.append_row(headers)

                logger.info(f"Подключен к таблице: {self.spreadsheet_name}")

            except gspread.SpreadsheetNotFound:
                # Создаём новую таблицу
                self.spreadsheet = self.client.create(self.spreadsheet_name)
                self.worksheet = self.spreadsheet.sheet1

                # Добавляем заголовки
                headers = [
                    "ID", "Дата", "Время", "Telegram ID", "Имя",
                    "Интерес", "Бюджет", "Контакт", "Ниша",
                    "Отправлено менеджеру"
                ]
                self.worksheet.append_row(headers)

                logger.info(f"Создана новая таблица: {self.spreadsheet_name}")

            return True

        except Exception as e:
            logger.error(f"Ошибка подключения к Google Sheets: {e}")
            return False

    async def add_lead(self, lead_data: dict, niche: str, sent_to_manager: bool = False):
        """Добавляет лид в таблицу"""
        logger.info(f"📊 Попытка добавить лид в Google Sheets: {lead_data}")

        if not self.worksheet:
            logger.warning("Worksheet не подключен, пытаюсь подключиться...")
            if not self.connect():
                logger.error("Не удалось подключиться к Google Sheets")
                return False

        try:
            # Получаем следующий ID
            all_rows = self.worksheet.get_all_values()
            next_id = len(all_rows)  # ID = номер строки

            # Формируем строку
            now = datetime.now()
            row = [
                next_id,
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                str(lead_data.get("tg_user_id", "")),
                str(lead_data.get("name", "") or ""),
                str(lead_data.get("interest", "") or ""),
                str(lead_data.get("budget", "") or ""),
                str(lead_data.get("contact", "") or ""),
                str(niche),
                "Да" if sent_to_manager else "Нет"
            ]

            logger.info(f"Добавляю строку в таблицу: {row}")
            self.worksheet.append_row(row)
            logger.success(f"✅ Лид добавлен в Google Sheets: {lead_data.get('name')}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка добавления лида в таблицу: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def get_leads_csv(self, days: int = None) -> str:
        """Получает лиды в формате CSV (Excel-compatible с точкой с запятой)"""
        if not self.connect():
            return "Ошибка подключения к Google Sheets"

        try:
            # Получаем все значения
            all_values = self.worksheet.get_all_values()

            if not all_values:
                return "Нет данных"

            # Берем заголовок из первой строки
            headers = all_values[0]

            # Остальные строки - данные
            data_rows = all_values[1:]

            # Фильтруем по дате если нужно
            if days and data_rows:
                cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                filtered_rows = []
                for row in data_rows:
                    if len(row) > 1 and row[1] and row[1] >= cutoff_date:
                        filtered_rows.append(row)
                data_rows = filtered_rows

            # Создаём CSV с ТОЧКОЙ С ЗАПЯТОЙ (для русского Excel)
            csv_lines = []

            # Заголовки
            csv_lines.append("ID;Дата;Время;Telegram ID;Имя;Интерес;Бюджет;Контакт;Ниша;Отправлено менеджеру")

            # Данные
            for row in data_rows:
                # Дополняем до 10 колонок
                while len(row) < 10:
                    row.append('')

                # Очищаем данные: убираем переносы строк и ТОЧКИ С ЗАПЯТОЙ в данных
                cleaned_row = []
                for cell in row[:10]:
                    cell_str = str(cell).replace('\n', ' ').replace('\r', '')
                    cell_str = cell_str.replace(';', ',')  # Заменяем ; на , в данных
                    cell_str = cell_str.replace('"', "'")  # Заменяем кавычки
                    cleaned_row.append(cell_str)

                csv_lines.append(';'.join(cleaned_row))  # Используем ; как разделитель

            # Объединяем с переносами строк
            csv_string = '\n'.join(csv_lines)

            logger.info(f"CSV экспортирован: {len(data_rows)} записей")
            return csv_string

        except Exception as e:
            logger.error(f"Ошибка экспорта CSV: {e}")
            return f"Ошибка: {e}"

    def get_stats(self) -> dict:
        """Получает статистику по лидам"""
        if not self.connect():
            return {}

        try:
            all_rows = self.worksheet.get_all_records()

            stats = {
                "total": len(all_rows),
                "today": 0,
                "this_week": 0,
                "by_niche": {},
                "sent_to_manager": 0
            }

            today = datetime.now().strftime("%Y-%m-%d")
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            for row in all_rows:
                # За сегодня
                if row.get("Дата") == today:
                    stats["today"] += 1

                # За неделю
                if row.get("Дата") >= week_ago:
                    stats["this_week"] += 1

                # По нишам
                niche = row.get("Ниша", "Unknown")
                stats["by_niche"][niche] = stats["by_niche"].get(niche, 0) + 1

                # Отправлено менеджеру
                if row.get("Отправлено менеджеру") == "Да":
                    stats["sent_to_manager"] += 1

            return stats

        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}


# Глобальный экземпляр
sheets_exporter = GoogleSheetsExporter()
