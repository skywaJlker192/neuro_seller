from app.db.repositories import LeadRepository
from app.db.database import async_session
from sqlalchemy import select
from app.db.models import Lead
from loguru import logger
import re


class LeadCollector:
    """Анализирует диалог и собирает информацию о клиенте"""

    def __init__(self):
        self.lead_repo = LeadRepository()

    async def check_and_collect_lead(self, user_id: int, history: list[dict]) -> Lead | None:
        """
        Проверяет, собрана ли вся необходимая информация о клиенте
        В MVP — достаточно хотя бы одного из: имя, контакт, интерес
        """
        # Получаем или создаём лид
        existing_lead = await self.lead_repo.get_by_user_id(user_id)

        if existing_lead and existing_lead.sent_to_manager:
            return None

        # Извлекаем данные из истории
        lead_data = self._extract_basic_info(history)

        # Если есть хотя бы один важный параметр — сохраняем
        if lead_data.get("interest") or lead_data.get("contact") or lead_data.get("name"):
            if existing_lead:
                lead = await self.lead_repo.update(existing_lead.id, **lead_data)
            else:
                lead = await self.lead_repo.create(user_id=user_id, **lead_data)

            logger.info(f"Лид частично собран для пользователя {user_id}: {lead_data}")
            return lead

        return None

    def _extract_basic_info(self, history: list[dict]) -> dict:
        """Извлекает базовую информацию из истории"""
        lead_data = {}

        # Собираем все сообщения пользователя
        user_messages = [msg["content"] for msg in history if msg["role"] == "user"]

        if not user_messages:
            return lead_data

        # Ищем интерес (что хочет купить)
        interest_keywords = ["хочу купить", "интересует", "ищу", "нужен", "покупаю"]
        for msg in user_messages:
            msg_lower = msg.lower()
            for kw in interest_keywords:
                if kw in msg_lower:
                    lead_data["interest"] = msg.strip()
                    break
            if lead_data.get("interest"):
                break

        # Ищем контакт (телефон/email)
        import re
        for msg in user_messages:
            # Телефон
            phone_match = re.search(r'(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', msg)
            if phone_match:
                lead_data["contact"] = phone_match.group(0)
                break

            # Email
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg)
            if email_match:
                lead_data["contact"] = email_match.group(0)
                break

        # Ищем имя (простая эвристика)
        for msg in user_messages:
            if "меня зовут" in msg.lower() or "мое имя" in msg.lower():
                parts = msg.split()
                for i, part in enumerate(parts):
                    if part.lower() in ["зовут", "имя"] and i + 1 < len(parts):
                        lead_data["name"] = parts[i + 1].capitalize()
                        break

        return lead_data
