class LLMError(Exception):
    """Базовое исключение для ошибок LLM"""
    pass

class LLMRateLimitError(LLMError):
    """Превышен лимит запросов"""
    pass

class LLMTimeoutError(LLMError):
    """Таймаут запроса"""
    pass

class LLMAPIError(LLMError):
    """Ошибка API"""
    pass
