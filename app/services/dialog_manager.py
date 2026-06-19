from app.llm.yandex_client import YandexGPTClient
from app.services.prompt_builder import PromptBuilder
from app.services.lead_collector import LeadCollector
from app.services.fallback import get_fallback_response
from app.services.google_sheets import sheets_exporter
from app.niche.loader import load_niche
from app.db.repositories import UserRepository, DialogRepository, LeadRepository
from loguru import logger
import re
import asyncio


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

    def _analyze_history(self, history: list, current_message: str) -> dict:
        """
        Анализирует ПОСЛЕДНИЕ 3 сообщения диалога (не всю историю!)
        """
        result = {
            "has_interest": False,
            "has_contact": False,
            "has_budget": False,
            "has_name": False,
            "interest_text": None,
            "contact_text": None,
            "budget_text": None,
            "name_text": None,
        }

        # ВАЖНО: Берём ТОЛЬКО последние 3 сообщения + текущее
        recent_history = history[-3:] if len(history) >= 3 else history
        all_user_texts = [msg["content"] for msg in recent_history if msg["role"] == "user"]
        all_user_texts.append(current_message)
        full_text = " ".join(all_user_texts).lower()

        logger.info(f"🔍 Анализирую {len(all_user_texts)} свежих сообщений: {full_text[:100]}...")

        # 1. Проверяем ИНТЕРЕС
        interest_keywords = [
            "хочу купить", "купить", "заказать", "покупаю",
            "хочу записаться", "записаться", "запись", "забронировать",
            "интересует", "ищу", "нужен", "нужна", "нужно", "хочу",
            "расскажите про", "покажи", "дайте", "оформить"
        ]

        product_patterns = [
            r'iphone', r'айфон', r'macbook', r'airpods',
            r'парфюм', r'крем', r'шампунь', r'косметика',
            r'диван', r'кроссовки', r'ноутбук', r'телефон',
            r'гантели', r'велосипед', r'беговая\s+дорожк',
            r'стрижк', r'маникюр', r'массаж', r'педикюр',
            r'окрашивани', r'чистк', r'пилинг',
            r'тормозн', r'двигател', r'подвеск', r'амортизатор',
            r'масло моторное', r'аккумулятор', r'шин',
            r'джинс', r'levis', r'nike', r'adidas'
        ]

        for kw in interest_keywords:
            if kw in full_text:
                result["has_interest"] = True
                result["interest_text"] = kw
                break

        if not result["has_interest"]:
            for pattern in product_patterns:
                if re.search(pattern, full_text, re.IGNORECASE):
                    result["has_interest"] = True
                    result["interest_text"] = pattern
                    break

        # 2. Проверяем КОНТАКТ
        phone_patterns = [
            r'\+7\d{10}',
            r'8\d{10}',
            r'\b\d{10,11}\b',
        ]
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'

        for pattern in phone_patterns:
            if re.search(pattern, full_text.replace(" ", "")):
                result["has_contact"] = True
                result["contact_text"] = "телефон"
                break

        if not result["has_contact"] and re.search(email_pattern, full_text):
            result["has_contact"] = True
            result["contact_text"] = "email"

        # 3. Проверяем БЮДЖЕТ
        budget_patterns = [
            r'бюджет[:\s]*\d+',
            r'\d+\s*(руб|рублей|тыс|к|₽)',
            r'за\s+\d+',
            r'до\s+\d+\s*руб',
            r'\d+\s*[-–]\s*\d+',
        ]

        for pattern in budget_patterns:
            if re.search(pattern, full_text):
                result["has_budget"] = True
                result["budget_text"] = "бюджет"
                break

        # 4. Проверяем ИМЯ
        name_patterns = [
            r'имя[:\s]+\w+',
            r'меня зовут\s+\w+',
            r'мое имя\s+\w+',
            r'зовут\s+\w+',
        ]

        for pattern in name_patterns:
            if re.search(pattern, full_text):
                result["has_name"] = True
                result["name_text"] = "имя"
                break

        return result

    async def _get_llm_response(self, user_message: str, history: list, niche_config) -> str:
        """Получает ответ от YandexGPT"""
        prompt_builder = PromptBuilder(niche_config)
        system_prompt = prompt_builder.build_system_prompt()

        history_text = self._format_history(history)

        # Анализируем что уже есть в диалоге
        analysis = self._analyze_history(history, user_message)
        logger.info(f"📊 Анализ диалога: {analysis}")

        # Формируем инструкцию что спросить
        missing_parts = []
        if not analysis["has_interest"]:
            missing_parts.append("интерес (что хочет купить/заказать)")
        if not analysis["has_contact"]:
            missing_parts.append("контакт (телефон или email)")
        if not analysis["has_budget"]:
            missing_parts.append("бюджет")
        if not analysis["has_name"]:
            missing_parts.append("имя")

        # Строим инструкцию для LLM
        if missing_parts:
            missing_instruction = f"""
⚠️ ВАЖНО — ЧТО УЖЕ ЕСТЬ В ДИАЛОГЕ:
- Интерес (что хочет): {'✅ ДА' if analysis['has_interest'] else '❌ НЕТ'}
- Контакт (телефон/email): {'✅ ДА' if analysis['has_contact'] else '❌ НЕТ'}
- Бюджет: {'✅ ДА' if analysis['has_budget'] else '❌ НЕТ'}
- Имя: {'✅ ДА' if analysis['has_name'] else '❌ НЕТ'}

🎯 ЧТО НУЖНО ДОСОБРАТЬ: {', '.join(missing_parts)}

ТВОЯ ЗАДАЧА:
1. Ответь на вопрос клиента (кратко, по делу)
2. ЕСТЕСТВЕННО спроси то, чего не хватает — ОДНИМ вопросом
3. НЕ пиши шаблонные фразы типа "укажите ваш телефон"
4. Спроси как живой менеджер, например:
   - Если нет контакта: "На какой номер записать?" или "Как с вами связаться?"
   - Если нет бюджета: "На какую сумму рассчитываете?" или "Какой у вас бюджет?"
   - Если нет имени: "Как к вам обращаться?"
   - Если нет интереса: "Что именно вас интересует?"

ВАЖНО: За один раз спрашивай ТОЛЬКО ОДНО — самое важное.
Приоритет: контакт > бюджет > имя
"""
        else:
            missing_instruction = """
✅ ВСЕ ДАННЫЕ СОБРАНЫ! Просто подтверди и жди создания лида.
"""

        full_prompt = f"""ИСТОРИЯ ДИАЛОГА:
{history_text}

СООБЩЕНИЕ КЛИЕНТА:
{user_message}
{missing_instruction}
ПРАВИЛА ОТВЕТА:
1. НЕ повторяй информацию которую уже дал в предыдущих сообщениях
2. НЕ пиши шаблонные фразы "напишите: хочу купить..." или "чтобы оформить..."
3. Отвечай ЕСТЕСТВЕННО как живой менеджер
4. Будь краток — 1-2 предложения
5. Если клиент просит скидку — отвечай что это решает менеджер
6. Если чего-то не хватает — спроси ОДНИМ естественным вопросом

Ответь кратко и естественно."""

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
            error_str = str(e).lower()
            logger.error(f"Ошибка YandexGPT: {e}")

            # Сетевая ошибка — пробуем ещё раз
            if "network" in error_str or "unreachable" in error_str or "winerror" in error_str or "clienterror" in error_str:
                logger.warning("🔄 Сетевая ошибка, пробую ещё раз...")
                try:
                    await asyncio.sleep(2)
                    bot_answer = await self.llm.generate(
                        prompt=full_prompt,
                        system_prompt=system_prompt,
                        temperature=0.7,
                        max_tokens=800
                    )
                    if not bot_answer:
                        bot_answer = "Извините, технические проблемы. Попробуйте написать через минуту."
                except Exception as retry_error:
                    logger.error(f"❌ Повторная ошибка: {retry_error}")
                    bot_answer = "Извините, технический перерыв. Ответим чуть позже!"
            else:
                bot_answer = "Извините, технический перерыв. Ответим чуть позже!"

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
