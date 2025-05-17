from geopy.geocoders import Nominatim
import requests
from datetime import datetime

WEATHER_DESCRIPTION = f"""
Retrieves the weather using Open-Meteo API for a given location (city) and a date (yyyy-mm-dd) format. 
Note that the current date is {datetime.now().strftime('%Y-%m-%d')}.
Returns a dictionary with time, temperature, humidity, precipitation, and windspeed for each hour.
"""
def get_weather(location: str, date: str):
    geolocator = Nominatim(user_agent="weather-app") 
    location = geolocator.geocode(location)
    print(date)
    if location:
        try:
            response = requests.get(
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={location.latitude}&longitude={location.longitude}"
                f"&hourly=temperature_2m,relativehumidity_2m,precipitation,windspeed_10m,weathercode"
                f"&start_date={date}&end_date={date}"
            )
            data = response.json()
            hourly_data = data["hourly"]
            return {
                "time": hourly_data["time"],
                "temperature": hourly_data["temperature_2m"],
                "humidity": hourly_data["relativehumidity_2m"],
                "precipitation": hourly_data["precipitation"],
                "windspeed": hourly_data["windspeed_10m"],
                "weathercode": hourly_data["weathercode"]
            }
        except Exception as e:
            return {"error": str(e)}
    else:
        return {"error": "Location not found"}

# get_weather_tool = create_function_tool(
#             get_weather,
#             name="get_weather",
#             description=WEATHER_DESCRIPTION
#         )