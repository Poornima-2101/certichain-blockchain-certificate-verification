import hashlib
import json
import uuid

def sha256_bytes(data: bytes) -> str:
    """SHA-256 of the exact uploaded bytes, returned as 0x-prefixed hex."""
    if not data:
        raise ValueError("The uploaded file is empty.")
    return "0x" + hashlib.sha256(data).hexdigest()

def new_certificate_id() -> str:
    """Create a random 32-byte identifier; no personal information is encoded."""
    return "0x" + uuid.uuid4().hex + uuid.uuid4().hex

def normalize_bytes32(value: str) -> str:
    value = value.strip()
    if value.startswith("0x"):
        value = value[2:]
    if len(value) != 64:
        raise ValueError("Expected exactly 32 bytes (64 hexadecimal characters).")
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError("Value must be hexadecimal.") from exc
    return "0x" + value.lower()

def validate_upload(filename: str, data: bytes) -> None:
    if not data:
        raise ValueError("The uploaded file is empty.")
    lower = filename.lower()
    if not (lower.endswith(".pdf") or lower.endswith(".json")):
        raise ValueError("Only PDF and JSON files are supported.")
    if lower.endswith(".pdf") and not data.startswith(b"%PDF-"):
        raise ValueError("The file does not appear to be a valid PDF.")
    if lower.endswith(".json"):
        try:
            json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("The uploaded JSON is invalid UTF-8 JSON.") from exc
