import json
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.models import Item, ItemHistory
from src.analytics.filters import calculate_local_stats, Kalman_filter

class OracleProcessor:
    def __init__(self, sql_session: Session):
        self.session = sql_session
        self.outlier_persistence_threshold = 5
        self.kalman_filter = Kalman_filter()
    def determine_price_for_kalman(self, past_prices:list, history_entries: list, raw_price: float, window_size:int) -> tuple[bool, float]:
        if len(past_prices) < window_size - 1:
            return False, raw_price
        window_for_stats = past_prices[-(window_size - 1):] if len(past_prices) >= (window_size - 1) else past_prices
        local_median, local_mad = calculate_local_stats(window_for_stats)
        k_mad = 1.4826
        is_outlier = False
        if (local_mad != 0) and (abs(raw_price - local_median) > k_mad * local_mad * 3):
            is_outlier = True
        return is_outlier, (local_median if is_outlier else raw_price)