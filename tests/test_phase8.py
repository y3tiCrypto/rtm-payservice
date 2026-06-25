import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sdk.raptoreumpay import RaptoreumPayClient
from app.models import Merchant
from app.main import app

def test_merchant_split_sweep_fields():
    m = Merchant(
        email="split@example.com",
        sweep_cold_address="cold_addr_123",
        sweep_split_ratio=0.75
    )
    assert m.sweep_cold_address == "cold_addr_123"
    assert m.sweep_split_ratio == 0.75

def test_merchant_analytics(mocker):
    # Mock Database Session
    mock_db = MagicMock()
    
    # Mock Merchant
    mock_merchant = Merchant(
        id=1,
        email="test@example.com",
        api_key="testkey",
        sweep_cold_address="cold_addr",
        sweep_split_ratio=0.7
    )
    
    # Mock database queries for merchant and invoices
    mock_db.query.return_value.filter.return_value.first.return_value = mock_merchant
    mock_db.query.return_value.filter.return_value.all.return_value = []  # Empty invoices for simplicity
    
    def override_get_db():
        yield mock_db
        
    from app.database import get_db
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    response = client.get("/api/merchant/analytics?api_key=testkey")
    
    assert response.status_code == 200
    json_data = response.json()
    assert "labels" in json_data
    assert "volume_rtm" in json_data
    assert "volume_fiat" in json_data
    assert "paid_count" in json_data
    assert "expired_count" in json_data
    assert len(json_data["labels"]) == 31
    
    app.dependency_overrides.clear()

def test_sdk_webhook_signature():
    api_key = "testkey"
    payload = b'{"event":"payment.confirmed"}'
    import time
    timestamp = str(int(time.time()))
    
    import hmac
    import hashlib
    # Create valid signature
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    valid_sig = hmac.new(api_key.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    
    # Test verification success
    res = RaptoreumPayClient.verify_webhook_signature(payload, valid_sig, timestamp, api_key)
    assert res is True
    
    # Test verification failure on signature
    res = RaptoreumPayClient.verify_webhook_signature(payload, "wrongsignature", timestamp, api_key)
    assert res is False
    
    # Test verification failure on timestamp age
    old_timestamp = str(int(time.time()) - 400)
    res = RaptoreumPayClient.verify_webhook_signature(payload, valid_sig, old_timestamp, api_key)
    assert res is False

def test_sdk_client_requests(mocker):
    client = RaptoreumPayClient(api_key="testkey", base_url="http://mockedurl")
    
    # Mock urllib.request.urlopen
    mock_urlopen = mocker.patch("urllib.request.urlopen")
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"invoice_id": "123", "status": "pending"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    res = client.create_invoice(amount_rtm=10.0, order_id="order1")
    assert res["invoice_id"] == "123"
    
    # Verify urlopen was called with a request containing standard params
    args, kwargs = mock_urlopen.call_args
    req = args[0]
    assert req.full_url == "http://mockedurl/api/payment/create?api_key=testkey"
    assert req.headers["Content-type"] == "application/json"
    
    # Test get_invoice_status
    mock_response.read.return_value = b'{"status": "paid"}'
    res = client.get_invoice_status("invoice_123")
    assert res["status"] == "paid"
