import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    API_KEY = os.getenv("WEATHER_API_KEY")
    BASE_URL = "https://api.qweather.com/v7/weather/now"
