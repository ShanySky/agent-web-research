#!/usr/bin/env python3
"""Verify project-side installation; does not call Exa or Context7 services."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


def parser():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", default=".")
    p.add_argument("--mode", choices=["direct", "plugin"], default="direct")
    p.add_argument("--routing-style", choices=["skill", "inline", "file", "thin"], default="skill")
    p.add_argument("--rules-dir", default=".agents/custom-rules")
    p.add_argument("--skills-dir", default=".agents/skills")
    p.add_argument("--agents-dir", default=".codex/agents")
    return p


def check(label, ok, detail=""):
    print(f"[{'OK' if ok else 'WARN'}] {label}" + (f": {detail}" if detail else ""))
    return bool(ok)


def context7_status():
    exe = shutil.which("ctx7")
    if not exe:
        return False, "ctx7 not found in PATH"
    try:
        proc = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=15)
    except Exception as exc:
        return False, f"cannot run ctx7 --version: {exc}"
    text = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    if proc.returncode != 0:
        return False, text or f"ctx7 --version exited {proc.returncode}"
    return True, f"{exe}" + (f" ({text.splitlines()[0]})" if text else "")


def main():
    args = parser().parse_args()
    style = "file" if args.routing_style == "thin" else args.routing_style
    root = Path(args.project_root).expanduser().resolve()
    checks = []

    if style == "file":
        rule = root / args.rules_dir / "web-research-router.md"
        checks.append(check("routing rule file", rule.exists(), str(rule)))
    else:
        check("routing rule file", True, "not required by selected routing style")

    agent = root / args.agents_dir / "web-searcher.toml"
    checks.append(check("web-searcher", agent.exists(), str(agent)))
    candidate = root / args.agents_dir / "web-searcher.agent-web-research.candidate.toml"
    if candidate.exists():
        check("web-searcher candidate merge", False, f"{candidate} exists; existing agent was preserved, review/merge the candidate")

    if args.mode == "direct":
        for name in ("web-research-router", "exa-retrieval", "context7-tech-docs"):
            skill = root / args.skills_dir / name / "SKILL.md"
            checks.append(check(f"{name} direct skill", skill.exists(), str(skill)))
    else:
        exe = shutil.which("codex")
        checks.append(check("codex executable", bool(exe), exe or "not in PATH"))
        if exe:
            try:
                proc = subprocess.run([exe, "plugin", "list"], capture_output=True, text=True, timeout=15)
                text = (proc.stdout or "") + (proc.stderr or "")
                checks.append(check("plugin list mentions agent-web-research", "agent-web-research" in text, "plugin list is not a full cache-health check"))
            except Exception as exc:
                checks.append(check("plugin list", False, str(exc)))

    key = bool(os.environ.get("EXA_API_KEY", "").strip())
    transport = os.environ.get("EXA_TRANSPORT", "auto").strip().lower() or "auto"
    if transport not in {"auto", "api", "mcp"}:
        checks.append(check("EXA_TRANSPORT", False, f"unsupported value: {transport}"))
    elif transport == "api" and not key:
        checks.append(check("Exa transport", False, "EXA_TRANSPORT=api requires EXA_API_KEY"))
    elif transport == "mcp":
        check("Exa transport", True, "Hosted MCP selected; EXA_API_KEY is optional")
    elif key:
        check("Exa transport", True, "auto + EXA_API_KEY -> REST API")
    else:
        check("Exa transport", True, "auto without EXA_API_KEY -> anonymous Exa Hosted MCP; Key is only needed for REST/deep/research")

    ctx7_ok, ctx7_detail = context7_status()
    if ctx7_ok:
        check("Context7 CLI", True, ctx7_detail)
    else:
        check("Context7 CLI", False, ctx7_detail + "; Context7 Skill is installed but unavailable until the official ctx7 CLI is ready. For an isolated Agent tool environment, prefer Node 22 LTS and do not use less than Node 20.18.1; see the Skill node-isolation reference or docs/CONTEXT7-NODE-ISOLATION.md.")

    agents = root / "AGENTS.md"
    marker = False
    if agents.exists():
        marker = "<!-- web-research-router:start -->" in agents.read_text(encoding="utf-8", errors="replace")
    check("AGENTS routing marker", marker, "optional if routing is integrated manually")
    print("\nNote: after Plugin install/update, start a new Codex thread and explicitly verify web-research-router, exa-retrieval, and context7-tech-docs are discoverable; plugin list alone may not prove cached Skill payload health on every Codex build.")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
