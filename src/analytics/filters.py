from numpy import median, array
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise
import matplotlib.pyplot as plt
import json

def calculate_local_stats(data_window:list):
    local_median = float(median(data_window))
    local_mad = float(median(abs(array(data_window) - local_median)))
    return local_median, local_mad

def hampel_filter(data: list, window_size: int = 7) -> list:
    k_mad = 1.4826
    n = len(data)
    if n < (2 * window_size + 1):
        return data
    filtered_data = data.copy()
    for i in range(n):
        start_index = max(0, i - window_size)
        end_index = min(n, i + window_size + 1)
        window = filtered_data[start_index:end_index]
        local_median, local_mad = calculate_local_stats(window)
        if (local_mad != 0) and (abs(filtered_data[i] - local_median)> k_mad * local_mad * 3):
            filtered_data[i] = local_median
    return filtered_data

class Kalman_filter:
    def __init__(self, R: float = 0.1, Q: float = 1.0, P: float = 1000.0):
        self._kf = KalmanFilter(2, 1)
        self._kf.F = array([[1., 1.], [0., 1.]])
        self._kf.H = array([[1., 0.]])
        self._kf.R = array([[R]])
        self._kf.Q = Q_discrete_white_noise(dim=2, dt=1., var=Q)
        self._kf.P = P
    
    def initialize_state(self, initial_price: float) -> dict:
        self._kf.x = array([[initial_price], [0.]])
        self._kf.P = self._kf.P * self.P

    def set_state_from_json(self, x_json: str, P_json: str):
        self._kf.x = array(json.loads(x_json))
        self._kf.P = array(json.loads(P_json))

    def get_state_as_json(self) -> tuple[str, str]:
        return json.dumps(self._kf.x.tolist()), json.dumps(self._kf.P.tolist())
    
    def update(self, measurement: float) -> float:
        self._kf.predict()
        self._kf.update(measurement)
        return float(self._kf.x[0, 0])


def initialize_kalman_filter(initial_price: float) -> dict:
    kf = KalmanFilter(2, 1)
    kf.x = array([[initial_price], [0.]])
    kf.F = array([[1., 1.], [0., 1.]])
    kf.H = array([[1., 0.]])
    kf.R = array([[0.1]])
    kf.Q = Q_discrete_white_noise(dim=2, dt=1., var=1.0)
    kf.P *= 1000.
    return {
        'x': kf.x.tolist(),
        'P': kf.P.tolist()
    }

def kalman_filter_step(previous_state: dict, current_measurement: float) -> tuple[float, dict]:
    kf = KalmanFilter(2,1)
    kf.x = array(previous_state['x'])
    kf.P = array(previous_state['P'])
    kf.F = array([[1., 1.], [0., 1.]])
    kf.H = array([[1., 0.]])
    kf.R = array([[0.1]])
    kf.Q = Q_discrete_white_noise(dim=2, dt=1., var=1.0)
    kf.predict()
    kf.update(current_measurement)
    return float(kf.x[0,0]), {
        'x': kf.x.tolist(),
        'P': kf.P.tolist()
    }


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