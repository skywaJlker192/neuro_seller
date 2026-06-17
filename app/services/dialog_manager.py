from app.db.repositories import UserRepository, DialogRepository, LeadRepository
from app.llm.yandex_client import YandexGPTClient
from app.llm.exceptions import LLMError
from app.services.prompt_builder import PromptBuilder
from app.services.fallback import handle_llm_error
from app.services.lead_collector import LeadCollector
from app.services.lead_sender import LeadSender
from app.niche.loader import load_niche
from app.config import settings
from loguru import logger
from aiogram import Bot

class DialogManager:
    """Управляет диалогом: загружает контекст, вызывает LLM, сохраняет историю"""

    def __init__(self, bot: Bot):
        self.llm_client = YandexGPTClient()
        self.user_repo = UserRepository()
        self.dialog_repo = DialogRepository()
        self.lead_collector = LeadCollector()
        self.lead_sender = LeadSender(bot, settings.MANAGER_CHAT_ID)

    async def process_message(self, tg_user_id: int, user_message: str, niche_file: str) -> str:
        """
        Обрабатывает сообщение от пользователя

        Returns:
            Ответ бота
        """
        try:
            # 1. Получаем или создаём пользователя
            user = await self.user_repo.get_or_create(tg_user_id)

            # 2. Загружаем конфиг ниши
            niche = load_niche(niche_file)

            # 3. Загружаем историю диалога (последние N сообщений)
            history = await self.dialog_repo.get_recent_messages(
                user.id,
                limit=settings.MAX_CONTEXT_MESSAGES
            )

            # 4. Формируем промпт
            system_prompt = PromptBuilder.build_system_prompt(niche)
            messages = PromptBuilder.build_messages_for_llm(system_prompt, history, user_message)

            # 5. Отправляем в YandexGPT
            bot_response = await self.llm_client.chat(messages)

            # 6. Сохраняем сообщение пользователя и ответ бота в БД
            await self.dialog_repo.save_message(user.id, "user", user_message)
            await self.dialog_repo.save_message(user.id, "assistant", bot_response)

            # 7. Проверяем, собран ли лид
            updated_history = history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": bot_response}
            ]
            lead = await self.lead_collector.check_and_collect_lead(user.id, updated_history)

            # 8. Если лид собран — отправляем менеджеру
            if lead and not lead.sent_to_manager:
                # Формируем резюме диалога
                dialog_summary = self._create_dialog_summary(updated_history)
                await self.lead_sender.send_lead(lead, dialog_summary)

                # Отмечаем лид как отправленный
                await self.lead_collector.lead_repo.update(lead.id, sent_to_manager=True)

                logger.info(f"Лид {lead.id} отправлен менеджеру")

            return bot_response

        except LLMError as e:
            logger.error(f"Ошибка LLM для пользователя {tg_user_id}: {e}")
            # Сохраняем сообщение пользователя даже если LLM упал
            try:
                user = await self.user_repo.get_or_create(tg_user_id)
                await self.dialog_repo.save_message(user.id, "user", user_message)
            except Exception as db_err:
                logger.error(f"Не удалось сохранить сообщение: {db_err}")

            return await handle_llm_error(e)

        except Exception as e:
            logger.error(f"Неожиданная ошибка в DialogManager: {e}")
            return "⚠️ Произошла ошибка. Попробуйте ещё раз или напишите позже."

    def _create_dialog_summary(self, history: list[dict]) -> str:
        """Создаёт краткое резюме диалога для менеджера"""
        # Берём последние 6 сообщений для резюме
        recent = history[-6:] if len(history) > 6 else history

        summary_parts = []
        for msg in recent:
            role = "Клиент" if msg["role"] == "user" else "Бот"
            summary_parts.append(f"{role}: {msg['content']}")

        return "\n".join(summary_parts)
