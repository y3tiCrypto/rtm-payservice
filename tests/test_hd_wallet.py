import pytest
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins
from app.services.hd_wallet import derive_rtm_address

def test_derive_rtm_address_invalid_key():
    with pytest.raises(ValueError):
        derive_rtm_address("invalid-xpub-string", 0)

def test_derive_rtm_address_valid_key():
    # Programmatically generate a structurally valid extended public key
    seed_bytes = Bip39SeedGenerator("abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about").Generate()
    bip_mst = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN)
    valid_xpub = bip_mst.Purpose().Coin().Account(0).PublicKey().ToExtended()
    
    # Derive index 0
    addr_0 = derive_rtm_address(valid_xpub, 0)
    assert isinstance(addr_0, str)
    assert addr_0.startswith("R")
    
    # Derive index 1 (should result in a different address)
    addr_1 = derive_rtm_address(valid_xpub, 1)
    assert isinstance(addr_1, str)
    assert addr_1.startswith("R")
    assert addr_0 != addr_1
