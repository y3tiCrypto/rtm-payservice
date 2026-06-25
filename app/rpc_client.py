import time
import logging
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from app.config import settings

logger = logging.getLogger(__name__)

class RaptoreumRPC:
    def __init__(self):
        rpc_connection_string = (
            f"http://{settings.rpc_user}:{settings.rpc_password}@"
            f"{settings.rpc_host}:{settings.rpc_port}"
        )
        self.rpc = AuthServiceProxy(rpc_connection_string, timeout=10)

    def _call_with_retry(self, func_name: str, *args, **kwargs):
        """
        Execute an RPC command with up to 3 retry attempts and incremental delay backoff.
        Helps protect against transient network outages and core daemon restarts.
        """
        max_attempts = 3
        delay = 1.0
        for attempt in range(1, max_attempts + 1):
            try:
                rpc_method = getattr(self.rpc, func_name)
                return rpc_method(*args, **kwargs)
            except (JSONRPCException, Exception) as e:
                logger.warning(
                    f"Raptoreum Core RPC '{func_name}' failed on attempt {attempt}/{max_attempts}: {e}"
                )
                if attempt == max_attempts:
                    raise e
                time.sleep(delay * attempt)

    def get_new_address(self, label="raptoreumpay_invoice"):
        try:
            return self._call_with_retry("getnewaddress", label)
        except Exception as e:
            raise Exception(f"RPC error getting new address: {e}")

    def get_received_by_address(self, address: str, minconf: int = 0):
        try:
            return float(self._call_with_retry("getreceivedbyaddress", address, minconf))
        except Exception as e:
            raise Exception(f"RPC error getting received amount: {e}")

    def get_transaction(self, txid: str):
        try:
            return self._call_with_retry("gettransaction", txid)
        except Exception:
            return None


# Singleton instance
rpc = RaptoreumRPC()