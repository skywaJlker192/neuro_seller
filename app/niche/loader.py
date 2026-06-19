import yaml
from pathlib import Path
from app.niche.schemas import NicheConfig

# Путь к папке с конфигами ниш
NICHES_DIR = Path("niches")

def load_niche(niche_name: str) -> NicheConfig:
    """
    Загружает конфигурацию ниши из YAML-файла

    Args:
        niche_name: Название ниши (например: "default", "beauty_salon", "auto_service")

    Returns:
        Объект NicheConfig с валидированными данными

    Raises:
        FileNotFoundError: Если файл не найден
        yaml.YAMLError: Если файл некорректный YAML
        pydantic.ValidationError: Если данные не проходят валидацию
    """
    # Если передан полный путь — используем его
    if "/" in niche_name or "\\" in niche_name or niche_name.endswith(".yaml"):
        path = Path(niche_name)
    else:
        # Иначе ищем в папке niches/
        path = NICHES_DIR / f"{niche_name}.yaml"

    if not path.exists():
        raise FileNotFoundError(f"Конфиг ниши не найден: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Файл ниши пуст: {path}")

    return NicheConfig(**data)
