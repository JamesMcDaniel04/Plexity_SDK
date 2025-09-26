from __future__ import annotations

import hmac
import json
import time
from hashlib import sha256
from typing import Any, Dict, Union

DEFAULT_TOLERANCE_SECONDS = 300


def compute_webhook_signature(*, secret: str, payload: Union[str, bytes], timestamp: str) -> str:
    """Create a SHA-256 HMAC signature for a webhook payload."""
    if isinstance(payload, bytes):
        data = payload.decode("utf-8")
    else:
        data = payload
    message = f"{timestamp}.{data}"
    digest = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), sha256)
    return digest.hexdigest()


def verify_webhook_signature(
    *,
    secret: str,
    payload: Union[str, bytes, Dict[str, Any]],
    timestamp: str,
    signature: str,
    tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS,
) -> bool:
    """Validate a webhook signature emitted by the SprintIQ orchestrator."""
    if not secret or not signature or not timestamp:
        return False
    try:
        ts = float(timestamp)
    except (TypeError, ValueError):
        return False
    if tolerance_seconds > 0:
        if abs(time.time() - ts) > tolerance_seconds:
            return False
    if isinstance(payload, dict):
        payload_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    elif isinstance(payload, bytes):
        payload_str = payload.decode("utf-8")
    else:
        payload_str = str(payload)
    expected = compute_webhook_signature(secret=secret, payload=payload_str, timestamp=str(timestamp))
    if len(expected) != len(signature):
        return False
    return hmac.compare_digest(expected, signature)


def extract_webhook_request(headers: Dict[str, Any], body: Any, raw_body: Union[str, bytes, None] = None) -> Dict[str, Any]:
    """Utility to pull signature metadata from a webhook request."""
    signature = headers.get("x-sprintiq-signature")
    timestamp = headers.get("x-sprintiq-timestamp")
    payload = raw_body if raw_body is not None else body
    return {
        "signature": signature,
        "timestamp": timestamp,
        "payload": payload,
    }
