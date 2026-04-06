import asyncio
import aiohttp
from config.configs import items_to_track
from database.database import AsyncSessionLocal
from database.models import Item, ItemHistory
from parser.fetcher import SteamFetcher
from sqlalchemy import select

async def process_steam_data(results_parser):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for data in results_parser:
                if not data: continue
                
                stmt = select(Item).where(Item.market_hash_name == data['name'])
                result = await session.execute(stmt)
                item = result.scalar_one_or_none()
                
                if not item:
                    item = Item(market_hash_name=data['name'], name=data['name'])
                    session.add(item)
                    await session.flush()
                
                history = ItemHistory(
                    item_id=item.id,
                    price=data['price']
                )
                session.add(history)
                
                print(f"-> {data['name']}: {data['price']} $ [SAVED]")

async def main():
    async with aiohttp.ClientSession() as session:
        while True:
            print("\n--- Запуск цикла обновления цен ---")
            
            results = await SteamFetcher().fetch_all(session, items_to_track)
            
            await process_steam_data(results)
            
            print("Спим 30 секунд...")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())