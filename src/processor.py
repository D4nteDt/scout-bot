import logging
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy.orm import selectinload
from database.models import Item, ItemHistory, Watchlist
from analytics.filters_and_predict import (
    calculate_local_stats,
    Kalman_filter,
)
from sqlalchemy import select


class OracleProcessor:
    def __init__(self, sql_session: AsyncSession, bot):
        self.signal_threshold = 15
        self.signal_delta_threshold = 5
        self.bot = bot
        self.session = sql_session
        self.window_size = 31
        self.outlier_persistence_threshold = 5
        self.kalman_filters: dict[int, Kalman_filter] = {}
        self.signal_counters: dict[str, int] = {}

    def get_kalman_filter(self, item_id: int) -> Kalman_filter:
        if item_id not in self.kalman_filters:
            self.kalman_filters[item_id] = Kalman_filter(R=10.0, Q=0.05)

        return self.kalman_filters[item_id]

    def update_signal_counter(self, item_name: str, signal_active: bool) -> int:

        if item_name not in self.signal_counters:
            self.signal_counters[item_name] = 0

        if signal_active:
            self.signal_counters[item_name] += 1
        else:
            self.signal_counters[item_name] = 0
        return self.signal_counters[item_name]

    def __determine_price_for_kalman(
        self,
        past_prices: list,
        raw_price: float,
    ) -> tuple[bool, float]:

        if len(past_prices) < self.window_size - 1:
            return False, raw_price

        window_for_stats = past_prices[-(self.window_size - 1):]
        local_median, local_mad = (calculate_local_stats(window_for_stats))
        is_outlier = False
        threshold = 1.4826 * local_mad * 3
        if (local_mad != 0 and abs(raw_price - local_median) > threshold):
            is_outlier = True

        if is_outlier:
            price_for_kalman = (raw_price * 0.3 + local_median * 0.7)
        else:
            price_for_kalman = raw_price

        return is_outlier, price_for_kalman

    def initialize_or_load_kalman(self, item: Item, price_for_kalman: float) -> tuple[Kalman_filter, float]:
        kf = self.get_kalman_filter(item.id)
        if item.kalman_state_x and item.kalman_state_p:
            try:
                kf.set_state_from_json(
                    item.kalman_state_x,
                    item.kalman_state_p,
                )

                previous_kalman_estimation = float(
                    kf._kf.x[0, 0]
                )

            except Exception as e:
                logging.error(
                    f"Failed to load Kalman state "
                    f"for item {item.id}: {e}"
                )

                kf.initialize_state(price_for_kalman)
                previous_kalman_estimation = (
                    price_for_kalman
                )

        else:
            kf.initialize_state(price_for_kalman)
            previous_kalman_estimation = (
                price_for_kalman
            )

        return kf, previous_kalman_estimation

    async def get_kalman_prediction(self, item_id: int, steps: int = 5) -> tuple[float, float, float] | None:

        item = await self.session.get(Item, item_id)

        if (not item or not item.kalman_state_x or not item.kalman_state_p):
            logging.warning(
                f"Could not get Kalman state "
                f"for prediction for item {item_id}"
            )
            return None

        try:
            kf = self.get_kalman_filter(item_id)
            kf.set_state_from_json(item.kalman_state_x, item.kalman_state_p)
            predicted_price, forecast_uncertainty = (kf.forecast(steps=steps))
            predicted_trend = kf.get_trend()
            logging.info(
                f"Item {item_id} prediction: "
                f"price={predicted_price:.2f}, "
                f"trend={predicted_trend:.4f}, "
                f"uncertainty={forecast_uncertainty:.2f}"
            )

            return (
                predicted_price,
                predicted_trend,
                forecast_uncertainty,
            )

        except Exception as e:
            logging.error(
                f"Failed to predict Kalman state "
                f"for item {item_id}: {e}"
            )
            return None

    async def process_notifications(self, item: Item):
        prediction = await self.get_kalman_prediction(
            item.id,
            steps=5,
        )
        if prediction is None:
            return

        predicted_price, predicted_trend, forecast_uncertainty = prediction
        if (predicted_price is None or item.oracle_price is None):
            return

        if forecast_uncertainty > 100:
            logging.info(
                f"Forecast uncertainty too high "
                f"for item {item.id}: "
                f"{forecast_uncertainty:.2f}"
            )
            return

        signal_percent = (
            (predicted_price - item.oracle_price) / item.oracle_price) * 100

        signal_percent = round(signal_percent, 2)

        for watch in item.watchers:

            if watch.notification_type not in (
                "up",
                "down",
            ):
                continue

            signal_active = False

            if (watch.notification_type == "up"
                    and signal_percent >= self.signal_threshold
                    and predicted_trend > 0
                    ):
                signal_active = True

            elif (
                watch.notification_type == "down"
                and signal_percent <= -self.signal_threshold
                and predicted_trend < 0
            ):
                signal_active = True

            signal_count = self.update_signal_counter(
                f"{item.id}_{watch.notification_type}",
                signal_active,
            )

            if signal_count < 3:
                continue

            if watch.last_notification_at is not None:
                delta = (datetime.utcnow() - watch.last_notification_at)
                if delta.total_seconds() < 1800:
                    continue

            confidence = max(0.0, 100.0 - forecast_uncertainty,)
            await self.bot.send_message(
                chat_id=watch.user.telegram_id,
                text=(
                    f"Сигнал для {item.name}\n\n"
                    f"Текущая цена: "
                    f"{item.current_price:.2f} ₽\n"
                    f"Oracle цена: "
                    f"{item.oracle_price:.2f} ₽\n"
                    f"Предсказанная цена: "
                    f"{predicted_price:.2f} ₽\n"
                    f"Тренд: "
                    f"{predicted_trend:.4f}\n"
                    f"Уверенность: "
                    f"{confidence:.2f}%\n"
                    f"Неопределенность: "
                    f"{forecast_uncertainty:.2f}\n"
                    f"Потенциал: "
                    f"{signal_percent:.2f}%"
                )
            )

            watch.last_notification_at = (datetime.utcnow())
            await self.session.commit()

    async def update_item_price(
        self,
        item_id: int,
        raw_price: float,
        volume: int,
    ):

        stmt = (
            select(Item)
            .where(Item.id == item_id)
            .options(
                selectinload(Item.watchers)
                .selectinload(Watchlist.user)
            )
        )

        result = await self.session.execute(stmt)

        item = result.scalar_one_or_none()

        if not item:
            logging.warning(
                f"Item with ID {item_id} not found."
            )
            return

        result = await self.session.execute(
            select(ItemHistory)
            .filter_by(item_id=item_id)
            .order_by(ItemHistory.timestamp.desc())
            .limit(self.window_size)
        )

        history_entries = result.scalars().all()

        past_prices = [
            h.price
            for h in reversed(history_entries)
        ]

        (
            is_outlier,
            price_for_kalman,
        ) = self.__determine_price_for_kalman(
            past_prices,
            raw_price,
        )

        if (
            is_outlier
            and len(history_entries)
            >= (
                self.outlier_persistence_threshold
                - 1
            )
        ):

            past_outliers = [
                h.is_outlier
                for h in history_entries[
                    : self.outlier_persistence_threshold
                    - 1
                ]
            ]

            if all(past_outliers):
                is_outlier = False
                price_for_kalman = raw_price

        kf, previous_kalman_estimation = self.initialize_or_load_kalman(
            item, price_for_kalman)
        current_kalman_price = kf.update(price_for_kalman)
        trend = kf.get_trend()
        new_kalman_state_x_json, new_kalman_state_P_json = kf.get_state_as_json()

        new_history = ItemHistory(
            item_id=item_id,
            price=raw_price,
            volume=volume,
            kalman_price=current_kalman_price,
            is_outlier=is_outlier,
            timestamp=datetime.utcnow(),
        )

        self.session.add(new_history)

        item.current_price = raw_price
        item.oracle_price = current_kalman_price
        item.trend = trend
        item.last_updated = datetime.utcnow()
        item.kalman_state_x = (
            new_kalman_state_x_json
        )
        item.kalman_state_p = (
            new_kalman_state_P_json
        )

        try:
            await self.session.commit()

            await self.process_notifications(item)

        except Exception as e:
            await self.session.rollback()

            logging.error(
                f"Update failed for item "
                f"{item_id}: {e}"
            )
