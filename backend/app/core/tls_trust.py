import os
import certifi
import tempfile
import hashlib

_CACHED_BUNDLE_PATH = None

# SHA-256 fingerprint of the expected intermediate certificate (DER encoded)
# Wait, this is the fingerprint of the DER, but we saved it as PEM. 
# We should compute the hash of the DER data, or the PEM data, or we can just parse it if we use cryptography.
# Since we saved the PEM, we can hash the PEM data as-is (with normalized line endings) or just hash the bytes.
# Wait, the requirement says:
# "Add/confirm a test that validates the pinned intermediate SHA-256 fingerprint:
# c8025f9fc65fdfc95b3ca8cc7867b9a587b5277973957917463fc813d0b625a9"
# This is the fingerprint of the DER certificate itself (which is typical for x509).
# To do this safely without adding cryptography as a runtime dependency just for hashing, 
# we can strip the PEM headers and base64 decode it to get the DER bytes, then hash it.

EXPECTED_FINGERPRINT = "c8025f9fc65fdfc95b3ca8cc7867b9a587b5277973957917463fc813d0b625a9"

def _validate_fingerprint(pem_data: bytes) -> bool:
    import base64
    lines = pem_data.decode("ascii").splitlines()
    b64_data = "".join([line for line in lines if not line.startswith("-----")])
    der_data = base64.b64decode(b64_data)
    fingerprint = hashlib.sha256(der_data).hexdigest()
    return fingerprint == EXPECTED_FINGERPRINT

def get_qatar_mof_ca_bundle() -> str:
    """
    Returns the path to a combined CA bundle containing both standard certifi roots
    and the pinned DigiCert intermediate required for Qatar MOF's misconfigured TLS.
    This safely allows verify=True without disabling TLS validation.
    
    The combined bundle is created once per process and cached in a temporary file.
    """
    global _CACHED_BUNDLE_PATH
    
    if _CACHED_BUNDLE_PATH and os.path.exists(_CACHED_BUNDLE_PATH):
        return _CACHED_BUNDLE_PATH
        
    # Get standard certifi bundle path
    certifi_path = certifi.where()
    
    # Get pinned intermediate path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pinned_cert_path = os.path.join(
        current_dir, 
        "..", 
        "..", 
        "certs", 
        "digicert_global_g2_tls_rsa_sha256_2020_ca1.pem"
    )
    
    if not os.path.exists(pinned_cert_path):
        return certifi_path
        
    with open(certifi_path, "rb") as f:
        certifi_data = f.read()
        
    with open(pinned_cert_path, "rb") as f:
        pinned_data = f.read()
        
    # Integrity check
    if not _validate_fingerprint(pinned_data):
        raise ValueError("Invalid certificate fingerprint for Qatar MOF pinned intermediate!")
        
    # Create temporary file (not automatically deleted, but OS cleans temp files)
    fd, temp_path = tempfile.mkstemp(prefix="gulfscopeiq_ca_bundle_", suffix=".pem")
    with os.fdopen(fd, "wb") as f:
        f.write(certifi_data)
        f.write(b"\n")
        f.write(pinned_data)
        f.write(b"\n")
        
    _CACHED_BUNDLE_PATH = temp_path
    return temp_path
