import asyncio
import aiohttp
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Base, Item
from processor import OracleProcessor 
from database.database import engine, AsyncSessionLocal 
from parser.fetcher import SteamFetcher
from config.configs import items_to_track 

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


async def main():
    logging.info("Starting main application loop")

    await init_db(engine)
    try:
        async with aiohttp.ClientSession() as http_session:
            while True:
                logging.info("Starting price update cycle")
                try:
                    fetcher = SteamFetcher()
                    fetched_data = await fetcher.fetch_all(http_session, items_to_track)
                    if not fetched_data:
                        logging.warning("No data fetched from Steam. Waiting for next cycle.")
                    else:
                        async with AsyncSessionLocal() as session:
                            processor = OracleProcessor(sql_session=session)
                            await process_and_update_prices(session, processor, fetched_data)
                except Exception as e:
                    logging.error(f"Error during fetching or processing Steam data: {e}", exc_info=True)
                sleep_time = 30
                logging.info(f"Price update cycle finished. Sleeping for {sleep_time} seconds")
                await asyncio.sleep(sleep_time)

    except asyncio.CancelledError:
        logging.info("Main loop cancelled. Shutting down.")
    except Exception as e:
        logging.critical(f"An unexpected critical error occurred in the main loop: {e}", exc_info=True)
    finally:
        logging.info("Main application loop stopped.")
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Application interrupted by user.")