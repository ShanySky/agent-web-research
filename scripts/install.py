#!/usr/bin/env python3
"""Safe cross-platform installer for the Agent Web Research."""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "agent-web-research"
MARKETPLACE_NAME = "agent-web-research"
START = "<!-- web-research-router:start -->"
END = "<!-- web-research-router:end -->"
LEGACY_MARKERS = (
    ("<!-- exa-search-routing:start -->", "<!-- exa-search-routing:end -->"),
    ("<!-- exa-web-research-router:start -->", "<!-- exa-web-research-router:end -->"),
)
DIRECT_SKILLS = ("web-research-router", "exa-retrieval", "context7-tech-docs")


def log(msg: str) -> None:
    print(msg)


def rel_display(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def candidate_path(target: Path) -> Path:
    if target.suffix:
        return target.with_name(f"{target.stem}.candidate{target.suffix}")
    return target.with_name(target.name + ".candidate")


def same_file_content(a: Path, b: Path) -> bool:
    try:
        return a.read_bytes() == b.read_bytes()
    except OSError:
        return False


def tree_fingerprint(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"):
        rel = path.relative_to(root).as_posix().encode("utf-8")
        h.update(rel + b"\0" + path.read_bytes() + b"\0")
    return h.hexdigest()


def same_tree_content(a: Path, b: Path) -> bool:
    try:
        return a.is_dir() and b.is_dir() and tree_fingerprint(a) == tree_fingerprint(b)
    except OSError:
        return False


def copy_file_safe(src: Path, dst: Path, *, dry: bool, force: bool = False, special_candidate: Optional[Path] = None) -> Tuple[Path, str]:
    if dst.exists() and same_file_content(src, dst):
        return dst, f"already current: {dst}"
    if dst.exists() and not force:
        cand = special_candidate or candidate_path(dst)
        action = f"candidate (existing preserved): {cand}"
        if not dry:
            cand.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, cand)
        return cand, action
    action = f"install: {dst}"
    if not dry:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return dst, action


def copy_tree_safe(src: Path, dst: Path, *, dry: bool, force: bool) -> Tuple[Path, str]:
    if dst.exists() and same_tree_content(src, dst):
        return dst, f"already current skill: {dst}"
    if dst.exists() and not force:
        cand = dst.with_name(dst.name + ".candidate")
        if not dry:
            if cand.exists():
                shutil.rmtree(cand)
            shutil.copytree(src, cand)
        return cand, f"candidate skill (existing preserved): {cand}"
    if not dry:
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
    return dst, f"install skill: {dst}"


def normalized_style(style: str) -> str:
    # Backward compatibility with v0.1's --routing-style thin.
    return "file" if style == "thin" else style


def render_snippet(style: str, rule_path: Optional[str] = None) -> str:
    style = normalized_style(style)
    mapping = {
        "skill": "AGENTS-skill-router.md",
        "inline": "AGENTS-inline.md",
        "file": "AGENTS-thin-reference.md",
    }
    path = REPO_ROOT / "templates" / "snippets" / mapping[style]
    text = path.read_text(encoding="utf-8")
    if style == "file":
        if not rule_path:
            raise ValueError("file routing style requires a rule path")
        text = text.replace("{{RULE_PATH}}", rule_path)
    return text.strip() + "\n"


def _find_routing_markers(text: str) -> Optional[Tuple[str, str]]:
    if START in text and END in text:
        return START, END
    for start, end in LEGACY_MARKERS:
        if start in text and end in text:
            return start, end
    return None


def patch_agents_file(path: Path, block: str, *, dry: bool) -> str:
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    markers = _find_routing_markers(old)
    if markers:
        start, end = markers
        before, rest = old.split(start, 1)
        _, after = rest.split(end, 1)
        block_body = block.strip()
        prefix = before.rstrip()
        new = (prefix + "\n\n" if prefix else "") + block_body + after
        action = f"update marked routing block: {path}"
    else:
        sep = "\n\n" if old.strip() else ""
        new = old.rstrip() + sep + block.strip() + "\n"
        action = f"append marked routing block: {path}"
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new, encoding="utf-8")
    return action


def codex_supports_plugins() -> Tuple[bool, str]:
    exe = shutil.which("codex")
    if not exe:
        return False, "codex executable not found in PATH"
    try:
        proc = subprocess.run([exe, "plugin", "--help"], capture_output=True, text=True, timeout=15)
    except Exception as exc:
        return False, f"cannot run codex plugin --help: {exc}"
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if proc.returncode != 0:
        return False, text.strip() or f"exit {proc.returncode}"
    if "marketplace" not in text.lower() or "add" not in text.lower():
        return False, "current Codex plugin CLI does not expose the expected marketplace/add surface"
    return True, exe


def context7_status() -> Tuple[bool, str]:
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


def report_context7_status() -> None:
    ok, detail = context7_status()
    if ok:
        log(f"Context7 CLI ready: {detail}")
        return
    log(f"Context7 CLI not ready: {detail}")
    log("Context7 is optional at install time. Install the official CLI with `npm install -g ctx7@latest`, or use the fnm isolation guidance in docs/CONTEXT7-NODE-ISOLATION.md when Node versions conflict.")


