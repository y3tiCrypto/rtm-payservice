import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_rpc(mocker):
    mock = mocker.patch("app.rpc_client.rpc")
    mock.get_new_address.return_value = "RDb9g8sW7aHJK90123"
    mock.get_received_by_address.return_value = 0.0
    mock.validate_address.return_value = True
    mock.get_balance.return_value = 10000.0
    mock.sweep_wallet.return_value = "mocked_sweep_txid_123"
    return mock
