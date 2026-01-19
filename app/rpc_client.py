from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from app.config import settings


class RaptoreumRPC:
    def __init__(self):
        rpc_connection_string = (
            f"http://{settings.rpc_user}:{settings.rpc_password}@"
            f"{settings.rpc_host}:{settings.rpc_port}"
        )
        self.rpc = AuthServiceProxy(rpc_connection_string, timeout=10)

    def get_new_address(self, label="raptoreumpay_invoice"):
        try:
            return self.rpc.getnewaddress(label)
        except JSONRPCException as e:
            raise Exception(f"RPC error getting new address: {e}")

    def get_received_by_address(self, address: str, minconf: int = 0):
        try:
            return float(self.rpc.getreceivedbyaddress(address, minconf))
        except JSONRPCException as e:
            raise Exception(f"RPC error getting received amount: {e}")

    def get_transaction(self, txid: str):
        try:
            return self.rpc.gettransaction(txid)
        except JSONRPCException:
            return None


# Singleton instance
rpc = RaptoreumRPC()