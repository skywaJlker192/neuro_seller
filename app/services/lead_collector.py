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
        Проверяет и собирает лид для ЛЮБОЙ ниши
        """
        logger.info(f"🔍 Проверка лида для пользователя {user_id}")
        logger.info(f"История диалога: {len(history)} сообщений")

        # Получаем последнее сообщение пользователя
        user_messages = [msg for msg in history if msg["role"] == "user"]

        if not user_messages:
            logger.info("Нет сообщений пользователя")
            return None

        last_message = user_messages[-1]["content"]
        logger.info(f"Последнее сообщение: {last_message}")

        # Извлекаем данные из последнего сообщения
        lead_data = self._extract_from_message(last_message)
        logger.info(f"Извлечённые данные: {lead_data}")

        # Получаем все лиды пользователя
        all_user_leads = await self._get_all_user_leads(user_id)

        # ПРОВЕРКА 1: Если пользователь даёт контакт/данные И есть лид без этих данных → обновляем
        if all_user_leads:
            last_lead = all_user_leads[-1]
            update_data = {}

            # Проверяем каждое поле лида
            if not last_lead.contact and lead_data.get("contact"):
                update_data["contact"] = lead_data["contact"]
                logger.info(f"Добавляем контакт к лиду {last_lead.id}")

            if not last_lead.budget and lead_data.get("budget"):
                update_data["budget"] = lead_data["budget"]
                logger.info(f"Добавляем бюджет к лиду {last_lead.id}")

            if not last_lead.name and lead_data.get("name"):
                update_data["name"] = lead_data["name"]
                logger.info(f"Добавляем имя к лиду {last_lead.id}")

            # Обновляем если есть что обновить
            if update_data:
                lead = await self.lead_repo.update(last_lead.id, **update_data)
                logger.success(f"✅ Лид обновлён: {lead}")
                return lead

        # ПРОВЕРКА 2: Проверяем намерение (только если нет лида для обновления)
        if not self._has_intent_in_message(last_message):
            logger.info("❌ Нет намерения - не создаю лид")
            return None

        # Проверяем есть ли данные
        if not lead_data:
            logger.warning("Не удалось извлечь данные из сообщения")
            return None

        # Проверяем, есть ли уже лид с таким интересом
        current_interest = lead_data.get("interest", "").lower()
        existing_lead_with_same_interest = None

        for lead in all_user_leads:
            lead_interest = (lead.interest or "").lower()
            if current_interest and lead_interest and current_interest in lead_interest:
                existing_lead_with_same_interest = lead
                break

        # Если есть данные — сохраняем/обновляем
        if lead_data.get("interest") or lead_data.get("contact") or lead_data.get("name"):
            logger.info(f"✅ Есть данные для лида: {lead_data}")

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
                    logger.info("Нет новых данных для обновления")
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
                    lead = await self.lead_repo.create(user_id=user_id, **lead_data)
                    logger.success(f"✅ Новый лид создан: {lead}")
                    return lead
            else:
                logger.info(f"Создаём ПЕРВЫЙ лид для user_id={user_id}")
                lead = await self.lead_repo.create(user_id=user_id, **lead_data)
                logger.success(f"✅ Первый лид создан: {lead}")
                return lead

        logger.warning("❌ Нет данных для сохранения лида")
        return None

    def _has_intent_in_message(self, message: str) -> bool:
        """
        УНИВЕРСАЛЬНАЯ проверка намерения (товары + услуги)
        """
        msg_lower = message.lower().strip()

        # Навигационные команды - НЕ создавать лид
        navigation_keywords = [
            "контакты", "контакт", "меню", "все товары", "каталог",
            "помощь", "help", "старт", "начать", "назад", "главное меню",
            "перезапустить", "рестарт", "кнопки", "категории",
            "что ты умеешь", "о боте", "инструкция", "список",
            "что вы предлагаете", "ассортимент", "услуги"
        ]

        for keyword in navigation_keywords:
            if keyword in msg_lower:
                logger.info(f"Навигационная команда '{keyword}' - не создаю лид")
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

        # Проверяем на наличие конкретных товаров/услуг
        product_patterns = [
            r'парфюм\s+\w+', r'крем\s+\w+', r'шампунь\s+\w+',
            r'косметика', r'\w+\s+набор', r'книга\s+.+',
            r'iphone\s*\d*', r'айфон\s*\d*', r'macbook', r'airpods',
            r'диван', r'кроссовки', r'ноутбук', r'телефон',
            r'гантели', r'велосипед', r'стрижк', r'массаж',
            r'консультаци', r'приём', r'запись на'
        ]

        for pattern in product_patterns:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                logger.info(f"Найден товар/услуга по паттерну: {pattern}")
                return True

        logger.info("Не найдено намерение")
        return False

    def _extract_from_message(self, message: str) -> dict:
        """УНИВЕРСАЛЬНОЕ извлечение данных из сообщения"""
        lead_data = {}
        msg_lower = message.lower()

        # Ищем интерес (что хочет клиент)
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
                    # Удаляем номер телефона из интереса
                    interest_text = re.sub(r'[\+\d\s\-\(\)]{10,}', '', interest_text).strip()
                    if interest_text:
                        lead_data["interest"] = f"{kw} {interest_text}"
                    else:
                        lead_data["interest"] = message.strip()
                else:
                    lead_data["interest"] = message.strip()
                logger.info(f"Найден интерес: {lead_data['interest']}")
                break

        # Если не нашли - проверяем паттерны товаров/услуг
        if not lead_data.get("interest"):
            product_patterns = [
                r'парфюм\s+\w+', r'крем\s+\w+', r'шампунь\s+\w+',
                r'косметика', r'\w+\s+набор', r'книга\s+.+',
                r'iphone\s*\d*', r'айфон\s*\d*', r'macbook', r'airpods',
                r'диван', r'кроссовки', r'ноутбук', r'телефон',
                r'гантели', r'велосипед', r'стрижк', r'массаж',
                r'консультаци', r'приём'
            ]

            for pattern in product_patterns:
                if re.search(pattern, msg_lower, re.IGNORECASE):
                    lead_data["interest"] = message.strip()
                    logger.info(f"Найден товар/услуга: {lead_data['interest']}")
                    break

        # Ищем телефон
        phone_patterns = [
            r'(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
            r'(\+7|8)\d{10}',
            r'номер[:\s]+(\+?7?\d{10,11})',
            r'телефон[:\s]+(\+?7?\d{10,11})',
            r'мой номер[:\s]*(\+?7?\d{10,11})',
        ]

        msg_clean = message.replace(" ", "")
        for pattern in phone_patterns:
            phone_match = re.search(pattern, msg_clean)
            if phone_match:
                lead_data["contact"] = phone_match.group(0)
                logger.info(f"Найден телефон: {lead_data['contact']}")
                break

        # Ищем email
        if not lead_data.get("contact"):
            email_patterns = [
                r'(?:почта|email|майл|e-mail|мейл)[:\s]*([\w\.-]+@[\w\.-]+\.\w+)',
                r'([\w\.-]+@[\w\.-]+\.\w+)',
            ]

            for pattern in email_patterns:
                email_match = re.search(pattern, message, re.IGNORECASE)
                if email_match:
                    lead_data["contact"] = email_match.group(1)
                    logger.info(f"Найден email: {lead_data['contact']}")
                    break

        # Ищем имя
        if "меня зовут" in msg_lower or "мое имя" in msg_lower or "зовут" in msg_lower:
            for kw in ["меня зовут", "мое имя", "зовут"]:
                if kw in msg_lower:
                    parts = msg_lower.split(kw, 1)
                    if len(parts) > 1:
                        name_part = parts[1].strip().split()[0]
                        name = ''.join(c for c in name_part if c.isalpha() or c == '-')
                        if name and len(name) > 1:
                            lead_data["name"] = name.capitalize()
                            logger.info(f"Найдено имя: {lead_data['name']}")
                    break

        # Ищем бюджет/цену
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
                    lead_data["budget"] = f"{min_price}-{max_price} руб"
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
                        lead_data["budget"] = f"{min_price}-{max_price} руб"
                else:
                    lead_data["budget"] = budget_match.group(0)
                logger.info(f"Найден бюджет: {lead_data['budget']}")
                break

        logger.info(f"Итоговые данные: {lead_data}")
        return lead_data

    async def _get_all_user_leads(self, user_id: int) -> list:
        """Получает все лиды пользователя"""
        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(Lead.user_id == user_id).order_by(Lead.created_at.desc())
            )
            return list(result.scalars().all())
