"""Proxy environment normalization shared by real-API smoke entrypoints."""

from __future__ import annotations

import importlib.util
import os

PROXY_ENV_KEYS = (
    "ALL_PROXY",
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "all_proxy",
    "https_proxy",
    "http_proxy",
)


def normalize_proxy_env_for_httpx() -> list[dict[str, str]]:
    """Rewrite ``socks://`` proxy URLs to schemes httpx can parse."""

    socksio_available = _module_available("socksio")
    adjustments: list[dict[str, str]] = []
    for key in PROXY_ENV_KEYS:
        value = os.environ.get(key)
        if not value:
            continue
        scheme, separator, remainder = value.partition("://")
        if not separator or not scheme.lower().startswith("socks"):
            continue
        target_scheme = "socks5" if socksio_available else "http"
        if scheme.lower() == target_scheme:
            continue
        os.environ[key] = f"{target_scheme}://{remainder}"
        adjustments.append({"key": key, "from": f"{scheme}://", "to": f"{target_scheme}://"})
    return adjustments


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None
