import asyncio
import aiohttp
from urllib.parse import quote
import logging

class SteamFetcher:
    def __init__(self, appid: int = 730, currency: int = 5, max_concurrent = 5): # <-- ИСПРАВЛЕНО: __init__ вместо init
        self.appid = appid
        self.currency = currency
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.base_url = "https://steamcommunity.com/market/priceoverview/" # <-- ИСПРАВЛЕНО: убрал &quot;

    def _clean_price(self, price_str: str) -> float:
        if not price_str: return 0.0
        clean_str = "".join(c for c in price_str[:-1] if c.isdigit() or c in ".,")
        try:
            return float(clean_str.replace(",", "."))
        except ValueError:
            return 0.0

    def _clean_volume(self, volume_str: str) -> int:
        if not volume_str: return 0
        return int(volume_str.replace(",", "").replace(".", ""))

    async def fetch_item(self, item_market_hash_name: str) -> dict: # <-- Изменил имя аргумента для ясности
        async with aiohttp.ClientSession() as session:

            async with self.semaphore:
                encoded_market_hash_name = quote(item_market_hash_name)
                url = f"{self.base_url}?appid={self.appid}&currency={self.currency}&market_hash_name={encoded_market_hash_name}"

                async with session.get(url) as response:
                    if response.status != 200:
                        logging.info(f"Ошибка сети для {item_market_hash_name}: {response.status}")
                        return None
            
                    data = await response.json()
                    
                    if not data or not data.get("success"):
                        logging.info(f"Steam API returned no success for {item_market_hash_name}. Data: {data}")
                        return None
                    
                    volume = self._clean_volume(data.get("volume"))
                    if volume <= 0:
                        logging.info(f"Steam API returned 0 or negative volume for {item_market_hash_name}. Volume: {volume}")
                        return None

                    display_name = data.get("item_name", item_market_hash_name) 

                    return {
                        "market_hash_name": item_market_hash_name,
                        "name": display_name,
                        "price": self._clean_price(data.get("lowest_price")),
                        "median": self._clean_price(data.get("median_price")),
                        "volume": volume
                    }
    
    async def fetch_all(self, item_market_hash_names: list):
        tasks = [self.fetch_item(market_hash_name) for market_hash_name in item_market_hash_names]
        results = await asyncio.gather(*tasks)
        return results