from numpy import median, array
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise
import matplotlib.pyplot as plt

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

def kalman_filter(prices: list) -> list:
    kf = KalmanFilter(2, 1)
    kf.x = array([[prices[0]], [0.]])
    kf.F = array([[1., 1.], [0., 1.]])
    kf.H = array([[1., 0.]])
    kf.R = array([[0.1]])
    kf.Q = Q_discrete_white_noise(dim=2, dt=1., var=1.0)
    kf.P *= 1000.
    filtered_prices = []
    for i in prices:
        kf.predict()
        kf.update(i)
        filtered_prices.append(kf.x[0, 0])
    return filtered_prices

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