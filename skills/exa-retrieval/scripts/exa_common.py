#!/usr/bin/env python3
"""Shared stdlib-only Exa REST helpers used by the API transport."""
from __future__ import annotations

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

DEFAULT_BASE = "https://api.exa.ai"
DEFAULT_TIMEOUT = 30.0


def configure_stdio() -> None:
    """Force UTF-8 text output without depending on the host shell code page."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, OSError, ValueError):
            # Some embedded or replaced streams do not support reconfiguration.
            pass


class ExaError(RuntimeError):
    pass


class ExaHttpError(ExaError):
    """Structured Exa REST HTTP error so transport policy can react safely."""

    def __init__(self, status: int, detail: str, data: Optional[Mapping[str, Any]] = None):
        self.status = int(status)
        self.data = dict(data) if isinstance(data, Mapping) else {}
        self.tag = self.data.get("tag") if isinstance(self.data.get("tag"), str) else None
        self.request_id = self.data.get("requestId") if isinstance(self.data.get("requestId"), str) else None
        self.detail = detail
        suffix = f" [{self.tag}]" if self.tag else ""
        super().__init__(f"Exa HTTP {self.status}{suffix}: {detail}")


@dataclass
class HttpResult:
    data: Dict[str, Any]
    status: int


def api_key() -> str:
    key = os.environ.get("EXA_API_KEY", "").strip()
    if not key:
        raise ExaError(
            "EXA_API_KEY is not set. The REST transport requires an Exa API key; use EXA_TRANSPORT=mcp or auto for anonymous Hosted MCP where supported."
        )
    return key


def api_base() -> str:
    return os.environ.get("EXA_API_BASE", DEFAULT_BASE).rstrip("/")


def timeout_seconds() -> float:
    raw = os.environ.get("EXA_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ExaError(f"Invalid EXA_TIMEOUT_SECONDS: {raw!r}") from exc
    return max(1.0, value)


def _headers(extra: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": api_key(),
        "User-Agent": "agent-web-research/0.6",
    }
    if extra:
        headers.update(extra)
    return headers


def _decode_error_body(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def request_json(
    method: str,
    path: str,
    payload: Optional[Mapping[str, Any]] = None,
    *,
    headers: Optional[Mapping[str, str]] = None,
    retries: int = 2,
) -> HttpResult:
    url = f"{api_base()}{path}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    attempt = 0
    while True:
        req = urllib.request.Request(
            url,
            data=body,
            headers=_headers(headers),
            method=method.upper(),
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds()) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
                if not isinstance(data, dict):
                    raise ExaError("Exa returned a non-object JSON response.")
                return HttpResult(data=data, status=getattr(resp, "status", 200))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            retryable = exc.code == 429 or 500 <= exc.code <= 599
            if retryable and attempt < retries:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    delay = min(10.0, float(retry_after)) if retry_after else min(5.0, 0.8 * (2 ** attempt) + random.random() * 0.3)
                except ValueError:
                    delay = min(5.0, 0.8 * (2 ** attempt) + random.random() * 0.3)
                time.sleep(delay)
                attempt += 1
                continue
            data = _decode_error_body(raw)
            detail = str(data.get("error") or (raw[:1200] if raw else exc.reason))
            raise ExaHttpError(exc.code, detail, data) from exc
        except urllib.error.URLError as exc:
            if attempt < retries:
                time.sleep(min(5.0, 0.8 * (2 ** attempt)))
                attempt += 1
                continue
            raise ExaError(f"Exa connection error: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise ExaError("Exa returned invalid JSON.") from exc


def cost_total(data: Mapping[str, Any]) -> Optional[float]:
    cost = data.get("costDollars")
    if isinstance(cost, Mapping):
        value = cost.get("total")
        if isinstance(value, (int, float)):
            return float(value)
    return None


def compact_text(value: Any, max_chars: int) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip() + "…"
    return text


def dump_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))
