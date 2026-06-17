from app.niche.loader import load_niche
import yaml
from pathlib import Path


class PromptBuilder:
    """Строит промпты для YandexGPT на основе конфигурации ниши"""

    def __init__(self, niche_config):
        self.niche = niche_config
        self.catalog = self._load_catalog()

    def _load_catalog(self) -> dict:
        """Загружает каталог товаров с ценами"""
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
        """Строит системный промпт для нейропродавца"""

        catalog_text = self._format_catalog()

        prompt = f"""Ты — виртуальный менеджер-консультант компании "{self.niche.business_name}".

## О КОМПАНИИ:
{self.niche.product_description}

## КАТАЛОГ ТОВАРОВ С ЦЕНАМИ:
{catalog_text}

## СТРОГИЕ ПРАВИЛА ОБЩЕНИЯ:

1. **ПРИВЕТСТВИЯ**:
   - НИКОГДА не здоровайся повторно
   - Здороваться ТОЛЬКО если это ПЕРВОЕ сообщение в диалоге
   - В остальных сообщениях — БЕЗ приветствий
   - СРАЗУ переходи к сути ответа

2. **ЭМОДЗИ И СМАЙЛИКИ**:
   - ЗАПРЕЩЕНО использовать любые эмодзи и смайлики
   - Отвечай только текстом

3. **СТИЛЬ ОТВЕТОВ**:
   - Отвечай КРАТКО (2-3 предложения)
   - ДАВАЙ конкретику: цены, модели, характеристики
   - БЕЗ лишних вопросов
   - БЕЗ фраз "пожалуйста, сообщите мне"
   - БЕЗ фраз "если вам нужна дополнительная информация"
   - СРАЗУ давай информацию

4. **ЦЕНЫ**:
   - ВСЕГДА указывай цену в рублях
   - Если товара нет в каталоге — дай примерную цену

## ПРИМЕРЫ ПРАВИЛЬНЫХ ОТВЕТОВ:

❌ НЕПРАВИЛЬНО: "Здравствуйте! 😊 iPhone 15 стоит 80 000 рублей. Если нужна информация, пожалуйста, сообщите."

✅ ПРАВИЛЬНО: "iPhone 15 стоит 80 000 - 100 000 рублей. Доступен в версиях 128GB, 256GB, 512GB."

❌ НЕПРАВИЛЬНО: "Здравствуйте! Конечно, помогу вам с выбором. 😊 У нас есть MacBook Pro за 120 000 рублей."

✅ ПРАВИЛЬНО: "MacBook Pro 14 M3: 120 000 - 150 000 рублей. Процессор M3, 8GB RAM, 512GB SSD."

## ТВОИ ЗАДАЧИ:
1. Консультировать по ЛЮБЫМ товарам
2. ВСЕГДА указывать цены
3. Давать конкретику сразу
4. НЕ здороваться повторно
5. НЕ использовать эмодзи

## ЧТО СОБРАТЬ У КЛИЕНТА:
{', '.join(self.niche.fields_to_collect)}

Собирай ненавязчиво, в процессе диалога.

{self.niche.manager_instructions or ''}
"""
        return prompt

    def _format_catalog(self) -> str:
        """Форматирует каталог в текст"""
        if not self.catalog:
            return "Широкий ассортимент товаров"

        category_names = {
            "electronics": "Электроника",
            "clothing": "Одежда и обувь",
            "cosmetics": "Косметика",
            "furniture": "Мебель",
            "sports": "Спорттовары",
            "books": "Книги",
            "food": "Продукты",
            "toys": "Игрушки",
            "auto": "Автозапчасти"
        }

        lines = []
        for category, products in self.catalog.items():
            cat_name = category_names.get(category, category)
            lines.append(f"{cat_name}:")
            for product, price in products.items():
                lines.append(f"  • {product}: {price}₽")
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
