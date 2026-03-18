import asyncio
import aiohttp
import configs

from parser.fetcher import SteamFetcher

async def main():
    app_id = configs.APP_ID
    currency = configs.CURRENCY
    items = configs.ITEMS_TO_TRACK
    
    fetcher = SteamFetcher(appid=app_id, currency=currency)
    
    async with aiohttp.ClientSession() as session:
        print(f"Начинаем сбор данных для {len(items)} предметов...")
        
        all_items_data = await fetcher.fetch_all(session, items)
        
        successful_data = [item for item in all_items_data if item is not None]
        
        print(f"Получены данные для {len(successful_data)} предметов.")

        for item_data in successful_data:
            print(item_data)

if __name__ == "__main__":
    asyncio.run(main())