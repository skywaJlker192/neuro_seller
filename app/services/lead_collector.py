from app.db.repositories import LeadRepository
from app.db.database import async_session
from sqlalchemy import select
from app.db.models import Lead
from loguru import logger

class LeadCollector:
    """Анализирует диалог и собирает информацию о клиенте"""

    def __init__(self):
        self.lead_repo = LeadRepository()

    async def check_and_collect_lead(self, user_id: int, history: list[dict]) -> Lead | None:
        """
        Проверяет, собрана ли вся необходимая информация о клиенте

        Args:
            user_id: ID пользователя в БД
            history: История диалога

        Returns:
            Lead объект если лид собран, иначе None
        """
        # Проверяем, есть ли уже лид для этого пользователя
        existing_lead = await self.lead_repo.get_by_user_id(user_id)

        if existing_lead and existing_lead.sent_to_manager:
            # Лид уже отправлен менеджеру, не собираем повторно
            return None

        # Анализируем историю диалога для извлечения информации
        lead_data = await self._extract_lead_info(history)

        if lead_data and self._is_lead_complete(lead_data):
            # Сохраняем или обновляем лид
            if existing_lead:
                lead = await self.lead_repo.update(existing_lead.id, **lead_data)
            else:
                lead = await self.lead_repo.create(user_id=user_id, **lead_data)

            logger.info(f"Лид собран для пользователя {user_id}: {lead}")
            return lead

        return None

    async def _extract_lead_info(self, history: list[dict]) -> dict | None:
        """
        Извлекает информацию о лиде из истории диалога
        В MVP используем простую логику, в будущем можно подключить LLM для парсинга
        """
        # Собираем все сообщения пользователя
        user_messages = [msg["content"] for msg in history if msg["role"] == "user"]

        if not user_messages:
            return None

        # Простой парсинг (в будущем можно улучшить с помощью LLM)
        lead_data = {}

        # Ищем имя (простая эвристика)
        for msg in user_messages:
            msg_lower = msg.lower()
            if "меня зовут" in msg_lower or "мое имя" in msg_lower:
                # Извлекаем имя после ключевых слов
                parts = msg.split()
                for i, part in enumerate(parts):
                    if part.lower() in ["зовут", "имя"] and i + 1 < len(parts):
                        lead_data["name"] = parts[i + 1].capitalize()
                        break

        # Ищем контакт (телефон или email)
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

        return lead_data if lead_data else None

    def _is_lead_complete(self, lead_data: dict) -> bool:
        """Проверяет, собрана ли вся необходимая информация"""
        required_fields = ["name", "contact"]
        return all(field in lead_data for field in required_fields)
