import requests
from .config import Config
from .exception import APILimitExceededError, InvalidResponseError


class APIClient:
    """"Handles API requests for weather data."""

    def __init__(self, base_url=Config.BASE_URL, api_key=Config.API_KEY):
        self.base_url = base_url
        self.api_key = api_key

    def get(self, latitude, longitude):
        """Fetch weather data for a given location."""
        params = {
            "location": f"{latitude},{longitude}",
            "key": self.api_key,
        }
        response = requests.get(self.base_url, params=params)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            raise APILimitExceededError("API rate limit exceeded. Try again later.")
        else:
            raise InvalidResponseError(f"Invalid response from API: {response.text}")
