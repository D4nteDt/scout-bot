from numpy import median, array

def calculate_local_stats(data_window:list):
    local_median = median(data_window)
    local_mad = median(abs(array(data_window) - local_median))
    return local_median, local_mad

def hampel_filter(data: list, window_size: int) -> list:
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
            filtered_data[i] = float(local_median)
    return filtered_data

print(hampel_filter([100, 101, 102, 550, 600, 101, 104], 3))