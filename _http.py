"""
PagoMedios HTTP client module.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from config import PAGOMEDIOS_BASE_URL, HTTP_TIMEOUT, logger


def _resolve_token() -> str:
    resolved = os.environ.get("PAGOMEDIOS_BEARER_TOKEN", "")
    if not resolved:
        raise ValueError(
            "PAGOMEDIOS_BEARER_TOKEN env var is required. Configure it in your .env file."
        )
    return resolved


def _build_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_resolve_token()}",
        "Content-Type": "application/json",
    }


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict | list | str:
    """Execute an HTTP request against the PagoMedios API.

    Error contract:
    - HTTP >= 400 → {"error": True, "status_code": int, "detail": str}
    - Empty body  → {"ok": True, "status_code": int}
    - Plaintext   → {"text": str}
    - JSON        → parsed dict or list
    """
    url = f"{PAGOMEDIOS_BASE_URL}{path}"
    if params:
        params = {k: v for k, v in params.items() if v is not None and v != ""}

    logger.info("%s %s", method.upper(), url)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.request(
            method,
            url,
            headers=_build_headers(),
            params=params,
            json=body,
        )
    logger.info("Respuesta HTTP %s", resp.status_code)

    if resp.status_code >= 400:
        return {
            "error": True,
            "status_code": resp.status_code,
            "detail": resp.text,
        }
    if not resp.text.strip():
        return {"ok": True, "status_code": resp.status_code}
    try:
        return resp.json()
    except Exception:
        return {"text": resp.text}


def _json(result: Any) -> str:
    return json.dumps(result, ensure_ascii=False, default=str)


def _drop_none(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}
