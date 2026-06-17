import yaml
from pathlib import Path
from app.niche.schemas import NicheConfig

def load_niche(file_path: str | Path) -> NicheConfig:
    """
    Загружает конфигурацию ниши из YAML-файла

    Args:
        file_path: Путь к YAML-файлу с настройками ниши

    Returns:
        Объект NicheConfig с валидированными данными

    Raises:
        FileNotFoundError: Если файл не найден
        yaml.YAMLError: Если файл некорректный YAML
        pydantic.ValidationError: Если данные не проходят валидацию
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Конфиг ниши не найден: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Файл ниши пуст: {path}")

    return NicheConfig(**data)
