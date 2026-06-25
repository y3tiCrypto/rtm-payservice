import urllib.request
import urllib.error
import json
import hmac
import hashlib
import time

class RaptoreumPayClient:
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, data: dict) -> dict:
        url = f"{self.base_url}{path}?api_key={self.api_key}"
        req_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_data = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_data)
                detail = err_json.get("detail", err_data)
            except Exception:
                detail = err_data
            raise Exception(f"RaptoreumPay API Error ({e.code}): {detail}")

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_data = e.read().decode("utf-8")
            raise Exception(f"RaptoreumPay API Error ({e.code}): {err_data}")

    def create_invoice(self, amount_rtm: float = None, amount_fiat: float = None, fiat_currency: str = None, order_id: str = None, webhook_url: str = None) -> dict:
        payload = {}
        if amount_rtm is not None:
            payload["amount_rtm"] = amount_rtm
        if amount_fiat is not None:
            payload["amount_fiat"] = amount_fiat
        if fiat_currency is not None:
            payload["fiat_currency"] = fiat_currency
        if order_id is not None:
            payload["order_id"] = order_id
        if webhook_url is not None:
            payload["webhook_url"] = webhook_url
            
        return self._post("/api/payment/create", payload)

    def get_invoice_status(self, invoice_id: str) -> dict:
        return self._get(f"/api/payment/{invoice_id}/status")

    @staticmethod
    def verify_webhook_signature(payload_bytes: bytes, signature: str, timestamp: str, api_key: str, max_age_seconds: int = 300) -> bool:
        # Check signature age to prevent replay attacks
        try:
            if abs(int(time.time()) - int(timestamp)) > max_age_seconds:
                return False
        except (ValueError, TypeError):
            return False

        # Compute signature
        signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
        computed = hmac.new(
            api_key.encode("utf-8"),
            signed_payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed, signature)
