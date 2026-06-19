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
        ВСЕГДА создаёт НОВЫЙ лид - не обновляет старые
        """
        logger.info(f"🔍 Проверка лида для пользователя {user_id}")
        logger.info(f"История диалога: {len(history)} сообщений")

        user_messages = [msg for msg in history if msg["role"] == "user"]

        if not user_messages:
            logger.info("Нет сообщений пользователя")
            return None

        last_message = user_messages[-1]["content"]
        logger.info(f"Последнее сообщение: {last_message}")

        all_user_leads = await self._get_all_user_leads(user_id)

        if all_user_leads:
            last_lead = all_user_leads[-1]
            logger.info(f"Последний лид ID={last_lead.id} создан: {last_lead.created_at}")
            relevant_messages = user_messages[-2:]
            logger.info(f"Анализирую {len(relevant_messages)} СВЕЖИХ сообщений")
        else:
            relevant_messages = user_messages[-3:] if len(user_messages) >= 3 else user_messages
            logger.info(f"Первый лид — анализирую {len(relevant_messages)} сообщений")

        lead_data = self._extract_from_messages(relevant_messages)
        logger.info(f"Извлечённые данные: {lead_data}")

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

        if not self._has_intent_in_message(last_message):
            logger.info("❌ Нет намерения")
            return None

        # ВАЖНО: ВСЕГДА создаём НОВЫЙ лид если есть все данные
        # НЕ обновляем старые лиды
        logger.info(f"Создаём НОВЫЙ лид")
        lead = await self.lead_repo.create(user_id=user_id, **lead_data)
        logger.success(f"✅ Новый лид создан: {lead}")
        return lead

    def _has_intent_in_message(self, message: str) -> bool:
        msg_lower = message.lower().strip()

        category_keywords = [
            "косметика", "электроника", "спорттовары", "книги", "мебель",
            "одежда", "обувь", "игрушки", "продукты", "помощь", "меню",
            "каталог", "категории", "старт", "назад", "перезапустить",
            "ноутбуки", "смартфоны", "автотовары", "автозапчасти",
            "товары для дома", "детские товары", "зоотовары"
        ]

        for keyword in category_keywords:
            if keyword in msg_lower:
                logger.info(f"Категория '{keyword}' - не создаю лид")
                return False

        intent_keywords = [
            "хочу купить", "купить", "заказать", "покупаю",
            "интересует", "ищу", "нужен", "нужна", "нужно", "хочу",
            "расскажите про", "покажи", "дайте", "хочу оформить", "оформить"
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
            r'macbook\s+air', r'nike', r'adidas', r'levis',
            r'маникюр', r'стрижк', r'массаж'
        ]

        for pattern in product_patterns:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return True

        return False

    def _extract_from_messages(self, messages: list[dict]) -> dict:
        """Извлекает данные ТОЛЬКО из ПОСЛЕДНЕГО сообщения пользователя"""
        lead_data = {}

        if not messages:
            return lead_data

        logger.info(f"Анализирую {len(messages)} сообщений")

        # ВАЖНО: Берём ТОЛЬКО последнее сообщение пользователя
        last_user_msg = messages[-1]["content"]
        logger.info(f"Анализирую сообщение: {last_user_msg}")

        # Извлекаем ВСЕ данные ТОЛЬКО из последнего сообщения
        name = self._extract_name(last_user_msg)
        if name:
            lead_data["name"] = name
            logger.info(f"Найдено имя: {name}")

        contact = self._extract_contact(last_user_msg)
        if contact:
            lead_data["contact"] = contact
            logger.info(f"Найден контакт: {contact}")

        budget = self._extract_budget(last_user_msg)
        if budget:
            lead_data["budget"] = budget
            logger.info(f"Найден бюджет: {budget}")

        interest = self._extract_interest(last_user_msg, lead_data)
        if interest:
            lead_data["interest"] = interest
            logger.info(f"Найден интерес: {interest}")

        logger.info(f"Итоговые данные: {lead_data}")
        return lead_data

    def _extract_interest(self, message: str, existing_data: dict = None) -> str | None:
        """Извлекает интерес из сообщения (ЧИСТЫЙ, без телефона, бюджета, имени)"""
        if existing_data is None:
            existing_data = {}

        msg_lower = message.lower()

        intent_keywords = [
            "хочу купить", "купить", "заказать", "интересует", "ищу", "нужен", "покупаю",
            "нужна", "нужно", "хочу", "хочу записаться", "записаться", "запись", "забронировать",
            "расскажите про", "покажи", "дайте", "хочу оформить", "оформить"
        ]

        for kw in intent_keywords:
            if kw in msg_lower:
                parts = message.split(kw, 1)
                if len(parts) > 1:
                    interest_text = parts[1].strip()

                    # УДАЛЯЕМ из интереса ВСЁ лишнее:
                    # 1. Имя (если уже извлечено)
                    if existing_data.get("name"):
                        name_lower = existing_data["name"].lower()
                        interest_text = re.sub(rf'\b{name_lower}\b', '', interest_text, flags=re.IGNORECASE)

                    # 2. Номер телефона
                    interest_text = re.sub(r'[\+\d\s\-\(\)]{10,}', '', interest_text)
                    # 3. Email
                    interest_text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', interest_text)
                    # 4. Бюджет
                    interest_text = re.sub(r'бюджет[:\s]*\d+', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\d+\s*(к|тыс|руб|рублей)?', '', interest_text, flags=re.IGNORECASE)
                    # 5. Ключевые слова
                    interest_text = re.sub(r'\bимя\b', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\bтелефон\b', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\bпочта\b', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\bemail\b', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\bконтакт\b', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\bрублей\b', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\bруб\b', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\bза\b', '', interest_text, flags=re.IGNORECASE)

                    # Удаляем лишние запятые, точки и пробелы
                    interest_text = interest_text.strip()
                    interest_text = re.sub(r'\s+', ' ', interest_text)
                    interest_text = re.sub(r'[,\s]+$', '', interest_text)
                    interest_text = re.sub(r'^[,\s]+', '', interest_text)
                    interest_text = re.sub(r',\s*,', ',', interest_text)
                    interest_text = interest_text.strip(',').strip()

                    if interest_text and len(interest_text) > 2:
                        return f"{kw} {interest_text}"
                return message.strip()

        # Проверяем паттерны товаров
        product_patterns = [
            r'iphone\s*\d*', r'айфон\s*\d*', r'macbook', r'airpods',
            r'pantene', r'nivea', r'chanel', r'dior',
            r'lego\s+\w+', r'barbie',
            r'парфюм\s+\w+', r'крем\s+\w+', r'шампунь\s+\w+',
            r'\w+\s+набор', r'книга\s+.+',
            r'диван', r'кроссовки', r'ноутбук', r'телефон',
            r'гантели', r'велосипед', r'гироскутер',
            r'стрижк', r'массаж', r'маникюр',
            r'консультаци', r'приём',
            r'macbook\s+air', r'nike', r'adidas', r'levis'
        ]

        for pattern in product_patterns:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                clean_text = message
                if existing_data.get("name"):
                    name_lower = existing_data["name"].lower()
                    clean_text = re.sub(rf'\b{name_lower}\b', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'[\+\d\s\-\(\)]{10,}', '', clean_text)
                clean_text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', clean_text)
                clean_text = re.sub(r'бюджет[:\s]*\d+', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'\d+\s*(к|тыс|руб|рублей)?', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'\bимя\b', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'\bтелефон\b', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'\bпочта\b', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'\bemail\b', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'\bконтакт\b', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'\bрублей\b', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'\bруб\b', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'\bза\b', '', clean_text, flags=re.IGNORECASE)
                clean_text = clean_text.strip()
                clean_text = re.sub(r'\s+', ' ', clean_text)
                clean_text = re.sub(r'[,\s]+$', '', clean_text)
                clean_text = re.sub(r'^[,\s]+', '', clean_text)
                clean_text = clean_text.strip(',').strip()
                return clean_text if clean_text else message.strip()

        return None

    def _extract_contact(self, message: str) -> str | None:
        """Извлекает контакт (телефон или email)"""
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
        """Извлекает бюджет из сообщения"""
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

        name_patterns = [
            r'(?:имя|меня зовут|мое имя|зовут)[:\s]+(\w+)',
            r'имя\s+(\w+)',
            r',\s*(\w+),\s*(?:телефон|бюджет|контакт)',
            r'\s(\w+)\s*,\s*бюджет',
        ]

        for pattern in name_patterns:
            name_match = re.search(pattern, msg_lower)
            if name_match:
                name = name_match.group(1)
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
