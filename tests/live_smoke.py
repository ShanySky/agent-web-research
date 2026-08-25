#!/usr/bin/env python3
"""Optional live Exa smoke test for REST or keyless Hosted MCP."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "exa-retrieval" / "scripts" / "exa.py"

p = argparse.ArgumentParser()
p.add_argument("--transport", choices=["auto", "api", "mcp"], default="mcp")
args = p.parse_args()

if args.transport == "api" and not os.environ.get("EXA_API_KEY"):
    print("SKIP: --transport api requires EXA_API_KEY")
    raise SystemExit(0)

env = dict(os.environ)
env["EXA_TRANSPORT"] = args.transport
proc = subprocess.run(
    [sys.executable, str(CLI), "find", "Exa search official documentation", "-n", "2", "--json"],
    env=env,
)
raise SystemExit(proc.returncode)
