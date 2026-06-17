from aiogram import Bot
from app.db.models import Lead
from loguru import logger

class LeadSender:
    """Отправляет карточку лида менеджеру в Telegram"""

    def __init__(self, bot: Bot, manager_chat_id: str | int):
        self.bot = bot
        self.manager_chat_id = manager_chat_id

    async def send_lead(self, lead: Lead, dialog_summary: str = "") -> bool:
        """
        Отправляет карточку лида менеджеру

        Args:
            lead: Объект лида из БД
            dialog_summary: Краткое резюме диалога (опционально)

        Returns:
            True если успешно отправлено
        """
        message = self._format_lead_message(lead, dialog_summary)

        try:
            await self.bot.send_message(
                chat_id=self.manager_chat_id,
                text=message,
                parse_mode="HTML"
            )
            logger.info(f"Лид отправлен менеджеру: {lead.id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки лида менеджеру: {e}")
            return False

    def _format_lead_message(self, lead: Lead, dialog_summary: str) -> str:
        """Форматирует сообщение с карточкой лида"""
        message = f"""
 <b>Новый лид!</b>

👤 <b>Имя:</b> {lead.name or 'Не указано'}
 <b>Интерес:</b> {lead.interest or 'Не указано'}
 <b>Бюджет:</b> {lead.budget or 'Не указано'}
 <b>Контакт:</b> {lead.contact or 'Не указано'}
"""

        if dialog_summary:
            message += f"\n📝 <b>Резюме диалога:</b>\n{dialog_summary}\n"

        message += f"\n <b>Время:</b> {lead.created_at.strftime('%d.%m.%Y %H:%M')}"

        return message
