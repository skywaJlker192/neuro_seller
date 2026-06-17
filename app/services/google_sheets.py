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

            # Пробуем открыть существующую таблицу или создаём новую
            try:
                self.spreadsheet = self.client.open(self.spreadsheet_name)
                self.worksheet = self.spreadsheet.sheet1
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

                # Делимся таблицей с админом (опционально)
                # self.spreadsheet.share(settings.ADMIN_EMAIL, perm_type='user', role='writer')

                logger.info(f"Создана новая таблица: {self.spreadsheet_name}")

            return True

        except Exception as e:
            logger.error(f"Ошибка подключения к Google Sheets: {e}")
            return False

    async def add_lead(self, lead_data: dict, niche: str, sent_to_manager: bool = False):
        """Добавляет лид в таблицу"""
        if not self.worksheet:
            if not self.connect():
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
                lead_data.get("tg_user_id", ""),
                lead_data.get("name", ""),
                lead_data.get("interest", ""),
                lead_data.get("budget", ""),
                lead_data.get("contact", ""),
                niche,
                "Да" if sent_to_manager else "Нет"
            ]

            self.worksheet.append_row(row)
            logger.info(f"Лид добавлен в Google Sheets: {lead_data.get('name')}")
            return True

        except Exception as e:
            logger.error(f"Ошибка добавления лида в таблицу: {e}")
            return False

    async def get_leads_csv(self, days: int = None) -> str:
        """Получает лиды в формате CSV"""
        if not self.connect():
            return "Ошибка подключения к Google Sheets"

        try:
            # Получаем все данные
            all_rows = self.worksheet.get_all_records()

            if not all_rows:
                return "Нет данных"

            # Фильтруем по дате если нужно
            if days:
                cutoff_date = datetime.now() - timedelta(days=days)
                filtered_rows = []
                for row in all_rows:
                    try:
                        row_date = datetime.strptime(row["Дата"], "%Y-%m-%d")
                        if row_date >= cutoff_date:
                            filtered_rows.append(row)
                    except:
                        filtered_rows.append(row)
                all_rows = filtered_rows

            # Конвертируем в DataFrame и затем в CSV
            df = pd.DataFrame(all_rows)
            csv_string = df.to_csv(index=False, sep=";")

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
