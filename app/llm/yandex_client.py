import aiohttp
from loguru import logger
from app.config import settings


class YandexGPTClient:
    """Клиент для работы с YandexGPT API"""

    def __init__(self):
        self.api_key = settings.YANDEX_API_KEY
        self.folder_id = settings.YANDEX_FOLDER_ID
        self.model = getattr(settings, 'YANDEX_MODEL', 'yandexgpt-lite')
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.6,
        max_tokens: int = 1500
    ) -> str:
        """Генерирует ответ через YandexGPT"""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}"
        }

        # Формируем сообщения
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "text": system_prompt
            })
        messages.append({
            "role": "user",
            "text": prompt
        })

        payload = {
            "modelUri": f"gpt://{self.folder_id}/{self.model}",
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": max_tokens
            },
            "messages": messages
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        alternatives = result.get("result", {}).get("alternatives", [])
                        if alternatives:
                            text = alternatives[0]["message"]["text"]
                            logger.info(f"YandexGPT ответ получен ({len(text)} символов)")
                            return text
                        else:
                            logger.error(f"Нет alternatives в ответе: {result}")
                            return ""
                    else:
                        error_text = await response.text()
                        logger.error(f"YandexGPT ошибка {response.status}: {error_text}")
                        return ""

        except Exception as e:
            logger.error(f"YandexGPT исключение: {e}")
            return ""
