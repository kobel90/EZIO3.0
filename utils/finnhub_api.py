# utils/finnhub_api.py
import requests

class FinnhubAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"

    def get_price(self, symbol: str) -> float:
        try:
            url = f"{self.base_url}/quote"
            response = requests.get(url, params={"symbol": symbol, "token": self.api_key})
            data = response.json()
            return float(data.get("c", 0.0))  # "c" = current price
        except Exception as e:
            print(f"❌ Fehler bei Preisabfrage ({symbol}): {e}")
            return 0.0