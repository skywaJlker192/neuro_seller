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
                # Обновляем только заполненные поля
                update_data = {k: v for k, v in lead_data.items() if v}
                if update_data:
                    lead = await self.lead_repo.update(existing_lead.id, **update_data)
                else:
                    lead = existing_lead
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
        interest_keywords = ["хочу купить", "купить", "заказать", "интересует", "ищу", "нужен", "покупаю"]
        for msg in user_messages:
            msg_lower = msg.lower()
            for kw in interest_keywords:
                if kw in msg_lower:
                    parts = msg.split(kw, 1)
                    if len(parts) > 1:
                        lead_data["interest"] = f"{kw} {parts[1].strip()}"
                    else:
                        lead_data["interest"] = msg.strip()
                    break
            if lead_data.get("interest"):
                break

        # Ищем телефон (несколько форматов)
        phone_patterns = [
            r'(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
            r'(\+7|8)\d{10}',
            r'номер[:\s]+(\+?7?\d{10,11})',
            r'телефон[:\s]+(\+?7?\d{10,11})',
            r'мой номер[:\s]*(\+?7?\d{10,11})',
        ]

        for msg in user_messages:
            msg_clean = msg.replace(" ", "")
            for pattern in phone_patterns:
                phone_match = re.search(pattern, msg_clean)
                if phone_match:
                    lead_data["contact"] = phone_match.group(0)
                    logger.info(f"Найден телефон: {lead_data['contact']}")
                    break
            if lead_data.get("contact"):
                break

        # Ищем email
        if not lead_data.get("contact"):
            for msg in user_messages:
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg)
                if email_match:
                    lead_data["contact"] = email_match.group(0)
                    logger.info(f"Найден email: {lead_data['contact']}")
                    break

        # Ищем имя
        for msg in user_messages:
            msg_lower = msg.lower()
            if "меня зовут" in msg_lower or "мое имя" in msg_lower or "зовут" in msg_lower:
                for kw in ["меня зовут", "мое имя", "зовут"]:
                    if kw in msg_lower:
                        parts = msg.lower().split(kw, 1)
                        if len(parts) > 1:
                            name_part = parts[1].strip().split()[0]
                            name = ''.join(c for c in name_part if c.isalpha() or c == '-')
                            if name and len(name) > 1:
                                lead_data["name"] = name.capitalize()
                                logger.info(f"Найдено имя: {lead_data['name']}")
                        break

        # Ищем бюджет
        budget_patterns = [
            r'бюджет[:\s]*(\d+[\s\-]?\d*)',
            r'до\s+(\d+[\s\-]?\d*)\s*руб',
            r'(\d+[\s\-]?\d*)\s*руб',
            r'цена[:\s]*(\d+[\s\-]?\d*)',
        ]

        for msg in user_messages:
            for pattern in budget_patterns:
                budget_match = re.search(pattern, msg.lower())
                if budget_match:
                    lead_data["budget"] = budget_match.group(0)
                    logger.info(f"Найден бюджет: {lead_data['budget']}")
                    break
            if lead_data.get("budget"):
                break

        logger.info(f"Извлечены данные лида: {lead_data}")
        return lead_data
