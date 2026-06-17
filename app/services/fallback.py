from app.llm.exceptions import LLMError, LLMRateLimitError, LLMTimeoutError

async def handle_llm_error(error: LLMError) -> str:
    """
    Возвращает fallback-сообщение при ошибках LLM
    """
    if isinstance(error, LLMRateLimitError):
        return "⏸️ Технический перерыв: слишком много запросов. Ваш вопрос уже записан, менеджер скоро свяжется с вами!"
    elif isinstance(error, LLMTimeoutError):
        return "⏸️ Технический перерыв: ответ занимает слишком много времени. Ваш вопрос записан, менеджер скоро свяжется!"
    else:
        return "⏸️ Технический перерыв: временно недоступен. Ваш вопрос записан, менеджер скоро свяжется с вами!"
