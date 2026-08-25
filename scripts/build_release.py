#!/usr/bin/env python3
"""Build a clean GitHub Release ZIP from the repository."""
from __future__ import annotations

import argparse
import compileall
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_JSON = ROOT / ".codex-plugin" / "plugin.json"
DIST = ROOT / "dist"
EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build", ".venv", "venv"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def version() -> str:
    data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    value = str(data["version"]).strip()
    if not value:
        raise RuntimeError("plugin version is empty")
    return value


def validate_json() -> None:
    for path in (PLUGIN_JSON, ROOT / ".agents" / "plugins" / "marketplace.json"):
        json.loads(path.read_text(encoding="utf-8"))


def run_tests() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
    )
    if proc.returncode != 0:
        raise RuntimeError("tests failed")


def should_include(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def build_zip(ver: str) -> Path:
    DIST.mkdir(exist_ok=True)
    out = DIST / f"agent-web-research-v{ver}.zip"
    if out.exists():
        out.unlink()
    prefix = Path(f"agent-web-research-v{ver}")
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(ROOT.rglob("*")):
            if should_include(path):
                zf.write(path, (prefix / path.relative_to(ROOT)).as_posix())
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Build Agent Web Research release ZIP.")
    p.add_argument("--skip-tests", action="store_true")
    args = p.parse_args()

    validate_json()
    if not compileall.compile_dir(ROOT / "skills", quiet=1):
        raise RuntimeError("skill Python compile check failed")
    if not compileall.compile_dir(ROOT / "scripts", quiet=1):
        raise RuntimeError("repository script compile check failed")
    if not args.skip_tests:
        run_tests()

    out = build_zip(version())
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
