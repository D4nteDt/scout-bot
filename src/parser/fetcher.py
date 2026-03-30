import asyncio
import aiohttp
from urllib.parse import quote

class SteamFetcher:
    def __init__(self, appid: int = 730, currency: int = 5, max_concurrent = 5):
        self.appid = appid
        self.currency = currency
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.base_url = "https://steamcommunity.com/market/priceoverview/"

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

    async def fetch_item(self, session: aiohttp.ClientSession, item_name: str) -> dict:
        async with self.semaphore:
            encoded_name = quote(item_name)
            url = f"{self.base_url}?appid={self.appid}&currency={self.currency}&market_hash_name={encoded_name}"
        
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Ошибка сети: {response.status}")
                    return None
            
                data = await response.json()
                if data and data.get("success"):
                    return {
                        "name": item_name,
                        "price": self._clean_price(data.get("lowest_price")),
                        "median": self._clean_price(data.get("median_price")),
                        "volume": self._clean_volume(data.get("volume"))
                    }
                return None
    async def fetch_all(self, session, item_list):
        tasks = [self.fetch_item(session, item) for item in item_list]
        results = await asyncio.gather(*tasks)
        return results