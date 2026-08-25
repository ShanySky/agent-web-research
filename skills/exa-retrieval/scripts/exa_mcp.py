#!/usr/bin/env python3
"""Tiny stdlib-only Exa Hosted MCP client with cross-process session reuse.

This intentionally implements only the small Streamable HTTP subset needed by
agent-web-research. It does not perform tools/list on every invocation; tool
names are part of this kit's stable adapter contract.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from exa_common import ExaError, timeout_seconds

MCP_PROTOCOL_VERSION = "2025-11-25"
DEFAULT_MCP_ENDPOINT = (
    "https://mcp.exa.ai/mcp?tools="
    "web_search_exa,web_search_advanced_exa,web_fetch_exa"
)
DEFAULT_SESSION_MAX_AGE = 20 * 60 * 60  # Exa metadata TTL is currently 24h; stay below it.
USER_AGENT = "agent-web-research/0.6"


class McpHttpError(ExaError):
    def __init__(self, status: int, detail: str):
        super().__init__(f"Exa MCP HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


class McpRpcError(ExaError):
    def __init__(self, code: Any, message: str, data: Any = None):
        suffix = f"; data={data}" if data not in (None, "") else ""
        super().__init__(f"Exa MCP JSON-RPC error {code}: {message}{suffix}")
        self.code = code
        self.message = message
        self.data = data


def endpoint() -> str:
    return os.environ.get("EXA_MCP_ENDPOINT", DEFAULT_MCP_ENDPOINT).strip() or DEFAULT_MCP_ENDPOINT


def cache_root() -> Path:
    explicit = os.environ.get("EXA_MCP_CACHE_DIR", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "").strip()
        if local:
            return Path(local) / "agent-web-research"
    xdg = os.environ.get("XDG_CACHE_HOME", "").strip()
    if xdg:
        return Path(xdg).expanduser() / "agent-web-research"
    return Path.home() / ".cache" / "agent-web-research"


def cache_path() -> Path:
    mode = "authenticated" if os.environ.get("EXA_API_KEY", "").strip() else "anonymous"
    return cache_path_for_mode(mode)


def _auth_fingerprint() -> str:
    import hashlib
    key = os.environ.get("EXA_API_KEY", "").strip()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12] if key else "anonymous"


def cache_path_for_mode(auth_mode: str) -> Path:
    if auth_mode == "anonymous":
        suffix = "anonymous"
    elif auth_mode == "authenticated":
        suffix = f"authenticated-{_auth_fingerprint()}"
    else:
        raise ExaError(f"Invalid MCP auth mode: {auth_mode!r}")
    return cache_root() / f"exa-mcp-session-{suffix}.json"


def session_max_age() -> float:
    raw = os.environ.get("EXA_MCP_SESSION_MAX_AGE_SECONDS", str(DEFAULT_SESSION_MAX_AGE))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ExaError(f"Invalid EXA_MCP_SESSION_MAX_AGE_SECONDS: {raw!r}") from exc
    return max(0.0, value)


def _load_session(auth_mode: str) -> Optional[str]:
    path = cache_path_for_mode(auth_mode)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("endpoint") != endpoint() or data.get("protocol_version") != MCP_PROTOCOL_VERSION:
        return None
    sid = data.get("session_id")
    created = data.get("created_at")
    if not isinstance(sid, str) or not sid.strip() or not isinstance(created, (int, float)):
        return None
    max_age = session_max_age()
    if max_age > 0 and time.time() - float(created) > max_age:
        return None
    return sid.strip()


def _save_session(session_id: str, auth_mode: Optional[str] = None) -> None:
    mode = auth_mode or ("authenticated" if os.environ.get("EXA_API_KEY", "").strip() else "anonymous")
    path = cache_path_for_mode(mode)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "endpoint": endpoint(),
        "protocol_version": MCP_PROTOCOL_VERSION,
        "session_id": session_id,
        "created_at": time.time(),
        "last_used_at": time.time(),
        "auth_mode": mode,
    }
    # Atomic replace prevents partially-written cache files across concurrent CLI calls.
    fd, tmp_name = tempfile.mkstemp(prefix="exa-mcp-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass


def _touch_session(session_id: str, auth_mode: str) -> None:
    path = cache_path_for_mode(auth_mode)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(data, dict) and data.get("session_id") == session_id:
        data["last_used_at"] = time.time()
        try:
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


def clear_session(auth_mode: Optional[str] = None) -> None:
    mode = auth_mode or ("authenticated" if os.environ.get("EXA_API_KEY", "").strip() else "anonymous")
    try:
        cache_path_for_mode(mode).unlink()
    except OSError:
        pass


def _parse_body(raw: str, content_type: str) -> Dict[str, Any]:
    raw = raw.strip()
    if not raw:
        return {}
    if "text/event-stream" in (content_type or "").lower() or raw.startswith("event:") or "\ndata:" in raw:
        # Streamable HTTP may return one or more SSE events. Use the last JSON data event.
        candidates = []
        current = []
        for line in raw.splitlines():
            if line.startswith("data:"):
                current.append(line[5:].lstrip())
            elif not line.strip() and current:
                candidates.append("\n".join(current))
                current = []
        if current:
            candidates.append("\n".join(current))
        for item in reversed(candidates):
            try:
                value = json.loads(item)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        raise ExaError("Exa MCP returned SSE without a JSON data event.")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExaError("Exa MCP returned invalid JSON.") from exc
    if not isinstance(value, dict):
        raise ExaError("Exa MCP returned a non-object JSON-RPC response.")
    return value


def _post(payload: Mapping[str, Any], *, session_id: Optional[str] = None, auth_mode: str = "anonymous") -> Tuple[Dict[str, Any], Mapping[str, str]]:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        "User-Agent": USER_AGENT,
        "x-exa-source": "agent-web-research",
    }
    key = os.environ.get("EXA_API_KEY", "").strip()
    if auth_mode == "authenticated":
        if not key:
            raise ExaError("Authenticated MCP mode requires EXA_API_KEY.")
        # Header auth avoids leaking credentials through MCP URLs/logs.
        headers["x-api-key"] = key
    elif auth_mode != "anonymous":
        raise ExaError(f"Invalid MCP auth mode: {auth_mode!r}")
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    req = urllib.request.Request(endpoint(), data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds()) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = _parse_body(raw, resp.headers.get("Content-Type", ""))
            return parsed, resp.headers
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise McpHttpError(exc.code, raw[:1200] or str(exc.reason)) from exc
    except urllib.error.URLError as exc:
        raise ExaError(f"Exa MCP connection error: {exc.reason}") from exc


def _check_rpc(response: Mapping[str, Any]) -> Mapping[str, Any]:
    error = response.get("error")
    if isinstance(error, Mapping):
        code = error.get("code")
        message = error.get("message") or "unknown JSON-RPC error"
        data = error.get("data")
        raise McpRpcError(code, str(message), data)
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise ExaError("Exa MCP response did not contain an object result.")
    return result


def initialize_session(auth_mode: str = "anonymous") -> str:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "agent-web-research", "version": "0.6"},
        },
    }
    response, headers = _post(payload, auth_mode=auth_mode)
    result = _check_rpc(response)
    negotiated = result.get("protocolVersion")
    if negotiated and negotiated != MCP_PROTOCOL_VERSION:
        raise ExaError(
            f"Exa MCP negotiated unsupported protocol {negotiated!r}; expected {MCP_PROTOCOL_VERSION!r}."
        )
    sid = headers.get("Mcp-Session-Id") or headers.get("mcp-session-id")
    if not sid:
        raise ExaError("Exa MCP initialize response did not include Mcp-Session-Id.")
    sid = str(sid).strip()
    # Complete the MCP initialization lifecycle. A notification has no JSON-RPC id.
    notification = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    try:
        _post(notification, session_id=sid, auth_mode=auth_mode)
    except ExaError:
        # Some Streamable HTTP handlers return an empty/202-style notification response;
        # the session is still usable. The next tool call is the authoritative check.
        pass
    _save_session(sid, auth_mode)
    return sid


def _tool_result_text(result: Mapping[str, Any]) -> str:
    content = result.get("content")
    texts = []
    if isinstance(content, list):
        for part in content:
            if isinstance(part, Mapping) and part.get("type") == "text" and part.get("text") is not None:
                texts.append(str(part.get("text")))
    text = "\n".join(texts).strip()
    if result.get("isError"):
        raise ExaError(f"Exa MCP tool error: {text or 'unknown tool error'}")
    return text


def call_tool(name: str, arguments: Mapping[str, Any], *, anonymous: bool = False) -> Dict[str, Any]:
    auth_mode = "anonymous" if anonymous or not os.environ.get("EXA_API_KEY", "").strip() else "authenticated"
    cached = _load_session(auth_mode)
    sid = cached or initialize_session(auth_mode)

    def invoke(current_sid: str) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000) % 2_000_000_000,
            "method": "tools/call",
            "params": {"name": name, "arguments": dict(arguments)},
        }
        response, _ = _post(payload, session_id=current_sid, auth_mode=auth_mode)
        result = dict(_check_rpc(response))
        result["_text"] = _tool_result_text(result)
        result["_mcp_session_reused"] = bool(cached and current_sid == cached)
        result["_mcp_protocol_version"] = MCP_PROTOCOL_VERSION
        result["_mcp_auth_mode"] = auth_mode
        _touch_session(current_sid, auth_mode)
        return result

    try:
        return invoke(sid)
    except McpHttpError as exc:
        # Cached Streamable HTTP sessions can expire or be rejected. Reinitialize once,
        # transparently, but do not hide ordinary tool/schema errors.
        if cached and exc.status in {400, 404, 410}:
            clear_session(auth_mode)
            fresh = initialize_session(auth_mode)
            return invoke(fresh)
        raise
    except McpRpcError as exc:
        if cached and "session" in exc.message.lower():
            clear_session(auth_mode)
            fresh = initialize_session(auth_mode)
            return invoke(fresh)
        raise

