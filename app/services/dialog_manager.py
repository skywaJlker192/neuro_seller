from app.llm.yandex_client import YandexGPTClient
from app.services.prompt_builder import PromptBuilder
from app.services.lead_collector import LeadCollector
from app.services.fallback import get_fallback_response
from app.services.google_sheets import sheets_exporter
from app.niche.loader import load_niche
from app.db.repositories import UserRepository, DialogRepository, LeadRepository
from loguru import logger


class DialogManager:
    """Управляет диалогом с пользователем"""

    def __init__(self, bot):
        self.bot = bot
        self.llm = YandexGPTClient()
        self.lead_collector = LeadCollector()

    async def process_message(self, tg_user_id: int, user_message: str, niche_file: str) -> str:
        """Обрабатывает сообщение пользователя"""

        niche_config = load_niche(niche_file)

        user_repo = UserRepository()
        user = await user_repo.get_or_create(tg_user_id)

        dialog_repo = DialogRepository()
        history = await dialog_repo.get_recent_messages(user.id, limit=10)

        await dialog_repo.save_message(user.id, "user", user_message)

        # СНАЧАЛА пробуем создать лид
        full_history = history + [
            {"role": "user", "content": user_message}
        ]

        lead = await self.lead_collector.check_and_collect_lead(
            user_id=user.id,
            history=full_history
        )

        # Если лид СОЗДАН
        if lead:
            logger.info(f"✅ ЛИД СОЗДАН: {lead}")

            # Если это НОВЫЙ лид (только что создан)
            if not lead.sent_to_manager:
                # Отправляем менеджеру
                await self._send_lead_to_manager(lead, niche_config)

                # Экспорт в Google Sheets
                lead_data = {
                    "tg_user_id": user.tg_id,
                    "name": lead.name,
                    "interest": lead.interest,
                    "budget": lead.budget,
                    "contact": lead.contact
                }

                await sheets_exporter.add_lead(
                    lead_data,
                    niche_config.business_name,
                    sent_to_manager=True
                )

                # Обновляем статус
                lead_repo = LeadRepository()
                await lead_repo.update(lead.id, sent_to_manager=True)

            # ОТВЕЧАЕМ что заявка оформлена (БЕЗ шаблонных фраз!)
            bot_answer = "Контакт получен. Заявка оформлена."
        else:
            # Лид НЕ создан — даём обычный ответ
            logger.info("❌ Лид НЕ создан — даю информацию")
            bot_answer = await self._get_llm_response(user_message, history, niche_config)

        await dialog_repo.save_message(user.id, "assistant", bot_answer)
        return bot_answer

    async def _get_llm_response(self, user_message: str, history: list, niche_config) -> str:
        """Получает ответ от YandexGPT"""
        prompt_builder = PromptBuilder(niche_config)
        system_prompt = prompt_builder.build_system_prompt()

        history_text = self._format_history(history)
        full_prompt = f"""ИСТОРИЯ ДИАЛОГА:
{history_text}

СООБЩЕНИЕ КЛИЕНТА:
{user_message}

ВАЖНО:
- Если клиент указал бюджет — ИСПОЛЬЗУЙ его (например: "В вашем бюджете 5000 руб...")
- Дай информацию о товаре
- Если не хватает данных — попроси ТОЛЬКО то, чего нет (телефон ИЛИ бюджет)
- НЕ пиши шаблонные фразы "напишите: хочу купить..." или "укажите ваш email"
- Будь краток и конкретен

Ответь кратко и по делу (2-3 предложения)."""

        try:
            bot_answer = await self.llm.generate(
                prompt=full_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=800
            )

            if not bot_answer:
                bot_answer = get_fallback_response()

        except Exception as e:
            logger.error(f"Ошибка YandexGPT: {e}")
            bot_answer = get_fallback_response()

        return bot_answer

    def _format_history(self, history: list) -> str:
        """Форматирует историю диалога"""
        if not history:
            return "(диалог только начался)"

        lines = []
        for msg in history:
            role = "Клиент" if msg["role"] == "user" else "Менеджер"
            lines.append(f"{role}: {msg['content']}")

        return "\n".join(lines)

    async def _send_lead_to_manager(self, lead, niche_config):
        """Отправляет лид менеджеру"""
        from app.config import settings

        manager_id = settings.MANAGER_CHAT_ID

        if lead.user_id and manager_id and str(lead.user_id) == str(manager_id):
            logger.info("📢 Пользователь = админ, пропускаем уведомление")
            return

        if not manager_id:
            logger.warning("MANAGER_CHAT_ID не указан")
            return

        text = f"🔥 <b>НОВЫЙ ЛИД!</b>\n\n"
        text += f"📋 <b>Ниша:</b> {niche_config.business_name}\n\n"
        text += "<b>Данные клиента:</b>\n"

        if lead.name:
            text += f"• Имя: {lead.name}\n"
        if lead.contact:
            text += f"• Контакт: {lead.contact}\n"
        if lead.interest:
            text += f"• Интерес: {lead.interest}\n"
        if lead.budget:
            text += f"• Бюджет: {lead.budget}\n"

        try:
            await self.bot.send_message(manager_id, text, parse_mode="HTML")
            logger.info(f"✅ Лид отправлен менеджеру {manager_id}")
        except Exception as e:
            logger.error(f"Не удалось отправить лид: {e}")
