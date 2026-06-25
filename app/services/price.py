import requests
import threading
from datetime import datetime, timezone
from app.redis_client import redis_client

CACHE_TTL_SECONDS = 300

# Cache storage and thread lock (local fallbacks per currency)
_price_lock = threading.Lock()
_cached_prices: dict[str, float] = {}
_cached_times: dict[str, datetime] = {}


def get_rtm_price(fiat_currency: str = "USD") -> float:
    """
    Fetch current RTM price in target fiat currency from CoinGecko.
    Uses Redis cache if available, falling back to in-memory thread-safe cache.
    """
    global _cached_prices, _cached_times
    
    currency_key = fiat_currency.upper()
    redis_key = f"raptoreumpay:rtm_price:{currency_key}"
    
    # 1. Try Redis cache if enabled
    if redis_client is not None:
        try:
            cached = redis_client.get(redis_key)
            if cached is not None:
                return float(cached)
        except Exception as e:
            print(f"Redis cache read error: {e}")

    now = datetime.now(timezone.utc)
    
    # 2. Local Fallback Cache check (fallback if Redis is disabled or failed/missed)
    with _price_lock:
        cached_price = _cached_prices.get(currency_key)
        cached_time = _cached_times.get(currency_key)
        if cached_price is not None and cached_time is not None:
            if (now - cached_time).total_seconds() < CACHE_TTL_SECONDS:
                return cached_price

    # 3. Fetch from API (CoinGecko)
    fresh_price = 0.0
    try:
        coingecko_url = f"https://api.coingecko.com/api/v3/simple/price?ids=raptoreum&vs_currencies={currency_key.lower()}"
        response = requests.get(coingecko_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        fresh_price = float(data.get("raptoreum", {}).get(currency_key.lower(), 0.0))
    except Exception as e:
        print(f"Primary price fetch (CoinGecko) failed for {currency_key}: {e}.")
        
        # If USD or USDT, try CoinEx ticker fallback
        if currency_key in ("USD", "USDT"):
            print("Trying fallback oracle (CoinEx)...")
            try:
                coinex_url = "https://api.coinex.com/v1/market/ticker?market=RTMUSDT"
                response = requests.get(coinex_url, timeout=5)
                response.raise_for_status()
                data = response.json()
                fresh_price = float(data.get("data", {}).get("ticker", {}).get("last", 0.0))
                print(f"Fallback price fetch (CoinEx) succeeded: {fresh_price}")
            except Exception as ex:
                print(f"Fallback price fetch (CoinEx) failed: {ex}")
                fresh_price = 0.0
            
    if fresh_price > 0:
        # Always write to local memory cache as a fallback/resilience mechanism
        with _price_lock:
            _cached_prices[currency_key] = fresh_price
            _cached_times[currency_key] = now
            
        # Save to Redis if available
        if redis_client is not None:
            try:
                redis_client.set(redis_key, str(fresh_price), ex=CACHE_TTL_SECONDS)
            except Exception as e:
                print(f"Redis cache write error: {e}")
        return fresh_price

    # 4. Fallback on stale local value
    with _price_lock:
        stale_price = _cached_prices.get(currency_key)
        if stale_price is not None:
            print(f"Warning: Price APIs unreachable. Serving stale price for {currency_key}: {stale_price}")
            return stale_price
                
    return 0.0