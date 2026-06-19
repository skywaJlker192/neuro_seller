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

        # Извлекаем данные из ВСЕЙ истории
        lead_data = self._extract_from_history(history)
        logger.info(f"Извлечённые данные: {lead_data}")

        # ВАЖНО: Проверяем наличие ВСЕХ обязательных полей
        missing_fields = []

        if not lead_data.get("interest"):
            missing_fields.append("интерес (что хочет купить)")

        if not lead_data.get("contact"):
            missing_fields.append("контакт (телефон или email)")

        if not lead_data.get("budget"):
            missing_fields.append("бюджет")

        if missing_fields:
            logger.info(f"❌ Не хватает данных: {', '.join(missing_fields)} - НЕ создаю лид")
            return None

        logger.info(f"✅ Все данные есть: {lead_data}")

        # Проверяем намерение
        if not self._has_intent_in_message(last_message):
            logger.info("❌ Нет намерения - не создаю лид")
            return None

        # Получаем все лиды пользователя
        all_user_leads = await self._get_all_user_leads(user_id)

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
            # Обновляем СУЩЕСТВУЮЩИЙ лид
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
                logger.info("Нет новых данных для обновления")
                return lead

        elif all_user_leads:
            # Проверяем последний лид
            last_lead = all_user_leads[-1]
            last_interest = (last_lead.interest or "").lower()

            if current_interest and last_interest and current_interest != last_interest:
                # Новый интерес - создаём НОВЫЙ лид
                logger.info(f"Новый интерес '{current_interest}' - создаю новый лид")
                lead = await self.lead_repo.create(user_id=user_id, **lead_data)
                logger.success(f"✅ Новый лид создан: {lead}")
                return lead
            else:
                # Обновляем последний лид
                logger.info(f"Обновляю последний лид {last_lead.id}")
                lead = await self.lead_repo.create(user_id=user_id, **lead_data)
                logger.success(f"✅ Лид создан: {lead}")
                return lead
        else:
            # Первый лид пользователя
            logger.info(f"Создаём ПЕРВЫЙ лид для user_id={user_id}")
            lead = await self.lead_repo.create(user_id=user_id, **lead_data)
            logger.success(f"✅ Первый лид создан: {lead}")
            return lead

    def _has_intent_in_message(self, message: str) -> bool:
        """
        УНИВЕРСАЛЬНАЯ проверка намерения (товары + услуги)
        КАТЕГОРИИ НЕ СЧИТАЮТСЯ ЛИДАМИ
        """
        msg_lower = message.lower().strip()

        # КАТЕГОРИИ - НЕ создавать лид (навигация)
        category_keywords = [
            "косметика", "электроника", "спорттовары", "спорт товары",
            "книги", "мебель", "одежда", "обувь", "игрушки",
            "продукты", "питание", "автотовары", "авто товары",
            "бытовая техника", "техника", "смартфоны", "телефоны",
            "ноутбуки", "компьютеры", "аксессуары", "украшения",
            "парфюмерия", "косметика и парфюмерия", "уходовая косметика",
            "декоративная косметика", "спортивный инвентарь", "товары для спорта",
            "товары для дома", "дом", "сад", "огород",
            "детские товары", "товары для детей", "детское",
            "зоотовары", "товары для животных", "для животных",
            "канцтовары", "канцелярия", "офис",
            "стройматериалы", "строительство", "ремонт",
            "инструменты", "электроинструменты",
            # Общие навигационные
            "меню", "все товары", "каталог", "категории",
            "помощь", "help", "старт", "начать", "назад", "главное меню",
            "перезапустить", "рестарт", "кнопки",
            "что ты умеешь", "о боте", "инструкция", "список",
            "что вы предлагаете", "ассортимент", "услуги",
            "контакты", "контакт"
        ]

        for keyword in category_keywords:
            if keyword in msg_lower:
                logger.info(f"Категория/навигация '{keyword}' - не создаю лид")
                return False

        # Универсальные ключевые слова намерения (товары + услуги)
        intent_keywords = [
            # Покупка товаров
            "хочу купить", "купить", "заказать", "покупаю",
            # Запись на услуги
            "хочу записаться", "записаться", "запись", "забронировать",
            # Общие
            "интересует", "ищу", "нужен", "нужна", "нужно", "хочу",
            "расскажите про", "покажи", "дайте", "цена", "сколько стоит",
            "стоимость", "характеристики", "подробнее"
        ]

        # Проверяем сообщение - должно быть ключевое слово + что-то ещё
        for keyword in intent_keywords:
            if keyword in msg_lower:
                parts = msg_lower.split(keyword, 1)
                if len(parts) > 1 and parts[1].strip():
                    remaining_text = parts[1].strip()
                    # Проверяем что это не просто номер телефона
                    if not re.match(r'^[\d\s\+\-]+$', remaining_text):
                        logger.info(f"Найдено намерение: '{keyword}'")
                        return True

        # Проверяем на наличие КОНКРЕТНЫХ товаров/услуг (НЕ категорий)
        product_patterns = [
            # Конкретные бренды и модели
            r'iphone\s*\d*', r'айфон\s*\d*', r'macbook', r'airpods',
            r'samsung\s+galaxy', r'xiaomi', r'huawei', r'oneplus',
            r'pantene', r'nivea', r'chanel', r'dior', r'lancome',
            r'lego\s+\w+', r'barbie', r'hot wheels',
            # Конкретные товары
            r'парфюм\s+\w+', r'крем\s+\w+', r'шампунь\s+\w+',
            r'\w+\s+набор', r'книга\s+.+',
            r'диван', r'кроссовки', r'ноутбук', r'телефон',
            r'гантели', r'велосипед', r'гироскутер', r'самокат',
            r'стрижк', r'массаж', r'маникюр', r'педикюр',
            r'консультаци', r'приём', r'запись на'
        ]

        for pattern in product_patterns:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                logger.info(f"Найден конкретный товар/услуга: {pattern}")
                return True

        logger.info("Не найдено намерение купить конкретный товар")
        return False

    def _extract_from_history(self, history: list[dict]) -> dict:
        """Извлекает данные из ВСЕЙ истории диалога"""
        lead_data = {}

        # Собираем все сообщения пользователя
        user_messages = [msg["content"] for msg in history if msg["role"] == "user"]

        if not user_messages:
            return lead_data

        logger.info(f"Анализирую {len(user_messages)} сообщений")

        # Извлекаем интерес из последнего сообщения (самое актуальное)
        last_msg = user_messages[-1]
        interest = self._extract_interest(last_msg)
        if interest:
            lead_data["interest"] = interest

        # Если не нашли в последнем - ищем во всех
        if not interest:
            for msg in reversed(user_messages):
                interest = self._extract_interest(msg)
                if interest:
                    lead_data["interest"] = interest
                    break

        # Извлекаем контакт из ВСЕХ сообщений
        for msg in user_messages:
            contact = self._extract_contact(msg)
            if contact and not lead_data.get("contact"):
                lead_data["contact"] = contact
                break

        # Извлекаем бюджет из ВСЕХ сообщений
        for msg in user_messages:
            budget = self._extract_budget(msg)
            if budget and not lead_data.get("budget"):
                lead_data["budget"] = budget
                break

        # Извлекаем имя из ВСЕХ сообщений
        for msg in user_messages:
            name = self._extract_name(msg)
            if name and not lead_data.get("name"):
                lead_data["name"] = name
                break

        logger.info(f"Итоговые данные: {lead_data}")
        return lead_data

    def _extract_interest(self, message: str) -> str | None:
        """Извлекает интерес из сообщения (ЧИСТЫЙ, без телефона, бюджета, имени)"""
        msg_lower = message.lower()

        intent_keywords = [
            "хочу купить", "купить", "заказать", "интересует", "ищу", "нужен", "покупаю",
            "нужна", "нужно", "хочу", "хочу записаться", "записаться", "запись", "забронировать",
            "расскажите про", "покажи", "дайте"
        ]

        for kw in intent_keywords:
            if kw in msg_lower:
                parts = message.split(kw, 1)
                if len(parts) > 1:
                    interest_text = parts[1].strip()

                    # УДАЛЯЕМ из интереса:
                    # 1. Номер телефона
                    interest_text = re.sub(r'[\+\d\s\-\(\)]{10,}', '', interest_text)
                    # 2. Бюджет
                    interest_text = re.sub(r'бюджет[:\s]*\d+', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'\d+\s*(к|тыс|руб)?\s*(до|до)\s*\d+', '', interest_text, flags=re.IGNORECASE)
                    # 3. Имя
                    interest_text = re.sub(r'моё имя\s+\w+', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'меня зовут\s+\w+', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'мое имя\s+\w+', '', interest_text, flags=re.IGNORECASE)
                    # 4. Телефон
                    interest_text = re.sub(r'мой телефон', '', interest_text, flags=re.IGNORECASE)
                    interest_text = re.sub(r'телефон[:\s]*[\+\d]+', '', interest_text, flags=re.IGNORECASE)
                    # 5. Email
                    interest_text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', interest_text)

                    interest_text = interest_text.strip()
                    interest_text = re.sub(r'\s+', ' ', interest_text)  # Убираем лишние пробелы

                    if interest_text:
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
            r'консультаци', r'приём'
        ]

        for pattern in product_patterns:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return message.strip()

        return None

    def _extract_contact(self, message: str) -> str | None:
        """Извлекает контакт (телефон или email)"""
        msg_lower = message.lower()

        # Ищем телефон
        phone_patterns = [
            r'(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
            r'(\+7|8)\d{10}',
            r'номер[:\s]+(\+?7?\d{10,11})',
            r'телефон[:\s]+(\+?7?\d{10,11})',
            r'мой номер[:\s]*(\+?7?\d{10,11})',
            r'(\+?7)?\s*\d{11}',
            r'\b\d{10,11}\b',
        ]

        msg_clean = message.replace(" ", "")
        for pattern in phone_patterns:
            phone_match = re.search(pattern, msg_clean)
            if phone_match:
                phone = phone_match.group(0)
                # Добавляем +7 если нужно
                if len(phone) == 11 and phone.isdigit() and phone.startswith('9'):
                    phone = '+7' + phone
                elif len(phone) == 10 and phone.isdigit():
                    phone = '+7' + phone
                logger.info(f"Найден телефон: {phone}")
                return phone

        # Ищем email
        email_patterns = [
            r'(?:почта|email|майл|e-mail|мейл)[:\s]*([\w\.-]+@[\w\.-]+\.\w+)',
            r'([\w\.-]+@[\w\.-]+\.\w+)',
        ]

        for pattern in email_patterns:
            email_match = re.search(pattern, msg_lower, re.IGNORECASE)
            if email_match:
                email = email_match.group(1)
                logger.info(f"Найден email: {email}")
                return email

        return None

    def _extract_budget(self, message: str) -> str | None:
        """Извлекает бюджет из сообщения"""
        msg_lower = message.lower()

        budget_patterns = [
            r'бюджет[:\s]*(\d+[\s\-]?\d*)',
            r'до\s+(\d+[\s\-]?\d*)\s*руб',
            r'(\d+[\s\-]?\d*)\s*руб',
            r'цена[:\s]*(\d+[\s\-]?\d*)',
            r'от\s+(\d+)\s*(к|тыс)?\s*(до|до)\s*(\d+)\s*(к|тыс|руб)?',
            r'(\d+)\s*(к|тыс)\s*[-–]\s*(\d+)\s*(к|тыс)',
            r'(\d+)\s*[-–]\s*(\d+)\s*(к|тыс)',
        ]

        for pattern in budget_patterns:
            budget_match = re.search(pattern, msg_lower)
            if budget_match:
                if pattern.startswith(r'от\s+'):
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
                logger.info(f"Найден бюджет: {budget}")
                return budget

        return None

    def _extract_name(self, message: str) -> str | None:
        """Извлекает имя из сообщения"""
        msg_lower = message.lower()

        if "меня зовут" in msg_lower or "мое имя" in msg_lower or "зовут" in msg_lower:
            for kw in ["меня зовут", "мое имя", "зовут"]:
                if kw in msg_lower:
                    parts = msg_lower.split(kw, 1)
                    if len(parts) > 1:
                        name_part = parts[1].strip().split()[0]
                        name = ''.join(c for c in name_part if c.isalpha() or c == '-')
                        if name and len(name) > 1:
                            logger.info(f"Найдено имя: {name.capitalize()}")
                            return name.capitalize()

        return None

    async def _get_all_user_leads(self, user_id: int) -> list:
        """Получает все лиды пользователя"""
        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(Lead.user_id == user_id).order_by(Lead.created_at.desc())
            )
            return list(result.scalars().all())
