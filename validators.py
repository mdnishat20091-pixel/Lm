from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

_KEY_RE = re.compile(r"^[\x21-\x7E]+$")


def validate_base_url(raw: str):
    """Returns (url, error_bn). Exactly one of them is None."""
    value = (raw or "").strip()
    if not value or len(value) > 300 or re.search(r"\s", value):
        return None, "⚠️ ঠিকানা সঠিক নয়।"
    try:
        parts = urlsplit(value)
    except ValueError:
        return None, "⚠️ ঠিকানা সঠিক নয়।"
    if parts.scheme != "https":
        return None, "⚠️ শুধু https ঠিকানা গ্রহণযোগ্য।"
    host = parts.hostname
    if not host or "@" in parts.netloc or parts.query or parts.fragment:
        return None, "⚠️ ঠিকানা সঠিক নয়।"
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            return None, "⚠️ এই ঠিকানা গ্রহণযোগ্য নয়।"
    except ValueError:
        if host.lower() == "localhost" or "." not in host:
            return None, "⚠️ এই ঠিকানা গ্রহণযোগ্য নয়।"
    return value.rstrip("/"), None


def validate_api_key(raw: str):
    value = (raw or "").strip()
    if len(value) < 8 or len(value) > 512 or not _KEY_RE.match(value):
        return None, "⚠️ API Key সঠিক নয়।"
    return value, None
