import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime

month_to_season = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn"
}

def analyze_city_data(df_city):
    df_city = df_city.sort_values('timestamp').copy()
    window = 30
    df_city['rolling_mean'] = df_city['temperature'].rolling(window=window, min_periods=1).mean()
    df_city['rolling_std'] = df_city['temperature'].rolling(window=window, min_periods=1).std()
    df_city['is_anomaly'] = np.abs(df_city['temperature'] - df_city['rolling_mean']) > 2 * df_city['rolling_std']
    
    seasonal_stats = df_city.groupby('season')['temperature'].agg(['mean', 'std']).reset_index()
    seasonal_stats.columns = ['season', 'seasonal_mean', 'seasonal_std']
    df_city = df_city.merge(seasonal_stats[['season', 'seasonal_mean', 'seasonal_std']], on='season', how='left')
    return df_city, seasonal_stats

def compute_long_term_trend_and_forecast(df_city, forecast_years=5):
    df_city['year'] = df_city['timestamp'].dt.year
    yearly_avg = df_city.groupby('year')['temperature'].mean().reset_index()
    x_hist = yearly_avg['year'].values
    y_hist = yearly_avg['temperature'].values
    coeffs = np.polyfit(x_hist, y_hist, deg=1)
    trend_hist = np.polyval(coeffs, x_hist)
    yearly_avg['trend'] = trend_hist
    
    last_year = x_hist.max()
    future_years = np.arange(last_year + 1, last_year + 1 + forecast_years)
    future_trend = np.polyval(coeffs, future_years)
    
    all_years = np.concatenate([x_hist, future_years])
    all_trend = np.concatenate([trend_hist, future_trend])
    is_future = np.concatenate([np.full_like(x_hist, False, dtype=bool), np.full_like(future_years, True, dtype=bool)])
    
    trend_df = pd.DataFrame({
        'year': all_years,
        'trend': all_trend,
        'is_future': is_future
    })
    slope = coeffs[0]
    return yearly_avg, trend_df, slope

def get_current_weather(city, api_key):
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {'q': city, 'appid': api_key, 'units': 'metric'}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if response.status_code == 401:
            return {"error": "Invalid API key", "code": 401}
        elif response.status_code != 200:
            return {"error": data.get("message", "Unknown error"), "code": response.status_code}
        return {
            "city": city,
            "current_temp": data['main']['temp'],
            "season": month_to_season[datetime.now().month]
        }
    except Exception as e:
        return {"error": str(e), "code": None}

st.set_page_config(page_title="Мониторинг климатических аномалий", layout="wide")
st.title("Мониторинг климатических аномалий")

uploaded_file = st.file_uploader("Загрузите файл с историческими данными", type="csv")
if not uploaded_file:
    st.info("Пожалуйста, загрузите CSV-файл (например, temperature_data.csv)")
    st.stop()

df = pd.read_csv(uploaded_file, parse_dates=['timestamp'])
cities = sorted(df['city'].unique())

col1, col2 = st.columns([2, 1])
with col1:
    selected_city = st.selectbox("Выберите город", cities)
with col2:
    api_key = st.text_input("OpenWeatherMap API Key", type="password")

forecast_years = st.slider("Прогноз тренда на N лет вперёд", min_value=1, max_value=20, value=5)

city_df = df[df['city'] == selected_city].copy()
city_df, seasonal_stats = analyze_city_data(city_df)

st.subheader(f"Исторические данные: {selected_city}")
fig = go.Figure()
fig.add_trace(go.Scatter(x=city_df['timestamp'], y=city_df['temperature'], mode='lines', name='Температура'))
anomalies = city_df[city_df['is_anomaly']]
fig.add_trace(go.Scatter(x=anomalies['timestamp'], y=anomalies['temperature'], mode='markers', name='Аномалии', marker=dict(color='red', size=5)))
fig.add_trace(go.Scatter(x=city_df['timestamp'], y=city_df['rolling_mean'], mode='lines', name='Скользящее среднее (30 дней)', line=dict(color='orange')))
fig.update_layout(xaxis_title="Дата", yaxis_title="Температура (°C)")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Долгосрочный тренд и прогноз")
yearly_data, trend_full, slope = compute_long_term_trend_and_forecast(city_df, forecast_years=forecast_years)

