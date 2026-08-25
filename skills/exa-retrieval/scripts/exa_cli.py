#!/usr/bin/env python3
"""Agent-friendly Exa CLI contract."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from exa_common import ExaError, compact_text, configure_stdio, cost_total, dump_json, request_json
from exa_transport import choose_transport, execute, mcp_tool

PROVIDER = "exa"
BASIC_CATEGORIES = [
    "company",
    "publication",
    "news",
    "personal site",
    "people",
]
ADVANCED_CATEGORIES = [
    "company",
    "publication",
    "news",
    "pdf",
    "github",
    "personal site",
    "people",
    "financial report",
]
SEARCH_TYPES = ["instant", "fast", "auto", "deep-lite", "deep", "deep-reasoning"]
DEEP_TYPES = {"deep-lite", "deep", "deep-reasoning"}
EFFORTS = ["minimal", "low", "medium", "high", "xhigh", "auto", "max"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class CliError(ValueError):
    pass


def iso_date(value: Optional[str], *, end: bool = False) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if DATE_RE.match(value):
        return value + ("T23:59:59.999Z" if end else "T00:00:00.000Z")
    if "T" in value:
        return value
    raise CliError(f"Date must be YYYY-MM-DD or ISO-8601 datetime: {value!r}")


def build_find_payload(args: argparse.Namespace) -> Dict[str, Any]:
    if not 1 <= args.limit <= 25:
        raise CliError("Basic find --limit must be between 1 and 25.")
    payload: Dict[str, Any] = {
        "query": args.query,
        "type": "auto",
        "numResults": args.limit,
        "contents": {"highlights": True},
    }
    if args.category:
        payload["category"] = args.category
    return payload


def _contents_block(args: argparse.Namespace) -> Optional[Dict[str, Any]]:
    if args.content == "none":
        return None
    block: Dict[str, Any] = {}
    if args.content == "highlights":
        block["highlights"] = True
    elif args.content == "text":
        block["text"] = True
    elif args.content == "summary":
        block["summary"] = {}
    if args.fresh_hours is not None:
        if not -1 <= args.fresh_hours <= 720:
            raise CliError("--fresh-hours must be between -1 and 720.")
        block["maxAgeHours"] = args.fresh_hours
    return block


def build_advanced_payload(args: argparse.Namespace) -> Dict[str, Any]:
    if not 1 <= args.limit <= 100:
        raise CliError("Advanced --limit must be between 1 and 100.")
    if args.type in DEEP_TYPES and not args.allow_deep:
        raise CliError(f"Search type {args.type!r} requires explicit --allow-deep.")
    if args.additional_query and args.type not in DEEP_TYPES:
        raise CliError("--additional-query only works with deep-lite/deep/deep-reasoning.")
    if args.category in {"company", "people"} and (args.after or args.before or args.exclude_domain):
        raise CliError("Exa company/people categories do not support published-date or exclude-domain filters.")

    payload: Dict[str, Any] = {
        "query": args.query,
        "type": args.type,
        "numResults": args.limit,
    }
    if args.category:
        payload["category"] = args.category
    if args.include_domain:
        payload["includeDomains"] = args.include_domain
    if args.exclude_domain:
        payload["excludeDomains"] = args.exclude_domain
    if args.after:
        payload["startPublishedDate"] = iso_date(args.after, end=False)
    if args.before:
        payload["endPublishedDate"] = iso_date(args.before, end=True)
    if args.location:
        loc = args.location.upper()
        if not re.match(r"^[A-Z]{2}$", loc):
            raise CliError("--location must be a two-letter ISO country code, e.g. US.")
        payload["userLocation"] = loc
    if args.additional_query:
        payload["additionalQueries"] = args.additional_query
    contents = _contents_block(args)
    if contents is not None:
        payload["contents"] = contents
    return payload


def envelope(operation: str, data: Mapping[str, Any], *, results: Any = None, transport: str = "api") -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "provider": PROVIDER,
        "operation": operation,
        "transport": transport,
        "request_id": data.get("requestId"),
    }
    cost = cost_total(data)
    if cost is not None:
        out["cost_usd"] = cost
    meta = data.get("_transport_meta")
    if isinstance(meta, Mapping):
        out["transport_meta"] = dict(meta)
    if results is not None:
        out["results"] = results
    return out


def normalize_search_results(data: Mapping[str, Any], max_chars: int = 1200) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    raw = data.get("results") or []
    if not isinstance(raw, list):
        return items
    for row in raw:
        if not isinstance(row, Mapping):
            continue
        highlights = row.get("highlights")
        if isinstance(highlights, list):
            snippet = "\n".join(str(x) for x in highlights if x is not None)
        else:
            snippet = row.get("summary") or row.get("text") or ""
        items.append({
            "title": row.get("title"),
            "url": row.get("url") or row.get("id"),
            "published_date": row.get("publishedDate"),
            "author": row.get("author"),
            "snippet": compact_text(snippet, max_chars),
        })
    return items


def print_search(operation: str, data: Mapping[str, Any], *, as_json: bool, max_chars: int = 1200, transport: str = "api") -> None:
    results = normalize_search_results(data, max_chars=max_chars)
    out = envelope(operation, data, results=results, transport=transport)
    if as_json:
        dump_json(out)
        return
    print(f"provider: {PROVIDER}")
    print(f"operation: {operation}")
    print(f"transport: {transport}")
    if out.get("request_id"):
        print(f"request_id: {out['request_id']}")
    if "cost_usd" in out:
        print(f"cost_usd: {out['cost_usd']:.6g}")
    if isinstance(out.get("transport_meta"), Mapping):
        meta = out["transport_meta"]
        if "session_reused" in meta:
            print(f"mcp_session_reused: {str(bool(meta['session_reused'])).lower()}")
        if meta.get("mcp_auth_mode"):
            print(f"mcp_auth_mode: {meta['mcp_auth_mode']}")
        if meta.get("fallback_reason"):
            print(f"fallback_reason: {meta['fallback_reason']}")
        if meta.get("api_quota_tag"):
            print(f"api_quota_tag: {meta['api_quota_tag']}")
        if meta.get("api_quota_recovered"):
            print("api_quota_recovered: true")
    print(f"sources_reviewed: {len(results)}")
    for idx, row in enumerate(results, 1):
        print(f"\n{idx}. {row.get('title') or '(untitled)'}")
        if row.get("url"):
            print(f"   url: {row['url']}")
        if row.get("published_date"):
            print(f"   published: {row['published_date']}")
        if row.get("author"):
            print(f"   author: {row['author']}")
        if row.get("snippet"):
            text = str(row["snippet"]).replace("\n", " ")
            print(f"   highlight: {text}")


def _parse_mcp_basic_search(text: str) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for block in [x.strip() for x in text.split("\n\n---\n\n") if x.strip()]:
        row: Dict[str, Any] = {}
        highlights: List[str] = []
        in_highlights = False
        for line in block.splitlines():
            if line.startswith("Title: "):
                row["title"] = line[7:].strip()
            elif line.startswith("URL: "):
                row["url"] = line[5:].strip()
            elif line.startswith("Published: "):
                value = line[11:].strip()
                row["publishedDate"] = None if value == "N/A" else value
            elif line.startswith("Author: "):
                value = line[8:].strip()
                row["author"] = None if value == "N/A" else value
            elif line == "Highlights:":
                in_highlights = True
            elif line.startswith("Text: "):
                row["text"] = line[6:].strip()
            elif in_highlights:
                highlights.append(line)
        if highlights:
            row["highlights"] = [x for x in highlights if x.strip()]
        if row.get("url"):
            results.append(row)
    return {"results": results}


def _mcp_search_data(result: Mapping[str, Any], *, advanced: bool = False) -> Dict[str, Any]:
    text = str(result.get("_text") or "")
    if advanced:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ExaError("Exa MCP advanced search returned non-JSON content.") from exc
        if not isinstance(parsed, dict):
            raise ExaError("Exa MCP advanced search returned a non-object payload.")
        return parsed
    return _parse_mcp_basic_search(text)


def cmd_find(args: argparse.Namespace) -> int:
    payload = build_find_payload(args)

    def mcp_call(anonymous: bool) -> Dict[str, Any]:
        query = args.query
        if args.category:
            query = f"category:{args.category} {query}"
        result = mcp_tool("web_search_exa", {"query": query, "numResults": args.limit}, anonymous=anonymous).data
        data = _mcp_search_data(result)
        data["_transport_meta"] = {
            "session_reused": result.get("_mcp_session_reused"),
            "protocol_version": result.get("_mcp_protocol_version"),
            "mcp_auth_mode": result.get("_mcp_auth_mode"),
        }
        return data

    outcome = execute(
        api_call=lambda: request_json("POST", "/search", payload).data,
        mcp_call=mcp_call,
    )
    print_search("find", outcome.data, as_json=args.json, max_chars=args.max_snippet_chars, transport=outcome.transport)
    return 0


def normalize_contents(data: Mapping[str, Any], max_chars: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    statuses = {}
    for st in data.get("statuses") or []:
        if isinstance(st, Mapping):
            statuses[str(st.get("id"))] = {"status": st.get("status"), "source": st.get("source")}
    for row in data.get("results") or []:
        if not isinstance(row, Mapping):
            continue
        rid = str(row.get("id") or row.get("url") or "")
        rows.append({
            "title": row.get("title"),
            "url": row.get("url") or row.get("id"),
            "published_date": row.get("publishedDate"),
            "author": row.get("author"),
            "text": compact_text(row.get("text"), max_chars),
            "status": statuses.get(rid),
        })
    return rows


def _parse_mcp_read(text: str) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    body: List[str] = []

    def flush() -> None:
        nonlocal current, body
        if current is not None:
            current["text"] = "\n".join(body).strip()
            results.append(current)
        current = None
        body = []

    for line in text.splitlines():
        if line.startswith("# "):
            flush()
            current = {"title": line[2:].strip()}
        elif current is not None and line.startswith("URL: "):
            current["url"] = line[5:].strip()
        elif current is not None and line.startswith("Published: "):
            current["publishedDate"] = line[11:].strip()
        elif current is not None and line.startswith("Author: "):
            current["author"] = line[8:].strip()
        elif current is not None:
            body.append(line)
    flush()
    return {"results": results}


def cmd_read(args: argparse.Namespace) -> int:
    if not 1 <= len(args.urls) <= 100:
        raise CliError("read accepts 1-100 URLs per request.")
    payload = {"urls": args.urls, "text": True}

    def mcp_call(anonymous: bool) -> Dict[str, Any]:
        result = mcp_tool(
            "web_fetch_exa",
            {"urls": args.urls, "maxCharacters": args.max_chars},
            anonymous=anonymous,
        ).data
        data = _parse_mcp_read(str(result.get("_text") or ""))
        data["_transport_meta"] = {
            "session_reused": result.get("_mcp_session_reused"),
            "protocol_version": result.get("_mcp_protocol_version"),
            "mcp_auth_mode": result.get("_mcp_auth_mode"),
        }
        return data

    outcome = execute(
        api_call=lambda: request_json("POST", "/contents", payload).data,
        mcp_call=mcp_call,
    )
    data = outcome.data
    transport = outcome.transport
    rows = normalize_contents(data, args.max_chars)
    out = envelope("read", data, results=rows, transport=transport)
    if args.json:
        dump_json(out)
        return 0
    print(f"provider: {PROVIDER}")
    print("operation: read")
    print(f"transport: {transport}")
    if out.get("request_id"):
        print(f"request_id: {out['request_id']}")
    if "cost_usd" in out:
        print(f"cost_usd: {out['cost_usd']:.6g}")
    if isinstance(out.get("transport_meta"), Mapping):
        meta = out["transport_meta"]
        if "session_reused" in meta:
            print(f"mcp_session_reused: {str(bool(meta['session_reused'])).lower()}")
        if meta.get("mcp_auth_mode"):
            print(f"mcp_auth_mode: {meta['mcp_auth_mode']}")
        if meta.get("fallback_reason"):
            print(f"fallback_reason: {meta['fallback_reason']}")
        if meta.get("api_quota_tag"):
            print(f"api_quota_tag: {meta['api_quota_tag']}")
        if meta.get("api_quota_recovered"):
            print("api_quota_recovered: true")
    for idx, row in enumerate(rows, 1):
        print(f"\n## {idx}. {row.get('title') or row.get('url') or '(untitled)'}")
        if row.get("url"):
            print(f"url: {row['url']}")
        if row.get("published_date"):
            print(f"published: {row['published_date']}")
        if row.get("text"):
            print("\n" + row["text"])
    return 0


def build_advanced_mcp_args(args: argparse.Namespace) -> Dict[str, Any]:
    if args.type in DEEP_TYPES:
        raise CliError("Deep search modes require EXA_API_KEY / REST transport.")
    params: Dict[str, Any] = {
        "query": args.query,
        "numResults": args.limit,
        "type": args.type,
    }
    if args.category:
        params["category"] = args.category
    if args.include_domain:
        params["includeDomains"] = args.include_domain
    if args.exclude_domain:
        params["excludeDomains"] = args.exclude_domain
    if args.after:
        params["startPublishedDate"] = iso_date(args.after, end=False)
    if args.before:
        params["endPublishedDate"] = iso_date(args.before, end=True)
    if args.location:
        params["userLocation"] = args.location.upper()
    if args.additional_query:
        params["additionalQueries"] = args.additional_query
    if args.fresh_hours is not None:
        params["maxAgeHours"] = args.fresh_hours
    if args.content == "highlights":
        params["enableHighlights"] = True
        params["highlightsMaxCharacters"] = args.max_snippet_chars
    elif args.content == "summary":
        params["enableSummary"] = True
    elif args.content == "text":
        params["textMaxCharacters"] = args.max_snippet_chars
    return params


def cmd_advanced(args: argparse.Namespace) -> int:
    payload = build_advanced_payload(args)
    supports_mcp = args.type not in DEEP_TYPES and args.content != "none"

    def mcp_call(anonymous: bool) -> Dict[str, Any]:
        result = mcp_tool(
            "web_search_advanced_exa",
            build_advanced_mcp_args(args),
            anonymous=anonymous,
        ).data
        data = _mcp_search_data(result, advanced=True)
        data["_transport_meta"] = {
            "session_reused": result.get("_mcp_session_reused"),
            "protocol_version": result.get("_mcp_protocol_version"),
            "mcp_auth_mode": result.get("_mcp_auth_mode"),
        }
        return data

    outcome = execute(
        api_call=lambda: request_json("POST", "/search", payload).data,
        mcp_call=mcp_call if supports_mcp else None,
        supports_mcp=supports_mcp,
    )
    print_search("advanced", outcome.data, as_json=args.json, max_chars=args.max_snippet_chars, transport=outcome.transport)
    return 0


def _read_schema(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    p = Path(path)
    try:
        value = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"Cannot read JSON schema {path!r}: {exc}") from exc
    if not isinstance(value, dict):
        raise CliError("--output-schema must contain a JSON object.")
    return value


def build_research_payload(args: argparse.Namespace) -> Dict[str, Any]:
    if not args.confirm_cost:
        raise CliError("Creating a new Exa Agent run requires explicit --confirm-cost.")
    payload: Dict[str, Any] = {"query": args.query, "effort": args.effort}
    if args.system_prompt:
        payload["systemPrompt"] = args.system_prompt
    schema = _read_schema(args.output_schema)
    if schema is not None:
        payload["outputSchema"] = schema
    if args.previous_run_id:
        payload["previousRunId"] = args.previous_run_id
    if args.budget is not None:
        if args.budget <= 0:
            raise CliError("--budget must be > 0.")
        if args.effort not in {"auto", "max"}:
            raise CliError("Exa documents --budget for metered auto/max efforts; use --effort auto or max with --budget.")
        payload["budget"] = {"maxCostDollars": args.budget}
    return payload


def agent_headers(args: argparse.Namespace) -> Dict[str, str]:
    if not args.beta:
        return {}
    return {"Exa-Beta": ",".join(args.beta)}


def format_agent(data: Mapping[str, Any], *, as_json: bool, timed_out: bool = False) -> None:
    out: Dict[str, Any] = {
        "provider": PROVIDER,
        "operation": "research",
        "run_id": data.get("id"),
        "status": data.get("status"),
        "stop_reason": data.get("stopReason"),
        "timed_out": timed_out,
        "output": data.get("output"),
        "usage": data.get("usage"),
        "cost_dollars": data.get("costDollars"),
    }
    if as_json:
        dump_json(out)
        return
    print(f"provider: {PROVIDER}")
    print("operation: research")
    print(f"run_id: {out.get('run_id')}")
    print(f"status: {out.get('status')}")
    if timed_out:
        print("timed_out: true")
        print("note: remote Exa Agent run may still be active; query it later with --run-id.")
    cost = out.get("cost_dollars")
    if isinstance(cost, Mapping) and isinstance(cost.get("total"), (int, float)):
        print(f"cost_usd: {cost['total']}")
    output = out.get("output")
    if isinstance(output, Mapping):
        text = output.get("text")
        structured = output.get("structured")
        if text:
            print("\n" + str(text))
        if structured not in (None, False, ""):
            print("\nstructured:")
            print(json.dumps(structured, ensure_ascii=False, indent=2))


def get_run(run_id: str, args: argparse.Namespace) -> Dict[str, Any]:
    if not re.match(r"^[A-Za-z0-9_.:-]{1,200}$", run_id):
        raise CliError("Invalid Exa Agent run id.")
    return request_json("GET", f"/agent/runs/{run_id}", headers=agent_headers(args)).data


def cmd_research(args: argparse.Namespace) -> int:
    choose_transport(requires_api=True)
    if args.run_id:
        data = get_run(args.run_id, args)
        format_agent(data, as_json=args.json)
        return 0

    if not args.query:
        raise CliError("research requires QUERY unless --run-id is used.")
    payload = build_research_payload(args)
    data = request_json("POST", "/agent/runs", payload, headers=agent_headers(args)).data
    run_id = data.get("id")
    if not run_id:
        raise ExaError("Exa Agent create response did not include a run id.")

    terminal = {"completed", "failed", "cancelled"}
    if data.get("status") in terminal or args.max_wait <= 0:
        format_agent(data, as_json=args.json)
        return 0

    deadline = time.monotonic() + args.max_wait
    while time.monotonic() < deadline:
        time.sleep(max(0.5, args.poll_interval))
        data = get_run(str(run_id), args)
        if data.get("status") in terminal:
            format_agent(data, as_json=args.json)
            return 0
    format_agent(data, as_json=args.json, timed_out=True)
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="exa",
        description="Lightweight Exa CLI: REST preferred with EXA_API_KEY; anonymous Hosted MCP fallback when unavailable or quota-exhausted in auto mode.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    f = sub.add_parser("find", help="Basic semantic web search; default everyday Exa action.")
    f.add_argument("query")
    f.add_argument("-n", "--limit", type=int, default=8)
    f.add_argument("--category", choices=BASIC_CATEGORIES)
    f.add_argument("--max-snippet-chars", type=int, default=1200)
    f.add_argument("--json", action="store_true")
    f.set_defaults(func=cmd_find)

    r = sub.add_parser("read", help="Fetch clean text for one or more known URLs.")
    r.add_argument("urls", nargs="+")
    r.add_argument("--max-chars", type=int, default=6000)
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_read)

    a = sub.add_parser("advanced", help="Search with explicit filters/modes. Read references/advanced.md first.")
    a.add_argument("query")
    a.add_argument("-n", "--limit", type=int, default=10)
    a.add_argument("--type", choices=SEARCH_TYPES, default="auto")
    a.add_argument("--category", choices=ADVANCED_CATEGORIES)
    a.add_argument("--include-domain", action="append", default=[])
    a.add_argument("--exclude-domain", action="append", default=[])
    a.add_argument("--after")
    a.add_argument("--before")
    a.add_argument("--location")
    a.add_argument("--additional-query", action="append", default=[])
    a.add_argument("--content", choices=["highlights", "text", "summary", "none"], default="highlights")
    a.add_argument("--fresh-hours", type=int)
    a.add_argument("--allow-deep", action="store_true")
    a.add_argument("--max-snippet-chars", type=int, default=1600)
    a.add_argument("--json", action="store_true")
    a.set_defaults(func=cmd_advanced)

    q = sub.add_parser("research", help="Create/poll an Exa Agent run; new runs require --confirm-cost.")
    q.add_argument("query", nargs="?")
    q.add_argument("--run-id")
    q.add_argument("--effort", choices=EFFORTS, default="low")
    q.add_argument("--system-prompt")
    q.add_argument("--output-schema")
    q.add_argument("--previous-run-id")
    q.add_argument("--budget", type=float)
    q.add_argument("--beta", action="append", default=[])
    q.add_argument("--confirm-cost", action="store_true")
    q.add_argument("--poll-interval", type=float, default=2.0)
    q.add_argument("--max-wait", type=float, default=120.0)
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_research)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    configure_stdio()
    args = parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (CliError, ExaError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("error: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
