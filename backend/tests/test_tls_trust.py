import pytest
import os
import certifi
import hashlib
import base64
from app.core.tls_trust import get_qatar_mof_ca_bundle, _CACHED_BUNDLE_PATH, EXPECTED_FINGERPRINT
import app.core.tls_trust as tls_trust_module

def test_get_qatar_mof_ca_bundle():
    # Force reset
    tls_trust_module._CACHED_BUNDLE_PATH = None
    
    bundle_path = get_qatar_mof_ca_bundle()
    
    assert bundle_path is not None
    assert bundle_path != certifi.where(), "Bundle path should be a custom temp file"
    assert os.path.exists(bundle_path), "Combined bundle file must exist"
    
    with open(bundle_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Verify the bundle contains the standard roots
    with open(certifi.where(), "r", encoding="utf-8") as f:
        certifi_content = f.read()
        assert certifi_content in content, "Original certifi roots must be present"
        
    # Verify the bundle contains the pinned intermediate
    pinned_path = os.path.join(
        os.path.dirname(__file__), "..", "certs", "digicert_global_g2_tls_rsa_sha256_2020_ca1.pem"
    )
    with open(pinned_path, "r", encoding="utf-8") as f:
        pinned_content = f.read()
        assert pinned_content in content, "Pinned intermediate must be present"
        
    # Verify caching
    bundle_path_2 = get_qatar_mof_ca_bundle()
    assert bundle_path == bundle_path_2, "Must return the cached path on subsequent calls"
    
    # Cleanup
    if os.path.exists(bundle_path):
        os.remove(bundle_path)

def test_fingerprint_validation(monkeypatch):
    # Load the real pinned cert
    pinned_path = os.path.join(
        os.path.dirname(__file__), "..", "certs", "digicert_global_g2_tls_rsa_sha256_2020_ca1.pem"
    )
    with open(pinned_path, "rb") as f:
        real_pem = f.read()
        
    # Test valid
    assert tls_trust_module._validate_fingerprint(real_pem) is True
    
    # Test invalid fails
    bad_pem = real_pem.replace(b"M", b"N", 1)  # slightly mangle it
    assert tls_trust_module._validate_fingerprint(bad_pem) is False
    
    # Test that get_qatar_mof_ca_bundle raises ValueError on bad cert
    tls_trust_module._CACHED_BUNDLE_PATH = None
    
    # Mock read so we return bad_pem when reading the pinned cert
    original_open = builtins_open = open
    def mock_open(file, *args, **kwargs):
        if "digicert" in str(file):
            import io
            return io.BytesIO(bad_pem)
        return builtins_open(file, *args, **kwargs)
        
    monkeypatch.setattr("builtins.open", mock_open)
    
    with pytest.raises(ValueError, match="Invalid certificate fingerprint"):
        get_qatar_mof_ca_bundle()
