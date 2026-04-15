import logging
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from database.models import Item, ItemHistory
from analytics.filters_and_predict import calculate_local_stats, Kalman_filter
from sqlalchemy import select

class OracleProcessor:
    def __init__(self, sql_session: AsyncSession):
        self.session = sql_session
        self.window_size = 101
        self.outlier_persistence_threshold = 5
        self.kalman_filter = Kalman_filter()

    def __determine_price_for_kalman(self, past_prices:list, raw_price: float) -> tuple[bool, float]:
        if len(past_prices) < self.window_size - 1:
            return False, raw_price
        window_for_stats = past_prices[-(self.window_size - 1):] if len(past_prices) >= (self.window_size - 1) else past_prices
        local_median, local_mad = calculate_local_stats(window_for_stats)
        is_outlier = False
        if (local_mad != 0) and (abs(raw_price - local_median) > 1.4826 * local_mad * 3):
            is_outlier = True
        return is_outlier, (local_median if is_outlier else raw_price)
    
    def initialize_or_load_kalman(self, item: Item, price_for_kalman: float) -> float:
        if item.kalman_state_x and item.kalman_state_p:
            try:
                self.kalman_filter.set_state_from_json(item.kalman_state_x, item.kalman_state_p)
                previous_kalman_estimation = self.kalman_filter._kf.x[0,0]
            except Exception as e:
                logging.error(f"Failed to load Kalman state for item {item.id} from JSON: {e}.")
                self.kalman_filter.initialize_state(price_for_kalman)
                previous_kalman_estimation = price_for_kalman
        else:
            self.kalman_filter.initialize_state(price_for_kalman)
            previous_kalman_estimation = price_for_kalman
        return previous_kalman_estimation

    async def get_kalman_prediction(self, item_id: int, steps: int = 5) -> tuple[float, float] | None:
        item = await self.session.get(Item, item_id)
        if not item or not item.kalman_state_x or not item.kalman_state_p:
            logging.warning(f"Could not get Kalman state for prediction for item {item_id}. State x: {item.kalman_state_x}, State P: {item.kalman_state_p}")
            return None 

        try:
            self.kalman_filter.set_state_from_json(item.kalman_state_x, item.kalman_state_p)
            temp_kalman_for_prediction = Kalman_filter()
            temp_kalman_for_prediction.set_state_from_json(item.kalman_state_x, item.kalman_state_p)
            predicted_price, predicted_trend = temp_kalman_for_prediction.predict_state(steps=steps)
            return predicted_price, predicted_trend
        except Exception as e:
            logging.error(f"Failed to predict Kalman state for item {item_id}: {e}")
            return None

    async def update_item_price(self, item_id: int, raw_price: float, volume: int):
        item = await self.session.get(Item, item_id)
        if not item:
            logging.warning(f"Item with ID {item_id} not found. Skipping price update.")
            return

        result = await self.session.execute(select(ItemHistory).filter_by(item_id=item_id).order_by(ItemHistory.timestamp.desc()).limit(self.window_size))
        history_entries = result.scalars().all()
        past_prices = [h.price for h in reversed(history_entries)]
        is_outlier, price_for_kalman = self.__determine_price_for_kalman(past_prices, raw_price)
        if is_outlier and len(history_entries) >= (self.outlier_persistence_threshold - 1):
            past_outliers = [h.is_outlier for h in history_entries[:self.outlier_persistence_threshold - 1]]
            if all(past_outliers):
                is_outlier = False
                price_for_kalman = raw_price
        
        previous_kalman_estimation = self.initialize_or_load_kalman(item, price_for_kalman)
        current_kalman_price = self.kalman_filter.update(price_for_kalman)
        trend = current_kalman_price - previous_kalman_estimation
        new_kalman_state_x_json, new_kalman_state_P_json = self.kalman_filter.get_state_as_json()
        new_history = ItemHistory(
            item_id = item_id,
            price = raw_price,
            volume = volume,
            kalman_price = current_kalman_price,
            is_outlier = is_outlier,
            timestamp = datetime.utcnow()
        )
        self.session.add(new_history)
        
        item.current_price = raw_price 
        item.oracle_price = current_kalman_price
        item.trend = trend
        item.last_updated = datetime.utcnow()
        item.kalman_state_x = new_kalman_state_x_json
        item.kalman_state_p = new_kalman_state_P_json
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()