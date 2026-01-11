import requests
import aiohttp
import asyncio
import time

key = "YOUR_KEY"
def get_weather_sync(city, api_key):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}
    response = requests.get(url, timeout=10)
    return response.json()

async def get_weather_async(city, api_key):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=10) as resp:
            return await resp.json()
        
def fetch_weather(city, api_key):
    return asyncio.run(get_weather_async(city, api_key))

start = time.time()
data = get_weather_sync("Moscow", key)
print("Sync:", time.time() - start)

start = time.time()
data = fetch_weather("Moscow", key)
print("Async:", time.time() - start)