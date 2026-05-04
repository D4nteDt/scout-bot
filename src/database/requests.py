from sqlalchemy import select
from database.models import User, Item, watchlists
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from parser.fetcher import SteamFetcher
async def get_or_create_user(session: AsyncSession, tg_id: int, username: str | None):
    tg_id_str = str(tg_id)
    result = await session.execute(select(User).where(User.telegram_id == tg_id_str))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            telegram_id = tg_id_str,
            username = username,
            created_at = datetime.now(timezone.utc)
        )
        return True, user
    return False, user

async def get_or_create_item(session: AsyncSession, item_name: str):
    stmt = select(watchlists).where(Item.name == item_name)
    item = await session.execute(stmt).scalar_one_or_none()
    if item:
        return item, False
    steam_data = await SteamFetcher.fetch_item(item_name=item_name)
    if steam_data:
        item = Item(
            market_hash_name = steam_data['market_hash_name'],
            name = item_name,
            current_price = steam_data['price']
        )
        session.add(item)
        await session.flush()
        return item, True
    return None, False