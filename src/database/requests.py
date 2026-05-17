from sqlalchemy import select
from database.models import User, Item
from sqlalchemy.ext.asyncio import AsyncSession
from parser.fetcher import SteamFetcher
import logging
async def get_or_create_user(session: AsyncSession, tg_id: int, username: str | None):
    tg_id_str = str(tg_id)
    result = await session.execute(select(User).where(User.telegram_id == tg_id_str))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            telegram_id = tg_id_str,
            username = username,
        )
        return True, user
    return False, user

async def get_or_create_item(session: AsyncSession, item_name: str):
    stmt = select(Item).where(Item.name == item_name)
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()

    if item:
        return item, False

    pars = SteamFetcher()
    steam_data = None
    try:
        steam_data = await pars.fetch_item(item_name)
        if not steam_data or not steam_data.get('market_hash_name') or steam_data.get('price') == 0.0:
            logging.info(f"Steam fetch for '{item_name}' returned incomplete data or 0.0 price: {steam_data}. Treating as not found.")
            steam_data = None
    except Exception as e:
        logging.error(f"Error fetching item '{item_name}' from Steam: {e}", exc_info=True)
        steam_data = None

    if steam_data:
        item = Item(
            market_hash_name=steam_data['market_hash_name'],
            name=item_name,
            current_price=steam_data['price'],
            oracle_price=0.0,
            trend=0.0
        )
        session.add(item)
        await session.flush()
        return item, True
    else:
        return None, False