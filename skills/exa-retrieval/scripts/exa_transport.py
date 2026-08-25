#!/usr/bin/env python3
"""Transport selection for Exa REST API and Hosted MCP.

`auto` prefers REST when an API key exists. If REST returns one of Exa's
well-defined 402 quota/budget exhaustion tags, supported operations temporarily
fall back to *anonymous* Hosted MCP. The fallback state is cached so subsequent
CLI invocations do not keep paying a failed REST round-trip; after a probe TTL,
REST is tried again and automatically restored on success.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

from exa_common import ExaError, ExaHttpError, api_base, request_json
from exa_mcp import call_tool, cache_root as mcp_cache_root

TRANSPORTS = {"auto", "api", "mcp"}
QUOTA_TAGS = {
    "NO_MORE_CREDITS",
    "API_KEY_BUDGET_EXCEEDED",
    "TEAM_BUDGET_EXCEEDED",
}
DEFAULT_QUOTA_PROBE_SECONDS = 60 * 60


@dataclass
class TransportResult:
    transport: str
    data: Dict[str, Any]
    meta: Dict[str, Any] = field(default_factory=dict)


def configured_transport() -> str:
    value = os.environ.get("EXA_TRANSPORT", "auto").strip().lower() or "auto"
    if value not in TRANSPORTS:
        raise ExaError(f"Invalid EXA_TRANSPORT {value!r}; expected auto, api, or mcp.")
    return value


def has_api_key() -> bool:
    return bool(os.environ.get("EXA_API_KEY", "").strip())


def choose_transport(*, supports_mcp: bool = True, requires_api: bool = False) -> str:
    """Simple preflight selector retained for API-only operations/tests.

    Quota-aware fallback requires an actual REST attempt, so find/read/advanced
    should use execute() rather than relying on this function alone.
    """
    selected = configured_transport()
    if requires_api:
        if selected == "mcp":
            raise ExaError("This operation requires Exa REST/API credentials and cannot use anonymous MCP.")
        if not has_api_key():
            raise ExaError("This operation requires EXA_API_KEY.")
        return "api"
    if selected == "api":
        if not has_api_key():
            raise ExaError("EXA_TRANSPORT=api requires EXA_API_KEY.")
        return "api"
    if selected == "mcp":
        if not supports_mcp:
            raise ExaError("This operation is not supported by the Hosted MCP transport.")
        return "mcp"
    if has_api_key():
        return "api"
    if supports_mcp:
        return "mcp"
    raise ExaError("EXA_API_KEY is required because this operation has no anonymous MCP fallback.")


def _key_fingerprint() -> Optional[str]:
    key = os.environ.get("EXA_API_KEY", "").strip()
    if not key:
        return None
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _state_root() -> Path:
    explicit = os.environ.get("EXA_TRANSPORT_CACHE_DIR", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    return mcp_cache_root()


def quota_state_path() -> Path:
    return _state_root() / "exa-api-quota-state.json"


def quota_probe_seconds() -> float:
    raw = os.environ.get("EXA_API_QUOTA_PROBE_SECONDS", str(DEFAULT_QUOTA_PROBE_SECONDS))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ExaError(f"Invalid EXA_API_QUOTA_PROBE_SECONDS: {raw!r}") from exc
    return max(0.0, value)


def _load_quota_state() -> Optional[Dict[str, Any]]:
    path = quota_state_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("key_fingerprint") != _key_fingerprint() or data.get("api_base") != api_base():
        return None
    if data.get("tag") not in QUOTA_TAGS:
        return None
    if not isinstance(data.get("next_probe_at"), (int, float)):
        return None
    return data


def _write_state(data: Mapping[str, Any]) -> None:
    path = quota_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="exa-quota-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dict(data), f, ensure_ascii=False)
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass


def clear_quota_state() -> None:
    try:
        quota_state_path().unlink()
    except OSError:
        pass


def _mark_quota_exhausted(exc: ExaHttpError) -> Dict[str, Any]:
    now = time.time()
    state = {
        "key_fingerprint": _key_fingerprint(),
        "api_base": api_base(),
        "tag": exc.tag,
        "request_id": exc.request_id,
        "exhausted_at": now,
        "last_402_at": now,
        "next_probe_at": now + quota_probe_seconds(),
    }
    _write_state(state)
    return state


def _fallback_meta(state: Mapping[str, Any], *, reason: str) -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "fallback_reason": reason,
        "api_quota_tag": state.get("tag"),
        "api_next_probe_at": state.get("next_probe_at"),
    }
    if state.get("request_id"):
        meta["api_request_id"] = state.get("request_id")
    return meta


def _merge_meta(data: Dict[str, Any], meta: Mapping[str, Any]) -> Dict[str, Any]:
    if not meta:
        return data
    out = dict(data)
    current = out.get("_transport_meta")
    merged = dict(current) if isinstance(current, Mapping) else {}
    merged.update(meta)
    out["_transport_meta"] = merged
    return out


def is_quota_exhaustion(exc: BaseException) -> bool:
    return isinstance(exc, ExaHttpError) and exc.status == 402 and exc.tag in QUOTA_TAGS


def execute(
    api_call: Callable[[], Dict[str, Any]],
    mcp_call: Optional[Callable[[bool], Dict[str, Any]]] = None,
    *,
    supports_mcp: bool = True,
    requires_api: bool = False,
) -> TransportResult:
    """Execute an Exa operation under the configured transport policy.

    mcp_call receives a boolean `anonymous` flag. In quota fallback mode it is
    always True, ensuring an exhausted EXA_API_KEY is not forwarded to Hosted MCP.
    """
    selected = configured_transport()

    if requires_api:
        choose_transport(supports_mcp=False, requires_api=True)
        return TransportResult("api", api_call())

    if selected == "api":
        choose_transport(supports_mcp=supports_mcp)
        data = api_call()
        # A successful forced API request proves any prior quota cooldown is stale.
        if _load_quota_state() is not None:
            clear_quota_state()
            data = _merge_meta(data, {"api_quota_recovered": True})
        return TransportResult("api", data)

    if selected == "mcp":
        if not supports_mcp or mcp_call is None:
            raise ExaError("This operation is not supported by the Hosted MCP transport.")
        # Explicit MCP honors a configured key; otherwise it is anonymous.
        return TransportResult("mcp", mcp_call(not has_api_key()))

    # auto without a key: anonymous Hosted MCP where supported.
    if not has_api_key():
        if not supports_mcp or mcp_call is None:
            raise ExaError("EXA_API_KEY is required because this operation has no anonymous MCP fallback.")
        return TransportResult("mcp", mcp_call(True), {"selection_reason": "no_api_key"})

    # auto with key: if a previous recognized 402 is still cooling down, skip
    # the known-failing REST attempt and use anonymous MCP immediately.
    state = _load_quota_state() if supports_mcp and mcp_call is not None else None
    now = time.time()
    if state is not None and now < float(state["next_probe_at"]):
        meta = _fallback_meta(state, reason="api_quota_exhausted_cached")
        return TransportResult("mcp", _merge_meta(mcp_call(True), meta), meta)

    # No active cooldown, or probe time reached: try REST first.
    try:
        data = api_call()
    except ExaHttpError as exc:
        if is_quota_exhaustion(exc) and supports_mcp and mcp_call is not None:
            new_state = _mark_quota_exhausted(exc)
            meta = _fallback_meta(new_state, reason="api_quota_exhausted")
            return TransportResult("mcp", _merge_meta(mcp_call(True), meta), meta)
        # A non-quota API response means a cached quota diagnosis is no longer
        # authoritative. Do not mask auth/rate-limit/server errors with MCP.
        if state is not None:
            clear_quota_state()
        raise
    else:
        if state is not None:
            clear_quota_state()
            return TransportResult("api", _merge_meta(data, {"api_quota_recovered": True}), {"api_quota_recovered": True})
        return TransportResult("api", data)


def rest_request(method: str, path: str, payload: Optional[Mapping[str, Any]] = None, *, headers: Optional[Mapping[str, str]] = None) -> TransportResult:
    return TransportResult("api", request_json(method, path, payload, headers=headers).data)


def mcp_tool(tool: str, arguments: Mapping[str, Any], *, anonymous: bool = False) -> TransportResult:
    return TransportResult("mcp", call_tool(tool, arguments, anonymous=anonymous))
