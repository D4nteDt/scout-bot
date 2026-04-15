from numpy import median, array
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise
import matplotlib.pyplot as plt
import json

def calculate_local_stats(data_window:list) -> tuple[float, float]:
    if not data_window:
        return 0.0, 0.0
    local_median = float(median(data_window))
    local_mad = float(median(abs(array(data_window) - local_median)))
    return local_median, local_mad

class Kalman_filter:
    def __init__(self, R: float = 0.1, Q: float = 1.0):
        self._kf = KalmanFilter(2, 1)
        self._kf.F = array([[1., 1.], [0., 1.]])
        self._kf.H = array([[1., 0.]])
        self._kf.R = array([[R]])
        self._kf.Q = Q_discrete_white_noise(dim=2, dt=1., var=Q)
        self._kf.P = 1000.0
    
    def initialize_state(self, initial_price: float) -> dict:
        self._kf.x = array([[initial_price], [0.]])
        self._kf.P = self._kf.P * 1000.0

    def set_state_from_json(self, x_json: str, P_json: str):
        self._kf.x = array(json.loads(x_json))
        self._kf.P = array(json.loads(P_json))

    def get_state_as_json(self) -> tuple[str, str]:
        return json.dumps(self._kf.x.tolist()), json.dumps(self._kf.P.tolist())
    
    def update(self, measurement: float) -> float:
        self._kf.predict()
        self._kf.update(measurement)
        return float(self._kf.x[0, 0])
    
    def predict_state(self, steps: int = 1) -> tuple[float, float]:
        for i in range(steps):
            self._kf.predict()
        predicted_price = float(self._kf.x[0, 0])
        predicted_trend = float(self._kf.x[1, 0])
        return predicted_price, predicted_trend
    
def plot_results(original, filtered):
    plt.figure(figsize=(12, 6))
    plt.plot(original, label='Сырые цены (Steam)', color='blue', alpha=0.4)
    plt.plot(filtered, label='Фильтр (Оракул)', color='red', linewidth=2)
    plt.title('Очистка цен')
    plt.xlabel('Время (точки измерения)')
    plt.ylabel('Цена')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.show()