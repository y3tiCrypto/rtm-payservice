import requests
import threading
from datetime import datetime

COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price?ids=raptoreum&vs_currencies=usd"
CACHE_TTL_SECONDS = 300

# Cache storage and thread lock
_price_lock = threading.Lock()
_cached_price: float | None = None
_cached_time: datetime | None = None

def get_rtm_price_usd() -> float:
    """
    Fetch current RTM price in USD from CoinGecko.
    Uses a thread-safe local cache with a 5-minute TTL.
    If the API call fails and a cached price exists (even if stale), returns the cached price.
    """
    global _cached_price, _cached_time
    
    now = datetime.utcnow()
    
    with _price_lock:
        # 1. Return valid cache if it's within TTL
        if _cached_price is not None and _cached_time is not None:
            if (now - _cached_time).total_seconds() < CACHE_TTL_SECONDS:
                return _cached_price
                
        # 2. Try fetching a fresh price
        try:
            response = requests.get(COINGECKO_API, timeout=5)
            response.raise_for_status()
            data = response.json()
            fresh_price = float(data.get("raptoreum", {}).get("usd", 0.0))
            
            if fresh_price > 0:
                _cached_price = fresh_price
                _cached_time = now
                return fresh_price
        except Exception as e:
            print(f"Price fetch error: {e}")
            
        # 3. Fallback: if fetch failed but we have a stale cache, return it
        if _cached_price is not None:
            print(f"Warning: CoinGecko API unreachable or rate-limited. Serving stale cached price: {_cached_price}")
            return _cached_price
            
        return 0.0