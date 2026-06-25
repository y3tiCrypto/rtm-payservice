import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta
from app.services import price
from app.services.price import get_rtm_price

def test_get_rtm_price_cached(mocker):
    # Setup cache for USD
    price._cached_prices["USD"] = 0.0015
    price._cached_times["USD"] = datetime.now(timezone.utc)
    
    # Mock requests.get to verify it's NOT called (no API call)
    mock_get = mocker.patch("requests.get")
    
    val = get_rtm_price("USD")
    assert val == 0.0015
    mock_get.assert_not_called()

def test_get_rtm_price_coingecko_success(mocker):
    # Clear cache
    price._cached_prices.clear()
    price._cached_times.clear()
    
    # Mock CoinGecko response for EUR
    mock_response = MagicMock()
    mock_response.json.return_value = {"raptoreum": {"eur": 0.0022}}
    mock_response.raise_for_status = MagicMock()
    
    mocker.patch("requests.get", return_value=mock_response)
    
    val = get_rtm_price("EUR")
    assert val == 0.0022
    assert price._cached_prices["EUR"] == 0.0022

def test_get_rtm_price_coingecko_fail_coinex_success(mocker):
    # Clear cache
    price._cached_prices.clear()
    price._cached_times.clear()
    
    # Mock CoinGecko failure and CoinEx success for USD
    mock_coingecko_fail = Exception("CoinGecko API down")
    
    mock_coinex_success = MagicMock()
    mock_coinex_success.json.return_value = {"data": {"ticker": {"last": "0.0035"}}}
    mock_coinex_success.raise_for_status = MagicMock()
    
    mocker.patch("requests.get", side_effect=[mock_coingecko_fail, mock_coinex_success])
    
    val = get_rtm_price("USD")
    assert val == 0.0035
    assert price._cached_prices["USD"] == 0.0035

def test_get_rtm_price_stale_fallback(mocker):
    # Clear cache and insert a stale fallback
    price._cached_prices["USD"] = 0.0018
    price._cached_times["USD"] = datetime.now(timezone.utc) - timedelta(seconds=600)
    
    # Mock both APIs failing
    mocker.patch("requests.get", side_effect=Exception("Network Offline"))
    
    val = get_rtm_price("USD")
    assert val == 0.0018  # Should return stale fallback
