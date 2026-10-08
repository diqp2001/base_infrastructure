"""
Secret redaction for everything the dashboard returns or logs.

Removes passwords / tokens / keys written as ``key=value`` or ``"key": "value"``, ODBC
``PWD={...}`` (also URL-encoded), and the literal values of sensitive environment variables
and Docker secret files.
"""

import os
import re
from functools import lru_cache
from typing import Any, Iterable, List

MASK = "***"
_SENSITIVE_NAME = re.compile(r"(PASSWORD|PASSWD|PWD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|CREDENTIAL)", re.I)
_KEYS = r"(?:pwd|password|passwd|secret|token|api[_-]?key|apikey)"
_PATTERNS = [
    # ODBC / connection strings: PWD={...}
    (re.compile(r"(?i)\b(pwd|password)(\s*=\s*)\{(?:[^}]|\}\})*\}"), rf"\1\2{MASK}"),
    # key=value (connection strings, query strings, CLI flags)
    (re.compile(rf"(?i)\b({_KEYS})(\s*=\s*)[^;&\s'\",}}]+"), rf"\1\2{MASK}"),
    # URL-encoded odbc_connect: ...%3BPWD%3D%7B...%7D or PWD%3D... (separator may be %3B)
    (re.compile(r"(?i)(^|%3b|[;&?=\s])(pwd|password)(%3d)(?:%7b.*?%7d|[^%&\s]+)"), rf"\1\2\3{MASK}"),
    # JSON / dict style: "password": "..."
    (re.compile(rf"(?i)([\"']?{_KEYS}[\"']?\s*:\s*)[\"'][^\"']*[\"']"), rf'\1"{MASK}"'),
    # scheme://user:password@host
    (re.compile(r"(://[^:/@\s]+:)[^@\s]+(@)"), rf"\1{MASK}\2"),
]
SECRET_DIRS = ("/run/secrets",)


def _secret_values() -> List[str]:
    values = [v for k, v in os.environ.items() if _SENSITIVE_NAME.search(k) and v and len(v) >= 4]
    for d in SECRET_DIRS:
        try:
            for name in os.listdir(d):
                try:
                    with open(os.path.join(d, name), encoding="utf-8") as f:
                        content = f.read().strip()
                    if len(content) >= 4:
                        values.append(content)
                except OSError:
                    continue
        except OSError:
            continue
    return sorted(set(values), key=len, reverse=True)


@lru_cache(maxsize=1)
def _cached_secret_values() -> tuple:
    return tuple(_secret_values())


def refresh_secret_cache() -> None:
    _cached_secret_values.cache_clear()


def redact_text(text: str, extra_secrets: Iterable[str] = ()) -> str:
    if not text:
        return text
    out = str(text)
    for secret in list(extra_secrets) + list(_cached_secret_values()):
        if secret and secret in out:
            out = out.replace(secret, MASK)
    for pattern, replacement in _PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def redact(value: Any) -> Any:
    """Recursively redact strings in dicts / lists; values of sensitive keys are masked."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: (MASK if isinstance(k, str) and _SENSITIVE_NAME.search(k) and v not in (None, "", False)
                    else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value
