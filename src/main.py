import asyncio
import logging
from bot.bot import dp, bot
from bot.keyboards import private
from bot.handlers import router
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Base, Item
from processor import OracleProcessor
from database.database import engine, AsyncSessionLocal
from database.midleware import DbSessionMiddleware
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
        if not data or not all(key in data for key in ['name', 'price', 'volume', 'market_hash_name']):
            logging.warning(f"Skipping invalid data entry: {data}")
            continue

        item_name_from_steam = data['name']
        market_hash_name_from_steam = data['market_hash_name']
        raw_price = data['price']
        volume = data['volume']

        stmt = select(Item).where(Item.market_hash_name == market_hash_name_from_steam)
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()

        if not item:
            logging.warning(f"Item with market_hash_name '{market_hash_name_from_steam}' not found in DB for update. Skipping.")
            continue

        item_id = item.id
        logging.info(f"Found item '{item.name}' with ID: {item_id}")

        try:
            logging.info(f" Updating price for Item ID {item_id} (Price: {raw_price}, Volume: {volume})")
            await processor.update_item_price(item_id, raw_price, volume)
            
            updated_item = await session.get(Item, item_id) 
            if updated_item:
                logging.info(f"Item {item_id} (DB Updated): Raw Price={updated_item.current_price:.2f}, Oracle Price={updated_item.oracle_price:.2f}, Trend={updated_item.trend:.4f}")     
                prediction_steps = 5
                predicted_data = await processor.get_kalman_prediction(item_id, steps=prediction_steps)
                
                if predicted_data:
                    predicted_price, predicted_trend = predicted_data
                    logging.info(f"Prediction ({prediction_steps} steps): Price={predicted_price:.2f}, Trend={predicted_trend:.4f}")
                else:
                    logging.warning(f"Failed to get prediction for item {item_id}.")
            else:
                logging.warning(f"Could not retrieve updated item {item_id} after processing (item might have been deleted).")

        except Exception as e:
            logging.error(f"Error processing item ID {item_id} (Name: {item_name_from_steam}, Price: {raw_price}): {e}", exc_info=True)


async def run_parser_loop(session: AsyncSession):
    logging.info("Starting Steam Parser Loop")
    while True:
        try:
            fetcher = SteamFetcher()
            stmt = select(Item.appid, Item.market_hash_name)
            result = await session.execute(stmt)
            market_items = [
                {
                    "appid": appid,
                    "market_hash_name": market_hash_name
                }
                for appid, market_hash_name in result.all()
            ]
            
            if not market_items:
                logging.info("No items in DB to fetch. Waiting...")
                await asyncio.sleep(30)
                continue

            logging.info(f"Fetching data for market_hash_names: {market_items}")
            fetched_data_raw = await fetcher.fetch_all(market_items)
            fetched_data = [d for d in fetched_data_raw if d is not None]
            if fetched_data:
                async with AsyncSessionLocal() as write_session:
                    processor = OracleProcessor(sql_session=write_session, bot=bot)
                    await process_and_update_prices(write_session, processor, fetched_data)
            else:
                logging.info("No valid data fetched from Steam for any item. Waiting...")
            
            await asyncio.sleep(240)

        except asyncio.CancelledError:
            logging.info("Parser loop cancelled.")
            break
        except Exception as e:
            logging.error(f"Parser loop error: {e}", exc_info=True)
            await asyncio.sleep(240)

async def main():
    await init_db(engine)
    dp.update.middleware(DbSessionMiddleware(AsyncSessionLocal))
    dp.include_router(router)
    await bot.set_my_commands(private)
    logging.info("System is starting...")
    
    async with AsyncSessionLocal() as parser_read_session:
        parser_task = asyncio.create_task(run_parser_loop(parser_read_session))
        try:
            await dp.start_polling(bot, session_pool=AsyncSessionLocal)
        finally:
            parser_task.cancel()
            try:
                await parser_task
            except asyncio.CancelledError:
                logging.info("Parser task finished gracefully.")
            except Exception as e:
                logging.error(f"Error waiting for parser task to finish: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())