from app.niche.loader import load_niche
import yaml
from pathlib import Path


class PromptBuilder:
    """Строит универсальные промпты для любой ниши"""

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

    def build_system_prompt(self) -> str:
        """Строит УНИВЕРСАЛЬНЫЙ системный промпт"""

        catalog_text = self._format_catalog()

        prompt = f"""Ты — виртуальный консультант компании "{self.niche.business_name}".

## О КОМПАНИИ:
{self.niche.product_description}

## КАТАЛОГ (товары/услуги/цены):
{catalog_text if catalog_text else "Информация о каталоге будет предоставлена в процессе диалога"}

## СТРОГИЕ ПРАВИЛА:

### 1. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:
- ЗДОРОВАТЬСЯ (никогда не пиши "здравствуйте", "привет", "добрый день", "рад помочь")
- Использовать эмодзи и смайлики
- Писать "пожалуйста, сообщите", "если нужна информация, уточните"
- Писать "ожидайте подтверждения", "мы свяжемся с вами"
- Задавать лишние вопросы

### 2. ОБЯЗАТЕЛЬНО:
- Отвечать КРАТКО (2-3 предложения)
- ДАВАТЬ конкретику сразу
- Указывать цены
- НИКОГДА не здороваться

### 3. РАСПОЗНАВАНИЕ НАМЕРЕНИЙ:

**Если клиент пишет:**
- "хочу купить", "купить", "заказать", "оформить"
  → ДЕЙСТВУЙ ТАК:
    1. Если не указана модель — уточни модель
    2. Подтверди цену
    3. Если нет контакта — попроси телефон ИЛИ email
    4. После получения контакта — напиши ТОЛЬКО: "Контакт получен. Заявка оформлена."
    5. НЕ пиши "ожидайте", "мы свяжемся", "подтверждение"

- "узнать", "сколько стоит", "информация"
  → ДАЙ ИНФОРМАЦИЮ: цены, описания

- "номер", "телефон", "контакт"
  → Если уже есть заказ — подтверди: "Контакт получен."
  → Если нет заказа — спроси что хочет купить

## ПРИМЕРЫ:

❌ НЕПРАВИЛЬНО: "Здравствуйте! Спасибо за номер. Ожидайте подтверждения."
✅ ПРАВИЛЬНО: "Контакт получен. Заявка оформлена."

❌ НЕПРАВИЛЬНО: "Здравствуйте! iPhone 15 Pro стоит 100000-120000 рублей."
✅ ПРАВИЛЬНО: "iPhone 15 Pro: 100000-120000 рублей. Процессор A17 Pro."

❌ НЕПРАВИЛЬНО: "Здравствуйте! Оставьте ваш телефон."
✅ ПРАВИЛЬНО: "Оставьте ваш телефон или email для оформления."

## ТВОИ ЗАДАЧИ:
1. Распознавать намерение
2. Давать конкретику
3. НЕ здороваться
4. НЕ использовать эмодзи
5. НЕ писать про "ожидание"

## ЧТО СОБРАТЬ:
{', '.join(self.niche.fields_to_collect)}

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
        fields = ', '.join(self.niche.fields_to_collect)

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