def run_plugin_install(*, dry: bool) -> None:
    if dry:
        exe = shutil.which("codex") or "codex"
    else:
        ok, detail = codex_supports_plugins()
        if not ok:
            raise RuntimeError(f"Plugin mode unavailable: {detail}. Use --mode direct.")
        exe = detail
    commands = [
        [exe, "plugin", "marketplace", "add", str(REPO_ROOT)],
        [exe, "plugin", "add", f"{PLUGIN_NAME}@{MARKETPLACE_NAME}"],
    ]
    for cmd in commands:
        log("plugin command: " + " ".join(cmd))
        if dry:
            continue
        proc = subprocess.run(cmd, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Plugin command failed with exit {proc.returncode}: {' '.join(cmd)}")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Install Agent Web Research into a project safely.")
    p.add_argument("--project-root", default=".")
    p.add_argument("--mode", choices=["direct", "plugin"], default="direct")
    p.add_argument("--skills-dir", default=".agents/skills")
    p.add_argument("--agents-dir", default=".codex/agents")
    p.add_argument("--rules-dir", default=".agents/custom-rules", help="Used only with --routing-style file/thin.")
    p.add_argument("--patch-agents", action="store_true", help="Patch/create AGENTS.md with a marked routing bootstrap block.")
    p.add_argument("--agents-file", default="AGENTS.md")
    p.add_argument(
        "--routing-style",
        choices=["skill", "inline", "file", "thin"],
        default="skill",
        help="skill (recommended, no rule directory), inline, or file. 'thin' is a v0.1 alias for file.",
    )
    p.add_argument("--skip-agent", action="store_true")
    p.add_argument("--skip-context7-check", action="store_true", help="Do not probe whether the official ctx7 CLI is available in PATH.")
    p.add_argument("--skip-rule", action="store_true", help="Only relevant to file/thin routing style; reference an existing rule instead of installing one.")
    p.add_argument("--force", action="store_true", help="Overwrite existing Skill/rule targets. Existing web-searcher still gets a candidate.")
    p.add_argument("--dry-run", action="store_true")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = parser().parse_args(argv)
    style = normalized_style(args.routing_style)
    project = Path(args.project_root).expanduser().resolve()
    rules_dir = (project / args.rules_dir).resolve() if not Path(args.rules_dir).is_absolute() else Path(args.rules_dir).resolve()
    skills_dir = (project / args.skills_dir).resolve() if not Path(args.skills_dir).is_absolute() else Path(args.skills_dir).resolve()
    agents_dir = (project / args.agents_dir).resolve() if not Path(args.agents_dir).is_absolute() else Path(args.agents_dir).resolve()
    agents_file = (project / args.agents_file).resolve() if not Path(args.agents_file).is_absolute() else Path(args.agents_file).resolve()
    rule_target = rules_dir / "web-research-router.md"

    log(f"project: {project}")
    log(f"mode: {args.mode}")
    log(f"routing_style: {style}")
    if style == "file":
        log(f"rules_dir: {rules_dir}")
    else:
        log("rules_dir: not used by selected routing style")
    if args.dry_run:
        log("DRY RUN: no files or plugin state will be changed")

    try:
        if args.mode == "plugin":
            run_plugin_install(dry=args.dry_run)
        else:
            for skill_name in DIRECT_SKILLS:
                src_skill = REPO_ROOT / "skills" / skill_name
                _, action = copy_tree_safe(src_skill, skills_dir / skill_name, dry=args.dry_run, force=args.force)
                log(action)

        if style == "file":
            if args.skip_rule:
                if args.patch_agents and not args.dry_run and not rule_target.exists():
                    raise RuntimeError(f"--skip-rule with file routing requires an existing rule file: {rule_target}")
                log(f"routing rule not installed (--skip-rule); expected existing file: {rule_target}")
            else:
                _, action = copy_file_safe(
                    REPO_ROOT / "templates" / "rules" / "web-research-router.md",
                    rule_target,
                    dry=args.dry_run,
                    force=args.force,
                )
                log(action)
        else:
            log("no standalone routing rule file installed")

        if not args.skip_agent:
            agent_target = agents_dir / "web-searcher.toml"
            candidate = agents_dir / "web-searcher.agent-web-research.candidate.toml"
            _, action = copy_file_safe(
                REPO_ROOT / "templates" / "agents" / "web-searcher.toml",
                agent_target,
                dry=args.dry_run,
                force=False,
                special_candidate=candidate,
            )
            log(action)

        if args.patch_agents:
            rule_ref = rel_display(rule_target, project) if style == "file" else None
            block = render_snippet(style, rule_ref)
            log(patch_agents_file(agents_file, block, dry=args.dry_run))
        else:
            log("AGENTS.md not modified (use --patch-agents to opt in)")

        if args.skip_context7_check:
            log("Context7 CLI check skipped (--skip-context7-check)")
        else:
            report_context7_status()

        log("done")
        if not args.dry_run:
            log("next: run python scripts/verify.py. EXA_API_KEY is optional for basic/advanced Exa retrieval. Context7 uses the official ctx7 CLI; it can work without authentication, while `ctx7 login` or CONTEXT7_API_KEY provides higher limits. For plugin mode, start a new Codex thread before testing skill discovery.")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
