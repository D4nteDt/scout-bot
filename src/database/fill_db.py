print("=== НАЧАЛО СКРИПТА ===")

import asyncio
import aiohttp
import sys
import os

print("Импорты выполнены")

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'parser'))
print("Путь добавлен")

try:
    from fetcher import SteamFetcher
    print("SteamFetcher импортирован")
except Exception as e:
    print(f"Ошибка импорта fetcher: {e}")
    sys.exit(1)

try:
    from bazaIvanaNesveteeva import save_items_from_parser
    print("save_items_from_parser импортирована")
except Exception as e:
    print(f"Ошибка импорта базы: {e}")
    sys.exit(1)

print("=== НАЧАЛО ПАРСИНГА ===")

async def main():
    print("Внутри main()")
    
    items = [
        "AK-47 | Redline (Field-Tested)",
        "AWP | Dragon Lore (Factory New)"
    ]
    print(f"Предметы для парсинга: {items}")
    
    fetcher = SteamFetcher()
    print("Парсер создан")
    
    async with aiohttp.ClientSession() as session:
        print("Сессия создана, начинаю запросы...")
        results = await fetcher.fetch_all(session, items)
        print("Запросы выполнены")
    
    for item in results:
        if item:
            print(f"Получено: {item['name']} - {item['price']} руб.")
        else:
            print("Не удалось получить данные для предмета")
    
    print("Сохраняю в базу...")
    save_items_from_parser(results)
    print("Готово!")

print("Запускаю asyncio...")
asyncio.run(main())
print("=== КОНЕЦ СКРИПТА ===")