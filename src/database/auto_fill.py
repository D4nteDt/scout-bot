import asyncio
import aiohttp
import sys
import os

print("1. Начало")

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'parser'))
print("2. Путь добавлен")

try:
    from fetcher import SteamFetcher, SteamMarketExplorer
    print("3. SteamFetcher и SteamMarketExplorer импортированы")
except Exception as e:
    print(f"Ошибка: {e}")
    sys.exit(1)

try:
    import bazaIvanaNesveteeva as db
    print("4. База данных импортирована")
except Exception as e:
    print(f"Ошибка: {e}")
    sys.exit(1)

async def main():
    print("5. Внутри main()")
    
    print("6. Создаю Explorer...")
    explorer = SteamMarketExplorer()
    
    print("7. Получаю список предметов...")
    items = await explorer.get_items_list(max_items=10)
    
    print(f"8. Получено {len(items)} предметов")
    
    if items:
        print("Первые 3 предмета:")
        for i, item in enumerate(items[:3]):
            print(f"   {i+1}. {item}")

print("9. Запускаю asyncio...")
asyncio.run(main())
print("10. Готово!")