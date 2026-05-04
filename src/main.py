import asyncio
import aiohttp
import logging
from bot.bot import dp, bot
from bot.handlers import router
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Base, Item
from processor import OracleProcessor 
from database.database import engine, AsyncSessionLocal 
from parser.fetcher import SteamFetcher
logging.basicConfig(level=logging.INFO)

async def init_db(engine_obj):
    logging.info("Initializing database")
    async with engine_obj.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logging.info("Database initialized.")

async def process_and_update_prices(session: AsyncSession, processor: OracleProcessor, fetched_data: list):
    for data in fetched_data:
        if not data or not all(key in data for key in ['name', 'price', 'volume']):
            logging.warning(f"Skipping invalid data entry: {data}")
            continue

        item_name = data['name']
        raw_price = data['price']
        volume = data['volume']
        stmt = select(Item).where(Item.market_hash_name == item_name) 
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()
        item_id = None
        if not item:
            logging.info(f"Item '{item_name}' not found.")
            item = Item(market_hash_name=item_name, name=item_name, current_price = 0.0, oracle_price = 0.0, trend = 0.0)
            session.add(item)
            await session.flush()
            item_id = item.id
            logging.info(f"Created new item '{item_name}' with ID: {item_id}")
        else:
            item_id = item.id
            logging.info(f"Found item '{item_name}' with ID: {item_id}")
        if item_id:
            try:
                logging.info(f" Updating price for Item ID {item_id} (Price: {raw_price}, Volume: {volume})")
                await processor.update_item_price(item_id, raw_price, volume)
                updated_item = await session.get(Item, item_id) 
                if updated_data := updated_item:
                    logging.info(f"Item {item_id} (DB Updated): Raw Price={updated_data.current_price:.2f}, Oracle Price={updated_data.oracle_price:.2f}, Trend={updated_data.trend:.4f}")     
                    prediction_steps = 5
                    predicted_data = await processor.get_kalman_prediction(item_id, steps=prediction_steps)
                    
                    if predicted_data:
                        predicted_price, predicted_trend = predicted_data
                        logging.info(f"Prediction ({prediction_steps} steps): Price={predicted_price:.2f}, Trend={predicted_trend:.4f}")
                    else:
                        logging.warning(f"Failed to get prediction for item {item_id}.")
                else:
                    logging.warning(f"Could not retrieve updated item {item_id} after processing.")

            except Exception as e:
                logging.error(f"Error processing item ID {item_id} (Name: {item_name}, Price: {raw_price}): {e}", exc_info=True)
        else:
            logging.error(f"Could not obtain item ID for item '{item_name}'. Skipping update.")

async def run_parser_loop():
    logging.info("Starting Steam Parser Loop")
    async with aiohttp.ClientSession() as http_session:
        while True:
            try:
                fetcher = SteamFetcher()
                stmt = select(Item.name)
                names = (await session.execute(stmt)).scalars().all()
                fetched_data = await fetcher.fetch_all(http_session, names)
                if fetched_data:
                    async with AsyncSessionLocal() as session:
                        processor = OracleProcessor(sql_session=session)
                        await process_and_update_prices(session, processor, fetched_data)
            except Exception as e:
                logging.error(f"Parser Error: {e}")
            await asyncio.sleep(30)

async def main():
    await init_db(engine)
    dp.include_router(router)
    logging.info("System is starting...")
    parser_task = asyncio.create_task(run_parser_loop())
    try:
        await dp.start_polling(bot, session_pool=AsyncSessionLocal)
    finally:
        parser_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())