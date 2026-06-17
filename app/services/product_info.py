import aiohttp
from loguru import logger


class ProductInfoSearcher:
    """Поиск подробной информации о товарах в интернете"""

    def __init__(self):
        self.search_url = "https://yandex.com/search/"
        # Можно добавить API ключи для более продвинутых поисковиков

    async def search_product_info(self, product_name: str) -> str:
        """
        Ищет подробную информацию о товаре в интернете

        Args:
            product_name: Название товара

        Returns:
            Строка с информацией о товаре или пустая строка если не найдено
        """
        try:
            # Формируем поисковый запрос
            search_query = f"{product_name} характеристики specifications"

            async with aiohttp.ClientSession() as session:
                # Ищем на Яндекс.Маркете и других сайтах
                urls_to_check = [
                    f"https://market.yandex.ru/search?text={product_name.replace(' ', '%20')}",
                    f"https://www.google.com/search?q={product_name.replace(' ', '%20')}+характеристики"
                ]

                # В MVP возвращаем инструкцию для YandexGPT искать информацию
                # В продакшене здесь будет реальный парсинг сайтов
                return await self._get_info_via_llm(product_name)

        except Exception as e:
            logger.error(f"Ошибка поиска информации о товаре {product_name}: {e}")
            return ""

    async def _get_info_via_llm(self, product_name: str) -> str:
        """
        Использует YandexGPT для получения информации о товаре
        (в будущем можно заменить на реальный парсинг сайтов)
        """
        from app.llm.yandex_client import YandexGPTClient

        llm = YandexGPTClient()

        prompt = f"""Найди подробные технические характеристики товара: {product_name}

Укажи:
- Основные технические параметры
- Размеры и вес
- Материалы
- Функции и возможности
- Совместимость
- Комплектация
- Примерную цену в рублях

Отвечай структурированно, только факты, без лишних слов."""

        try:
            info = await llm.generate(
                prompt=prompt,
                system_prompt="Ты эксперт по товарам. Давай точную техническую информацию.",
                temperature=0.3,
                max_tokens=1000
            )
            return info
        except Exception as e:
            logger.error(f"Ошибка получения информации через LLM: {e}")
            return ""

    async def search_price(self, product_name: str) -> str:
        """Ищет актуальную цену на товар"""
        from app.llm.yandex_client import YandexGPTClient

        llm = YandexGPTClient()

        prompt = f"""Найди актуальную цену на товар: {product_name}

Укажи:
- Цену в рублях
- Где можно купить (магазины)
- Есть ли скидки

Отвечай кратко и по делу."""

        try:
            price_info = await llm.generate(
                prompt=prompt,
                system_prompt="Ты ищешь актуальные цены на товары в России.",
                temperature=0.3,
                max_tokens=500
            )
            return price_info
        except Exception as e:
            logger.error(f"Ошибка поиска цены: {e}")
            return ""
