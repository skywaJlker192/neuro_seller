from pydantic import BaseModel, Field
from typing import List, Optional

class NicheConfig(BaseModel):
    """Схема конфигурации ниши из YAML-файла"""

    business_name: str = Field(..., description="Название бизнеса")
    product_description: str = Field(..., description="Описание продукта или услуги")
    tone: str = Field(default="friendly", description="Стиль общения: friendly, formal, expert, casual")
    fields_to_collect: List[str] = Field(
        default=["name", "interest", "budget", "contact"],
        description="Список полей для сбора у клиента"
    )
    manager_instructions: Optional[str] = Field(
        default=None,
        description="Дополнительные инструкции для менеджера"
    )
