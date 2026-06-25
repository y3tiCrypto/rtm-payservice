import logging
from bip_utils import Bip44, Bip44Coins, Bip44Changes, P2PKHAddrEncoder

logger = logging.getLogger(__name__)


def derive_rtm_address(xpub: str, index: int) -> str:
    """
    Derive a mainnet Raptoreum P2PKH address from a standard Account Extended Public Key (xpub).
    RTM mainnet address prefix is 0x3c (60), which results in addresses starting with 'R'.
    """
    try:
        # Load the Account Extended Public Key (xpub)
        # We use Bip44Coins.BITCOIN configuration for key format loading compatibility
        bip_acc = Bip44.FromExtendedKey(xpub, Bip44Coins.BITCOIN)
        
        # Derive external address at the given index (change=0, index=index)
        child = bip_acc.Change(Bip44Changes.CHAIN_EXT).AddressIndex(index)
        
        # Encode the public key object to a P2PKH address using RTM mainnet version byte 0x3c (60)
        address = P2PKHAddrEncoder.EncodeKey(
            child.PublicKey().Bip32Key().KeyObject(),
            net_ver=b"\x3c"
        )
        return address
    except Exception as e:
        logger.error(f"Failed to derive RTM address from xpub at index {index}: {e}")
        raise ValueError(f"Invalid xpub or derivation error: {e}")
