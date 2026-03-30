import asyncio
import aiohttp
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'parser'))

from fetcher import SteamFetcher, SteamMarketExplorer
import bazaIvanaNesveteeva as db

async def main():
    print("=" * 50)
    print("АВТОМАТИЧЕСКИЙ СБОР ДАННЫХ STEAM MARKET")
    print("=" * 50)
    
    # 1. Получаем список предметов
    print("\n1. Получение списка предметов...")
    explorer = SteamMarketExplorer()
    items = await explorer.get_items_list(max_items=50)
    print(f"   ✅ Получено {len(items)} предметов")
    
    # 2. Сохраняем названия в базу
    print("\n2. Сохранение названий в базу...")
    db.add_items(items)
    print(f"   ✅ Названия сохранены")
    
    # 3. Получаем цены для всех предметов с задержками
    print("\n3. Получение цен...")
    fetcher = SteamFetcher(max_concurrent=2)  # Уменьшаем количество одновременных запросов
    
    all_prices = []
    batch_size = 5  # Уменьшаем размер пакета
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        print(f"   Обрабатываю предметы {i+1}-{min(i+batch_size, len(items))} из {len(items)}...")
        
        async with aiohttp.ClientSession() as session:
            prices = await fetcher.fetch_all(session, batch)
            all_prices.extend(prices)
        
        # Ждем 2 секунды между пакетами, чтобы не получить блокировку
        print(f"   Ожидание 2 секунды...")
        await asyncio.sleep(2)
    
    # 4. Сохраняем цены в базу
    print("\n4. Сохранение цен в базу...")
    db.save_prices(all_prices)
    
    # 5. Статистика
    print("\n5. Статистика:")
    valid_prices = [p for p in all_prices if p and p['price'] > 0]
    print(f"   ✅ Всего предметов: {len(items)}")
    print(f"   ✅ С ценами: {len(valid_prices)}")
    print(f"   ❌ Без цен: {len(items) - len(valid_prices)}")
    
    print("\n" + "=" * 50)
    print("ГОТОВО!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())