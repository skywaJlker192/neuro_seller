import aiohttp
from typing import List, Dict
from app.config import settings
from .exceptions import LLMRateLimitError, LLMTimeoutError, LLMAPIError

class YandexGPTClient:
    def __init__(self):
        self.api_key = settings.YANDEX_API_KEY
        self.folder_id = settings.YANDEX_FOLDER_ID
        self.model = settings.YANDEX_MODEL or "yandexgpt-lite"
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    async def chat(self, messages: List[Dict[str, str]], max_tokens: int = 2000) -> str:
        """
        Отправляет запрос в YandexGPT и возвращает ответ

        Args:
            messages: История диалога в формате [{"role": "user", "text": "..."}, ...]
            max_tokens: Максимальное количество токенов в ответе
        """
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "modelUri": f"gpt://{self.folder_id}/{self.model}",
            "completionOptions": {
                "stream": False,
                "temperature": 0.6,
                "maxTokens": str(max_tokens)
            },
            "messages": messages
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 429:
                        raise LLMRateLimitError("Превышен лимит запросов к YandexGPT")
                    elif response.status == 408:
                        raise LLMTimeoutError("Таймаут запроса к YandexGPT")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise LLMAPIError(f"Ошибка API YandexGPT: {response.status} - {error_text}")

                    data = await response.json()
                    return data["result"]["alternatives"][0]["message"]["text"]

        except aiohttp.ClientError as e:
            raise LLMAPIError(f"Сетевая ошибка при обращении к YandexGPT: {str(e)}")