fig_trend = go.Figure()
fig_trend.add_trace(go.Scatter(
    x=yearly_data['year'], y=yearly_data['temperature'],
    mode='markers', name='Среднегодовая температура'
))
hist_trend = trend_full[~trend_full['is_future']]
fig_trend.add_trace(go.Scatter(
    x=hist_trend['year'], y=hist_trend['trend'],
    mode='lines', name='Исторический тренд', line=dict(color='red')
))
future_trend = trend_full[trend_full['is_future']]
if not future_trend.empty:
    fig_trend.add_trace(go.Scatter(
        x=future_trend['year'], y=future_trend['trend'],
        mode='lines', name='Прогноз тренда', line=dict(color='red', dash='dot')
    ))
fig_trend.update_layout(
    xaxis_title="Год",
    yaxis_title="Средняя температура (°C)",
    title=f"Наклон тренда: {slope:+.3f} °C/год"
)
st.plotly_chart(fig_trend, use_container_width=True)

if slope > 0.01:
    st.success(f"Температура в {selected_city} стабильно растёт: **+{slope:.3f} °C в год**")
elif slope < -0.01:
    st.warning(f"Температура снижается: **{slope:.3f} °C в год**")
else:
    st.info(f"↔️ Нет значимого тренда: изменение {slope:+.3f} °C/год")
st.caption("⚠️ Прогноз основан на линейной экстраполяции исторического тренда. Это не метеорологический прогноз.")

st.subheader("Тепловая карта: Средняя температура по городам и сезонам")
all_cities_seasonal = []
for city in cities:
    city_data = df[df['city'] == city]
    stats = city_data.groupby('season')['temperature'].mean().reindex(['winter', 'spring', 'summer', 'autumn'])
    all_cities_seasonal.append(stats.values)

heatmap_data = np.array(all_cities_seasonal)
season_labels = ['Зима', 'Весна', 'Лето', 'Осень']

fig_heatmap = px.imshow(
    heatmap_data,
    labels=dict(x="Сезон", y="Город", color="Температура (°C)"),
    x=season_labels,
    y=cities,
    color_continuous_scale="RdYlBu_r",
    aspect="auto"
)
fig_heatmap.update_layout(title="Средняя температура по сезонам")
st.plotly_chart(fig_heatmap, use_container_width=True)

st.subheader("Сезонные нормы (среднее ± 2σ)")
season_order = ['winter', 'spring', 'summer', 'autumn']
seasonal_stats = seasonal_stats.set_index('season').reindex(season_order)
fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=seasonal_stats.index,
    y=seasonal_stats['seasonal_mean'],
    error_y=dict(type='data', array=2 * seasonal_stats['seasonal_std']),
    name='Средняя температура'
))
fig2.update_layout(yaxis_title="Температура (°C)")
st.plotly_chart(fig2, use_container_width=True)

if api_key:
    st.subheader("Текущая погода")
    weather = get_current_weather(selected_city, api_key)
    if "error" in weather:
        if weather["code"] == 401:
            st.error("Неверный API-ключ. Проверьте ключ или подождите 2 часа после регистрации.")
        else:
            st.warning(f"Ошибка: {weather['error']}")
    else:
        current_temp = weather['current_temp']
        current_season = weather['season']
        norm = seasonal_stats.loc[current_season]
        lower = norm['seasonal_mean'] - 2 * norm['seasonal_std']
        upper = norm['seasonal_mean'] + 2 * norm['seasonal_std']
        
        st.metric("Текущая температура", f"{current_temp:.1f}°C")
        st.write(f"Сезон: **{current_season}**")
        if lower <= current_temp <= upper:
            st.success("Температура в пределах нормы")
        else:
            st.error("Аномальная температура!")
            st.write(f"Нормальный диапазон: [{lower:.1f}, {upper:.1f}]°C")
else:
    st.info("Введите API-ключ OpenWeatherMap, чтобы отобразить текущую погоду.")