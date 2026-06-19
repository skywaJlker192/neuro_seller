from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ServiceItem(BaseModel):
    """Схема одной услуги"""
    name: str = Field(..., description="Название услуги")
    price: str = Field(default="", description="Цена услуги")
    duration: str = Field(default="", description="Длительность услуги")


class CategoryItem(BaseModel):
    """Схема одной категории"""
    id: str = Field(..., description="Уникальный ID категории")
    emoji: str = Field(default="", description="Эмодзи категории")
    name: str = Field(..., description="Название категории")
    description: str = Field(default="", description="Описание категории")
    services: List[ServiceItem] = Field(default_factory=list, description="Список услуг в категории")


class NicheConfig(BaseModel):
    """Схема конфигурации ниши из YAML-файла"""

    business_name: str = Field(..., description="Название бизнеса")
    business_type: str = Field(default="shop", description="Тип бизнеса: shop или services")
    product_description: str = Field(..., description="Описание продукта или услуги")
    tone: str = Field(default="friendly", description="Стиль общения")

    fields_to_collect: List[str] = Field(
        default=["name", "interest", "budget", "contact"],
        description="Список полей для сбора у клиента"
    )

    manager_instructions: Optional[str] = Field(
        default=None,
        description="Дополнительные инструкции для менеджера"
    )

    welcome_text: Optional[str] = Field(
        default=None,
        description="Текст приветствия при /start"
    )

    categories: List[CategoryItem] = Field(
        default_factory=list,
        description="Список категорий для клавиатуры"
    )

    product_catalog: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Каталог товаров с ценами"
    )

    service_catalog: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Каталог услуг с ценами"
    )
