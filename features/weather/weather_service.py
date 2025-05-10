from features.weather.api_client import APIClient


class WeatherService:
    """Provides high-level weather service methods."""

    def __init__(self):
        self.client = APIClient()

    def get_weather_info(self, longitude, latitude):
        """Fetches and processes weather data."""
        try:
            data = self.client.get(longitude, latitude)

            # Check if API response is valid
            if "code" in data and data["code"] != "200":
                return {"error": f"API returned error code: {data['code']}"}

            now = data.get("now", {})

            return {
                "location": f"{latitude},{longitude}",
                "updated_at": data.get("updateTime", "N/A"),
                "weather_condition": now.get("text", "Unknown"),
                "temperature": f"{now.get('temp', 'N/A')}°C",
                "feels_like": f"{now.get('feelsLike', 'N/A')}°C",
                "humidity": f"{now.get('humidity', 'N/A')}%",
                "wind_direction": now.get("windDir", "N/A"),
                "wind_speed": f"{now.get('windSpeed', 'N/A')} m/s",
                "pressure": f"{now.get('pressure', 'N/A')} hPa",
                "visibility": f"{now.get('vis', 'N/A')} km",
                "cloud_coverage": f"{now.get('cloud', 'N/A')}%",
                "reference": data.get("fxLink", "N/A"),  # Weather forecast link
                "source": ", ".join(data.get("refer", {}).get("sources", []))
            }

        except Exception as e:
            return {"error": str(e)}


# if __name__ == "__main__":
#
#     weather = WeatherService()
#     print(weather.get_weather_info(121.4581, 31.2222))



