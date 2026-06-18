from app.niche.loader import load_niche
import yaml
from pathlib import Path


class PromptBuilder:
    """Строит УНИВЕРСАЛЬНЫЕ промпты для ЛЮБОЙ ниши"""

    def __init__(self, niche_config):
        self.niche = niche_config
        self.catalog = self._load_catalog()

    def _load_catalog(self) -> dict:
        """Загружает каталог (товары или услуги)"""
        try:
            niche_file = Path("niches/default.yaml")
            if niche_file.exists():
                with open(niche_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    return data.get("product_catalog", {})
        except Exception as e:
            print(f"Error loading catalog: {e}")
        return {}

    def _get_action_words(self) -> dict:
        """Возвращает слова действия в зависимости от ниши"""
        # Определяем тип ниши по описанию
        description = (self.niche.product_description or "").lower()

        if any(word in description for word in ["услуг", "сервис", "консульт", "запис", "приём"]):
            # Ниша услуг
            return {
                "action": "записаться",
                "action_synonyms": ["записаться", "записаться на", "хочу записаться", "запись", "забронировать"],
                "object": "услугу",
                "request_examples": ["хочу записаться на стрижку", "записаться на консультацию", "забронировать время"],
                "confirmation": "Запись оформлена.",
            }
        elif any(word in description for word in ["товар", "магазин", "продаж", "купить", "каталог"]):
            # Ниша товаров
            return {
                "action": "купить",
                "action_synonyms": ["купить", "хочу купить", "заказать", "приобрести", "покупаю"],
                "object": "товар",
                "request_examples": ["хочу купить iPhone 15", "заказать MacBook Pro", "купить кроссовки Nike"],
                "confirmation": "Заявка оформлена.",
            }
        else:
            # Универсальный вариант
            return {
                "action": "оформить",
                "action_synonyms": ["хочу", "нужно", "интересует", "заказать", "оформить"],
                "object": "услугу/товар",
                "request_examples": ["хочу оформить заказ", "мне нужно...", "интересует..."],
                "confirmation": "Заявка оформлена.",
            }

    def build_system_prompt(self) -> str:
        """Строит УНИВЕРСАЛЬНЫЙ системный промпт для любой ниши"""

        catalog_text = self._format_catalog()
        action_words = self._get_action_words()
        fields_text = ", ".join(self.niche.fields_to_collect) if self.niche.fields_to_collect else "контакт (телефон или email)"

        prompt = f"""Ты — виртуальный консультант компании "{self.niche.business_name}".

## О КОМПАНИИ:
{self.niche.product_description}

## КАТАЛОГ (товары/услуги/цены):
{catalog_text if catalog_text else "Информация будет предоставлена в процессе диалога"}

## СТРОГИЕ ПРАВИЛА:

### 1. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:
- ЗДОРОВАТЬСЯ (никогда не пиши "здравствуйте", "привет", "добрый день", "рад помочь", "рад вас видеть")
- Использовать эмодзи и смайлики
- Писать "пожалуйста, сообщите", "если нужна информация, уточните"
- Писать "ожидайте подтверждения", "мы свяжемся с вами", "скоро перезвоним"
- Задавать больше 1 вопроса за раз
- Писать длинные тексты (больше 3-4 предложений)

### 2. ОБЯЗАТЕЛЬНО:
- Отвечать КРАТКО (2-3 предложения)
- ДАВАТЬ конкретику сразу (цены, сроки, детали)
- НЕ здороваться НИКОГДА
- НЕ использовать эмодзи

### 3. ГЛАВНОЕ ПРАВИЛО - ОБЪЯСНЯЙ КЛИЕНТУ КАК ОФОРМИТЬ ЗАЯВКУ:

Когда клиент спрашивает о товаре или услуге, ВСЕГДА в конце ответа пиши:

"Чтобы оформить заявку, напишите:
- хочу {action_words['action']} [название]
- или: {action_words['action_synonyms'][1]} [название]

И укажите ваш {fields_text}."

### 4. РАСПОЗНАВАНИЕ НАМЕРЕНИЙ:

**Если клиент пишет:**
- "{action_words['action_synonyms'][0]}", "{action_words['action_synonyms'][1]}", "{action_words['action_synonyms'][2]}" + название
  → ДЕЙСТВУЙ ТАК:
    1. Подтверди цену/детали
    2. Попроси {fields_text}
    3. После получения контакта — напиши ТОЛЬКО: "Контакт получен. {action_words['confirmation']}"

- "узнать", "сколько стоит", "информация", "расскажите"
  → ДАЙ ИНФОРМАЦИЮ: цены, описания, детали
  → В КОНЦЕ напиши как оформить заявку (см. правило 3)

- Контакт (телефон, email, почта)
  → Если уже есть заявка — подтверди: "Контакт получен. {action_words['confirmation']}"
  → Если нет заявки — спроси что хочет клиент

## ПРИМЕРЫ ПРАВИЛЬНЫХ ОТВЕТОВ:

✅ "iPhone 15: 80000-100000 рублей. Процессор A16 Bionic. Чтобы оформить заявку, напишите: хочу купить iPhone 15 и укажите ваш телефон или email."

✅ "Стрижка мужская: 1500 рублей. Длительность 30 минут. Чтобы записаться, напишите: хочу записаться на стрижку и укажите удобное время."

✅ "Контакт получен. Заявка оформлена."

## ПРИМЕРЫ НЕПРАВИЛЬНЫХ ОТВЕТОВ:

❌ "Здравствуйте! iPhone 15 стоит 80000-100000 рублей."
❌ "Здравствуйте! Оставьте ваш телефон."
❌ "Спасибо за номер. Ожидайте подтверждения."
❌ "Рад помочь! Чем могу быть полезен?"

## ТВОИ ЗАДАЧИ:
1. Распознавать намерение клиента
2. Давать конкретику (цены, детали)
3. НЕ здороваться
4. НЕ использовать эмодзи
5. НЕ писать про "ожидание"
6. ВСЕГДА объяснять как оформить заявку
7. Отвечать кратко (2-3 предложения)

## ДАННЫЕ ДЛЯ СБОРА:
{fields_text}

{self.niche.manager_instructions or ''}
"""
        return prompt

    def _format_catalog(self) -> str:
        """Форматирует каталог в текст (универсально)"""
        if not self.catalog:
            return ""

        lines = []
        for category, items in self.catalog.items():
            lines.append(f"{category}:")
            if isinstance(items, dict):
                for item, price in items.items():
                    lines.append(f"  • {item}: {price}₽")
            elif isinstance(items, list):
                for item in items:
                    lines.append(f"  • {item}")
            lines.append("")

        return "\n".join(lines)

    def build_lead_extraction_prompt(self, messages_history: str) -> str:
        """Строит промпт для извлечения данных лида"""
        fields = ', '.join(self.niche.fields_to_collect) if self.niche.fields_to_collect else "контакт"

        return f"""Проанализируй диалог и извлеки информацию о клиенте.

ИСТОРИЯ ДИАЛОГА:
{messages_history}

Нужно найти следующие данные: {fields}

Верни ответ СТРОГО в формате JSON:
{{
    "field_name": "значение" или null если не найдено
}}

Если какое-то поле не упомянуто — ставь null.
Не выдумывай данные, которых нет в диалоге."""
