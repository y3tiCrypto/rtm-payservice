import requests
from fastapi import HTTPException

COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price?ids=raptoreum&vs_currencies=usd"

def get_rtm_price_usd() -> float:
    """
    Fetch current RTM price in USD from CoinGecko
    Returns 0.0 if request fails (fail-safe for MVP)
    """
    try:
        response = requests.get(COINGECKO_API, timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data.get("raptoreum", {}).get("usd", 0.0))
    except Exception as e:
        print(f"Price fetch error: {e}")
        return 0.0  # Don't break invoice creation if price fails