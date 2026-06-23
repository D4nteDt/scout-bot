from numpy import median, array
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise
import matplotlib.pyplot as plt
import numpy as np
import json
import io


def calculate_local_stats(data_window: list) -> tuple[float, float]:
    if not data_window:
        return 0.0, 0.0

    local_median = float(median(data_window))
    local_mad = float(median(abs(array(data_window) - local_median)))
    return local_median, local_mad


class Kalman_filter:
    def __init__(self, R: float = 2.0, Q: float = 0.005, dt: float = 1.0, initial_P: float = 48_000_000.0):
        self._kf = KalmanFilter(2, 1)

        self._kf.F = array([
            [1., 1.],
            [0., 1.],
        ])

        self._kf.H = array([[1., 0.]])
        self._kf.R = array([[R]])
        self._kf.Q = Q_discrete_white_noise(
            dim=2,
            dt=dt,
            var=Q,
        )

        self._kf.P = np.eye(2) * initial_P

    def initialize_state(self, initial_price: float, initial_P: float = 48_000_000.0):
        self._kf.x = array([
            [initial_price],
            [0.],
        ])

        self._kf.P = np.eye(2) * initial_P

    def set_state_from_json(self, x_json: str, P_json: str):
        self._kf.x = array(json.loads(x_json))
        self._kf.P = array(json.loads(P_json))

    def get_state_as_json(self) -> tuple[str, str]:
        return (
            json.dumps(self._kf.x.tolist()),
            json.dumps(self._kf.P.tolist()),
        )

    def update(self, measurement: float) -> float:
        self._kf.predict()
        self._kf.update(measurement)

        return float(self._kf.x[0, 0])

    def get_trend(self) -> float:
        return float(self._kf.x[1, 0])

    def get_uncertainty(self) -> float:
        return float(np.trace(self._kf.P))

    def forecast(self, steps: int = 1) -> tuple[float, float]:
        x = self._kf.x.copy()
        P = self._kf.P.copy()
        for _ in range(steps):
            x = self._kf.F @ x
            P = self._kf.F @ P @ self._kf.F.T + self._kf.Q

        predicted_price = float(x[0, 0])
        uncertainty = float(np.trace(P))
        return predicted_price, uncertainty


def plot_results(original: list, filtered: list):
    plt.figure(figsize=(12, 6))
    plt.plot(original, label='Original', alpha=0.4)
    plt.plot(filtered, label='Filtered', linewidth=2)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    result = io.BytesIO()
    plt.savefig(result, format='png')
    result.seek(0)
    plt.close()

    return result
