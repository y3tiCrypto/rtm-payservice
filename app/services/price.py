import requests
import threading
from datetime import datetime
from app.redis_client import redis_client

COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price?ids=raptoreum&vs_currencies=usd"
CACHE_TTL_SECONDS = 300

# Cache storage and thread lock (local fallback)
_price_lock = threading.Lock()
_cached_price: float | None = None
_cached_time: datetime | None = None


def get_rtm_price_usd() -> float:
    """
    Fetch current RTM price in USD from CoinGecko.
    Uses Redis cache if available, falling back to in-memory thread-safe cache.
    """
    global _cached_price, _cached_time
    
    # 1. Try Redis cache if enabled
    if redis_client is not None:
        try:
            cached = redis_client.get("raptoreumpay:rtm_price")
            if cached is not None:
                return float(cached)
        except Exception as e:
            print(f"Redis cache read error: {e}")

    now = datetime.utcnow()
    
    # 2. Local Fallback Cache check
    if redis_client is None:
        with _price_lock:
            if _cached_price is not None and _cached_time is not None:
                if (now - _cached_time).total_seconds() < CACHE_TTL_SECONDS:
                    return _cached_price

    # 3. Fetch from API
    try:
        response = requests.get(COINGECKO_API, timeout=5)
        response.raise_for_status()
        data = response.json()
        fresh_price = float(data.get("raptoreum", {}).get("usd", 0.0))
        
        if fresh_price > 0:
            # Save to Redis if available
            if redis_client is not None:
                try:
                    redis_client.set("raptoreumpay:rtm_price", str(fresh_price), ex=CACHE_TTL_SECONDS)
                except Exception as e:
                    print(f"Redis cache write error: {e}")
            else:
                with _price_lock:
                    _cached_price = fresh_price
                    _cached_time = now
            return fresh_price
    except Exception as e:
        print(f"Price fetch error: {e}")

    # 4. Fallback on stale local or Redis value
    if redis_client is not None:
        # If Redis write failed, we fallback to the local thread-safe value if present
        if _cached_price is not None:
            return _cached_price
    else:
        with _price_lock:
            if _cached_price is not None:
                print(f"Warning: CoinGecko API unreachable. Serving stale price: {_cached_price}")
                return _cached_price
                
    return 0.0