from app.llm.yandex_client import YandexGPTClient
from app.services.prompt_builder import PromptBuilder
from app.services.lead_collector import LeadCollector
from app.services.fallback import get_fallback_response
from app.services.product_info import ProductInfoSearcher
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
        self.product_searcher = ProductInfoSearcher()

    async def process_message(self, tg_user_id: int, user_message: str, niche_file: str) -> str:
        """Обрабатывает сообщение пользователя"""

        # Загружаем конфигурацию ниши
        niche_config = load_niche(niche_file)

        # Получаем или создаём пользователя
        user_repo = UserRepository()
        user = await user_repo.get_or_create(tg_user_id)

        # Получаем историю диалога
        dialog_repo = DialogRepository()
        history = await dialog_repo.get_recent_messages(user.id, limit=10)

        # Сохраняем сообщение пользователя
        await dialog_repo.save_message(user.id, "user", user_message)

        # Проверяем, не просит ли пользователь подробные характеристики
        if self._is_detailed_info_request(user_message):
            product_name = self._extract_product_name(user_message, history)
            if product_name:
                detailed_info = await self.product_searcher.search_product_info(product_name)
                if detailed_info:
                    bot_answer = detailed_info
                else:
                    bot_answer = await self._get_llm_response(user_message, history, niche_config)
            else:
                bot_answer = await self._get_llm_response(user_message, history, niche_config)
        else:
            bot_answer = await self._get_llm_response(user_message, history, niche_config)

        # Сохраняем ответ бота
        await dialog_repo.save_message(user.id, "assistant", bot_answer)

        # Пытаемся собрать лид
        try:
            full_history = history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": bot_answer}
            ]

            lead = await self.lead_collector.check_and_collect_lead(
                user_id=user.id,
                history=full_history
            )

            if lead and not lead.sent_to_manager:
                logger.info(f"🔥 НОВЫЙ ЛИД: {lead}")

                # Отправляем лид менеджеру в Telegram
                await self._send_lead_to_manager(lead, niche_config)

                # ЭКСПОРТ В GOOGLE SHEETS
                lead_data = {
                    "tg_user_id": user.tg_id,
                    "name": lead.name,
                    "interest": lead.interest,
                    "budget": lead.budget,
                    "contact": lead.contact
                }

                logger.info(f"📊 Экспорт в Google Sheets: {lead_data}")
                export_result = await sheets_exporter.add_lead(
                    lead_data,
                    niche_config.business_name,
                    sent_to_manager=True
                )

                if export_result:
                    logger.success("✅ Лид добавлен в Google Sheets")
                else:
                    logger.error("❌ Ошибка экспорта в Google Sheets")

                # Обновляем статус лида
                lead_repo = LeadRepository()
                await lead_repo.update(lead.id, sent_to_manager=True)

                logger.info(f"Лид отправлен менеджеру и добавлен в Google Sheets: {lead}")

        except Exception as e:
            logger.error(f"Ошибка обработки лида: {e}")
            import traceback
            logger.error(traceback.format_exc())

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

Ответь клиенту естественно, как живой менеджер."""

        try:
            bot_answer = await self.llm.generate(
                prompt=full_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=1000
            )

            if not bot_answer:
                logger.warning("YandexGPT не ответил, используем fallback")
                bot_answer = get_fallback_response()

        except Exception as e:
            logger.error(f"Ошибка YandexGPT: {e}")
            bot_answer = get_fallback_response()

        return bot_answer

    def _is_detailed_info_request(self, message: str) -> bool:
        """Проверяет, просит ли пользователь подробную информацию"""
        keywords = [
            "подробные характеристики",
            "детальные характеристики",
            "полные характеристики",
            "все характеристики",
            "технические характеристики",
            "specs",
            "specifications",
            "подробно о",
            "детально о",
            "расскажи всё о",
            "подробная информация"
        ]

        message_lower = message.lower()
        return any(keyword in message_lower for keyword in keywords)

    def _extract_product_name(self, message: str, history: list) -> str:
        """Извлекает название товара из сообщения"""
        ignore_words = [
            "покажи", "найди", "расскажи", "характеристики",
            "подробные", "детальные", "полные", "информацию",
            "о", "об", "на", "товар", "продукт"
        ]

        words = message.split()
        product_words = [w for w in words if w.lower() not in ignore_words]

        if product_words:
            return " ".join(product_words[-4:])

        for msg in reversed(history):
            if msg["role"] == "user":
                return msg["content"][:50]

        return ""

    def _format_history(self, history: list) -> str:
        """Форматирует историю диалога в текст"""
        if not history:
            return "(диалог только начался)"

        lines = []
        for msg in history:
            role = "Клиент" if msg["role"] == "user" else "Менеджер"
            lines.append(f"{role}: {msg['content']}")

        return "\n".join(lines)

    async def _send_lead_to_manager(self, lead, niche_config):
        """Отправляет лид менеджеру (НЕ пользователю!)"""
        from app.config import settings

        manager_id = settings.MANAGER_CHAT_ID
        if not manager_id:
            logger.warning("MANAGER_CHAT_ID не указан, лид не отправлен")
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
            # ОТПРАВЛЯЕМ ТОЛЬКО АДМИНУ (manager_id)
            await self.bot.send_message(manager_id, text, parse_mode="HTML")
            logger.info(f"✅ Лид отправлен менеджеру {manager_id}")
        except Exception as e:
            logger.error(f"Не удалось отправить лид менеджеру: {e}")
