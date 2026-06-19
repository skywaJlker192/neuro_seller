from app.db.repositories import LeadRepository
from app.db.database import async_session
from sqlalchemy import select
from app.db.models import Lead
from loguru import logger
import re


class LeadCollector:
    """УНИВЕРСАЛЬНЫЙ сборщик лидов для любой ниши (товары + услуги)"""

    def __init__(self):
        self.lead_repo = LeadRepository()

    async def check_and_collect_lead(self, user_id: int, history: list[dict]) -> Lead | None:
        """
        Создаёт лид ТОЛЬКО когда есть ВСЕ данные: интерес + контакт + бюджет
        """
        logger.info(f"🔍 Проверка лида для пользователя {user_id}")
        logger.info(f"История диалога: {len(history)} сообщений")

        # Получаем все сообщения пользователя
        user_messages = [msg for msg in history if msg["role"] == "user"]

        if not user_messages:
            logger.info("Нет сообщений пользователя")
            return None

        last_message = user_messages[-1]["content"]
        logger.info(f"Последнее сообщение: {last_message}")

        # Получаем все лиды пользователя
        all_user_leads = await self._get_all_user_leads(user_id)

        # ВАЖНО: Берём ТОЛЬКО СВЕЖИЕ сообщения (после последнего лида)
        if all_user_leads:
            last_lead = all_user_leads[-1]
            logger.info(f"Последний лид ID={last_lead.id} создан: {last_lead.created_at}")

            # Берём ТОЛЬКО последние 2 сообщения пользователя (после последнего лида)
            relevant_messages = user_messages[-2:]
            logger.info(f"Анализирую {len(relevant_messages)} СВЕЖИХ сообщений")
        else:
            # Первый лид — берём последние 2-3 сообщения
            relevant_messages = user_messages[-3:] if len(user_messages) >= 3 else user_messages
            logger.info(f"Первый лид — анализирую {len(relevant_messages)} сообщений")

        # Извлекаем данные ТОЛЬКО из свежих сообщений
        lead_data = self._extract_from_messages(relevant_messages)
        logger.info(f"Извлечённые данные: {lead_data}")

        # ВАЖНО: Проверяем наличие ВСЕХ обязательных полей
        missing_fields = []

        if not lead_data.get("interest"):
            missing_fields.append("интерес")

        if not lead_data.get("contact"):
            missing_fields.append("контакт")

        if not lead_data.get("budget"):
            missing_fields.append("бюджет")

        if missing_fields:
            logger.info(f"❌ Не хватает: {', '.join(missing_fields)} - НЕ создаю лид")
            return None

        logger.info(f"✅ Все данные есть: {lead_data}")

        # Проверяем намерение
        if not self._has_intent_in_message(last_message):
            logger.info("❌ Нет намерения")
            return None

        # Проверяем, есть ли уже лид с таким интересом
        current_interest = lead_data.get("interest", "").lower()
        existing_lead_with_same_interest = None

        for lead in all_user_leads:
            lead_interest = (lead.interest or "").lower()
            if current_interest and lead_interest and current_interest in lead_interest:
                existing_lead_with_same_interest = lead
                break

        # Создаём или обновляем лид
        if existing_lead_with_same_interest:
            lead = existing_lead_with_same_interest
            update_data = {}

            if not lead.interest and lead_data.get("interest"):
                update_data["interest"] = lead_data["interest"]
            if not lead.contact and lead_data.get("contact"):
                update_data["contact"] = lead_data["contact"]
            if not lead.name and lead_data.get("name"):
                update_data["name"] = lead_data["name"]
            if not lead.budget and lead_data.get("budget"):
                update_data["budget"] = lead_data["budget"]

            if update_data:
                logger.info(f"Обновляем лид {lead.id}: {update_data}")
                lead = await self.lead_repo.update(lead.id, **update_data)
                logger.success(f"✅ Лид обновлён: {lead}")
                return lead
            else:
                logger.info("Нет новых данных")
                return lead

        elif all_user_leads:
            last_lead = all_user_leads[-1]
            last_interest = (last_lead.interest or "").lower()

            if current_interest and last_interest and current_interest != last_interest:
                logger.info(f"Новый интерес '{current_interest}' - создаю новый лид")
                lead = await self.lead_repo.create(user_id=user_id, **lead_data)
                logger.success(f"✅ Новый лид создан: {lead}")
                return lead
            else:
                logger.info(f"Обновляю последний лид {last_lead.id}")
                lead = await self.lead_repo.create(user_id=user_id, **lead_data)
                logger.success(f"✅ Лид создан: {lead}")
                return lead
        else:
            logger.info(f"Создаём ПЕРВЫЙ лид")
            lead = await self.lead_repo.create(user_id=user_id, **lead_data)
            logger.success(f"✅ Первый лид создан: {lead}")
            return lead

    def _has_intent_in_message(self, message: str) -> bool:
        msg_lower = message.lower().strip()

        category_keywords = [
            "косметика", "электроника", "спорттовары", "книги", "мебель",
            "одежда", "обувь", "игрушки", "продукты", "помощь", "меню",
            "каталог", "категории", "старт", "назад", "перезапустить"
        ]

        for keyword in category_keywords:
            if keyword in msg_lower:
                return False

        intent_keywords = [
            "хочу купить", "купить", "заказать", "покупаю",
            "интересует", "ищу", "нужен", "нужна", "нужно", "хочу",
            "расскажите про", "покажи", "дайте"
        ]

        for keyword in intent_keywords:
            if keyword in msg_lower:
                parts = msg_lower.split(keyword, 1)
                if len(parts) > 1 and parts[1].strip():
                    remaining_text = parts[1].strip()
                    if not re.match(r'^[\d\s\+\-]+$', remaining_text):
                        return True

        product_patterns = [
            r'iphone', r'айфон', r'macbook', r'airpods',
            r'парфюм', r'крем', r'шампунь', r'косметика',
            r'диван', r'кроссовки', r'ноутбук', r'телефон',
            r'гантели', r'велосипед', r'беговая\s+дорожк',
            r'мишк', r'игрушк', r'учебник', r'книга',
            r'macbook\s+air', r'nike', r'adidas', r'levis'
        ]

        for pattern in product_patterns:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return True

        return False

    def _extract_from_messages(self, messages: list[dict]) -> dict:
        """Извлекает данные ТОЛЬКО из предоставленных сообщений"""
        lead_data = {}

        if not messages:
            return lead_data

        logger.info(f"Анализирую {len(messages)} свежих сообщений")

        # Извлекаем интерес из последнего сообщения
        last_msg = messages[-1]["content"]
        interest = self._extract_interest(last_msg)
        if interest:
            lead_data["interest"] = interest

        # Если не нашли в последнем - ищем во всех свежих
        if not interest:
            for msg in reversed(messages):
                interest = self._extract_interest(msg["content"])
                if interest:
                    lead_data["interest"] = interest
                    break

        # Извлекаем контакт из ВСЕХ свежих сообщений
        for msg in messages:
            contact = self._extract_contact(msg["content"])
            if contact and not lead_data.get("contact"):
                lead_data["contact"] = contact
                break

        # Извлекаем бюджет из ВСЕХ свежих сообщений
        for msg in messages:
            budget = self._extract_budget(msg["content"])
            if budget and not lead_data.get("budget"):
                lead_data["budget"] = budget
                break

        # Извлекаем имя из ВСЕХ свежих сообщений
        for msg in messages:
            name = self._extract_name(msg["content"])
            if name and not lead_data.get("name"):
                lead_data["name"] = name
                break

        logger.info(f"Итоговые данные: {lead_data}")
        return lead_data

    def _extract_interest(self, message: str) -> str | None:
        msg_lower = message.lower()

        intent_keywords = [
            "хочу купить", "купить", "заказать", "интересует", "ищу", "нужен", "покупаю",
            "нужна", "нужно", "хочу", "хочу оформить", "оформить"
        ]

        for kw in intent_keywords:
            if kw in msg_lower:
                parts = message.split(kw, 1)
                if len(parts) > 1:
                    interest_text = parts[1].strip()

                    # УДАЛЯЕМ из интереса лишнее
                    interest_text = re.sub(r'[\+\d\s\-\(\)]{10,}', '', interest_text)
                    interest_text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', interest_text)
                    interest_text = re.sub(r'бюджет[:\s]*\d+', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\d+\s*(к|тыс|руб)?\s*(до|за)\s*\d+', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'за\s+\d+', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\bимя\b', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\bтелефон\b', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\bпочта\b', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\bemail\b', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\bконтакт\b', '', interest_text, flags=re.IGNORECASE)

                    interest_text = interest_text.strip()
                    interest_text = re.sub(r'\s+', ' ', interest_text)
                    interest_text = re.sub(r'[,\s]+$', '', interest_text)

                    if interest_text:
                        return f"{kw} {interest_text}"
                return message.strip()

        product_patterns = [
            r'macbook\s+air', r'iphone', r'айфон', r'macbook',
            r'кроссовки', r'nike', r'adidas', r'levis'
        ]

        for pattern in product_patterns:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                clean_text = message
                clean_text = re.sub(r'[\+\d\s\-\(\)]{10,}', '', clean_text)
                clean_text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', clean_text)
                clean_text = re.sub(r'бюджет[:\s]*\d+', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'за\s+\d+', '', clean_text, flags=re.IGNORECASE)
                clean_text = clean_text.strip()
                clean_text = re.sub(r'\s+', ' ', clean_text)
                return clean_text if clean_text else message.strip()

        return None

    def _extract_contact(self, message: str) -> str | None:
        msg_lower = message.lower()

        # Ищем email
        email_patterns = [
            r'(?:почта|email|майл|e-mail)[:\s]*([\w\.-]+@[\w\.-]+\.\w+)',
            r'([\w\.-]+@[\w\.-]+\.\w+)',
        ]

        for pattern in email_patterns:
            email_match = re.search(pattern, msg_lower, re.IGNORECASE)
            if email_match:
                email = email_match.group(1)
                if '@' in email and '.' in email:
                    return email

        # Ищем телефон
        phone_patterns = [
            r'(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
            r'(\+7|8)\d{10}',
            r'номер[:\s]+(\+?7?\d{10,11})',
            r'телефон[:\s]+(\+?7?\d{10,11})',
            r'мой номер[:\s]*(\+?7?\d{10,11})',
            r'контакт[:\s]*(\+?7?\d{10,11})',
            r'\b\d{10,11}\b',
        ]

        msg_clean = message.replace(" ", "")
        for pattern in phone_patterns:
            phone_match = re.search(pattern, msg_clean)
            if phone_match:
                phone = phone_match.group(0)

                if len(phone) == 11 and phone.isdigit():
                    if phone.startswith('8'):
                        phone = '+7' + phone[1:]
                    elif phone.startswith('9'):
                        phone = '+7' + phone
                elif len(phone) == 10 and phone.isdigit():
                    if phone.startswith('8'):
                        phone = '+7' + phone[1:]
                    elif phone.startswith('9'):
                        phone = '+7' + phone
                    else:
                        phone = '+7' + phone

                return phone

        return None

    def _extract_budget(self, message: str) -> str | None:
        msg_lower = message.lower()

        budget_patterns = [
            r'бюджет[:\s]*(\d+[\s\-]?\d*)',
            r'за\s+(\d+[\s\-]?\d*)\s*(руб|рублей|тыс|к)?',
            r'до\s+(\d+[\s\-]?\d*)\s*руб',
            r'(\d+[\s\-]?\d*)\s*руб',
            r'цена[:\s]*(\d+[\s\-]?\d*)',
            r'от\s+(\d+)\s*(к|тыс)?\s*(до|за)\s*(\d+)\s*(к|тыс|руб)?',
            r'(\d+)\s*(к|тыс)\s*[-–]\s*(\d+)\s*(к|тыс)',
        ]

        for pattern in budget_patterns:
            budget_match = re.search(pattern, msg_lower)
            if budget_match:
                if pattern.startswith(r'за\s+'):
                    price = budget_match.group(1)
                    budget = f"{price} руб"
                elif pattern.startswith(r'от\s+'):
                    min_price = budget_match.group(1)
                    max_price = budget_match.group(4)
                    if budget_match.group(2) and budget_match.group(2) in ['к', 'тыс']:
                        min_price = str(int(min_price) * 1000)
                    if budget_match.group(5) and budget_match.group(5) in ['к', 'тыс']:
                        max_price = str(int(max_price) * 1000)
                    budget = f"{min_price}-{max_price} руб"
                elif 'к' in pattern or 'тыс' in pattern:
                    groups = budget_match.groups()
                    if len(groups) >= 2:
                        min_price = groups[0]
                        max_price = groups[1]
                        for g in groups:
                            if g in ['к', 'тыс']:
                                min_price = str(int(min_price) * 1000)
                                max_price = str(int(max_price) * 1000)
                                break
                        budget = f"{min_price}-{max_price} руб"
                else:
                    budget = budget_match.group(0)

                return budget

        return None

    def _extract_name(self, message: str) -> str | None:
        """Извлекает имя из сообщения"""
        msg_lower = message.lower()

        # Ищем имя — РАСШИРЕННЫЕ ПАТТЕРНЫ
        name_patterns = [
            r'(?:имя|меня зовут|мое имя|зовут)[:\s]+(\w+)',  # имя: валентин, меня зовут валентин
            r'имя\s+(\w+)',  # имя валентин (без двоеточия)
            r',\s*(\w+),\s*(?:телефон|бюджет|контакт)',  # , валентин, телефон
            r'\s(\w+)\s*,\s*бюджет',  # валентин, бюджет
        ]

        for pattern in name_patterns:
            name_match = re.search(pattern, msg_lower)
            if name_match:
                name = name_match.group(1)
                # Проверяем что это имя (только буквы, не цифры, не служебные слова)
                if (name.isalpha() and len(name) > 1 and
                    not name.isdigit() and
                    name not in ['бюджет', 'телефон', 'контакт', 'почта', 'email']):
                    logger.info(f"Найдено имя: {name.capitalize()}")
                    return name.capitalize()

        return None

    async def _get_all_user_leads(self, user_id: int) -> list:
        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(Lead.user_id == user_id).order_by(Lead.created_at.desc())
            )
            return list(result.scalars().all())
