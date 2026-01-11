import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor

def analyze_city(city, group_df):
    group = group_df.sort_values('timestamp').set_index('timestamp')
    window = 30
    group['rolling_mean'] = group['temperature'].rolling(window=window, min_periods=1).mean()
    group['rolling_std'] = group['temperature'].rolling(window=window, min_periods=1).std()
    group['is_anomaly'] = np.abs(group['temperature'] - group['rolling_mean']) > 2 * group['rolling_std']
    
    seasonal_stats = group.reset_index().groupby('season')['temperature'].agg(['mean', 'std']).reset_index()
    seasonal_stats.columns = ['season', 'seasonal_mean', 'seasonal_std']
    seasonal_stats['city'] = city
    
    group = group.reset_index()
    group = group.merge(seasonal_stats[['season', 'seasonal_mean', 'seasonal_std']], on='season', how='left')
    return group, seasonal_stats

def analyze_city_wrapper(args):
    return analyze_city(*args)

def run_analysis(df, use_parallel=True):
    groups = [(c, df[df['city'] == c]) for c in df['city'].unique()]
    if use_parallel:
        with ProcessPoolExecutor() as executor:
            results = list(executor.map(analyze_city_wrapper, groups))
    else:
        results = [analyze_city_wrapper(g) for g in groups]
    full_df = pd.concat([r[0] for r in results], ignore_index=True)
    seasonal_all = pd.concat([r[1] for r in results], ignore_index=True)
    return full_df, seasonal_all

if __name__ == '__main__':
    df = pd.read_csv('temperature_data.csv', parse_dates=['timestamp'])
    
    import time
    start = time.time()
    _, _ = run_analysis(df, use_parallel=False)
    seq_time = time.time() - start

    start = time.time()
    full_df, seasonal_stats = run_analysis(df, use_parallel=True)
    par_time = time.time() - start

    print(f"Последовательно: {seq_time:.2f} сек")
    print(f"Параллельно: {par_time:.2f} сек")
    print(f"Ускорение: {seq_time / par_time:.2f}x")
    print(f"Замедление: {par_time / seq_time:.2f}x")