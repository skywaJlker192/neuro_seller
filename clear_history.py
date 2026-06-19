import asyncio
import os
from pathlib import Path

# Удаляем файл БД
db_file = Path("bot.db")
if db_file.exists():
    db_file.unlink()
    print(f"✅ Файл {db_file} удалён!")
else:
    print("❌ Файл БД не найден")

# Очищаем current_niche.txt
niche_file = Path("current_niche.txt")
if niche_file.exists():
    niche_file.write_text("default", encoding="utf-8")
    print("✅ Ниша сброшена на default")
