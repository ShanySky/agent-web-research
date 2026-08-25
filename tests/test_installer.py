import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "scripts" / "install.py"


class InstallerTests(unittest.TestCase):
    def run_install(self, project: Path, *args):
        proc = subprocess.run(
            [sys.executable, str(INSTALL), "--project-root", str(project), *args],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            self.fail(f"installer failed: {proc.stdout}\n{proc.stderr}")
        return proc

    def test_default_direct_installs_three_skills_and_no_rule_dir(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            self.run_install(p)
            self.assertTrue((p / ".agents/skills/exa-retrieval/SKILL.md").exists())
            self.assertTrue((p / ".agents/skills/web-research-router/SKILL.md").exists())
            self.assertTrue((p / ".agents/skills/context7-tech-docs/SKILL.md").exists())
            self.assertTrue((p / ".agents/skills/context7-tech-docs/references/node-isolation.md").exists())
            self.assertTrue((p / ".codex/agents/web-searcher.toml").exists())
            self.assertFalse((p / ".agents/custom-rules/web-research-router.md").exists())

    def test_default_skill_router_patch_has_no_rule_path(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            self.run_install(p, "--patch-agents")
            text = (p / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("`web-research-router` Skill", text)
            self.assertIn("`context7-tech-docs`", text)
            self.assertNotIn("custom-rules", text)
            self.assertEqual(text.count("web-research-router:start"), 1)

    def test_file_routing_custom_rules_dir(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            self.run_install(
                p,
                "--routing-style", "file",
                "--rules-dir", "rules/web",
                "--patch-agents",
            )
            self.assertTrue((p / "rules/web/web-research-router.md").exists())
            text = (p / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("rules/web/web-research-router.md", text)
            self.assertIn("`context7-tech-docs`", text)

    def test_thin_alias_still_maps_to_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            self.run_install(p, "--routing-style", "thin", "--rules-dir", ".agents/custom-rules")
            self.assertTrue((p / ".agents/custom-rules/web-research-router.md").exists())

    def test_existing_agent_is_preserved_and_candidate_created(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            target = p / ".codex/agents/web-searcher.toml"
            target.parent.mkdir(parents=True)
            target.write_text("original", encoding="utf-8")
            self.run_install(p)
            self.assertEqual(target.read_text(encoding="utf-8"), "original")
            self.assertTrue((p / ".codex/agents/web-searcher.agent-web-research.candidate.toml").exists())

    def test_repeat_install_does_not_create_candidates_when_identical(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            self.run_install(p)
            second = self.run_install(p)
            self.assertIn("already current skill", second.stdout)
            self.assertFalse((p / ".agents/skills/exa-retrieval.candidate").exists())
            self.assertFalse((p / ".agents/skills/web-research-router.candidate").exists())
            self.assertFalse((p / ".agents/skills/context7-tech-docs.candidate").exists())
            self.assertFalse((p / ".codex/agents/web-searcher.agent-web-research.candidate.toml").exists())

    def test_patch_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            self.run_install(p, "--patch-agents")
            first = (p / "AGENTS.md").read_text(encoding="utf-8")
            self.run_install(p, "--patch-agents")
            second = (p / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(first, second)
            self.assertEqual(second.count("web-research-router:start"), 1)
            self.assertEqual(second.count("context7-tech-docs"), 1)

    def test_inline_style_does_not_install_rule_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            self.run_install(p, "--routing-style", "inline", "--patch-agents")
            self.assertFalse((p / ".agents/custom-rules/web-research-router.md").exists())
            text = (p / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("两层路由", text)
            self.assertIn("`context7-tech-docs`", text)

    def test_context7_check_can_be_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            proc = self.run_install(p, "--skip-context7-check")
            self.assertIn("Context7 CLI check skipped", proc.stdout)

    def test_update_replaces_managed_skills_with_repository_state(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            self.run_install(p, "--skip-context7-check")
            skill = p / ".agents/skills/exa-retrieval/SKILL.md"
            expected = skill.read_text(encoding="utf-8")
            skill.write_text("local stale copy", encoding="utf-8")
            self.run_install(p, "--update", "--skip-context7-check")
            self.assertEqual(skill.read_text(encoding="utf-8"), expected)
            self.assertFalse((p / ".agents/skills/exa-retrieval.candidate").exists())

    def test_update_refreshes_existing_managed_agents_block_without_patch_flag(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            self.run_install(p, "--patch-agents", "--skip-context7-check")
            agents = p / "AGENTS.md"
            text = agents.read_text(encoding="utf-8")
            text = text.replace("`context7-tech-docs`", "`old-context7-name`")
            agents.write_text(text, encoding="utf-8")
            self.run_install(p, "--update", "--skip-context7-check")
            updated = agents.read_text(encoding="utf-8")
            self.assertIn("`context7-tech-docs`", updated)
            self.assertNotIn("`old-context7-name`", updated)
            self.assertEqual(updated.count("web-research-router:start"), 1)

    def test_update_without_managed_agents_block_does_not_append_one(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            agents = p / "AGENTS.md"
            agents.write_text("# Project rules\n\nKeep this file project-owned.\n", encoding="utf-8")
            proc = self.run_install(p, "--update", "--skip-context7-check")
            self.assertEqual(agents.read_text(encoding="utf-8"), "# Project rules\n\nKeep this file project-owned.\n")
            self.assertIn("managed routing block not found", proc.stdout)

    def test_update_preserves_agent_and_refreshes_candidate_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            target = p / ".codex/agents/web-searcher.toml"
            target.parent.mkdir(parents=True)
            target.write_text("project customized agent", encoding="utf-8")
            self.run_install(p, "--update", "--skip-context7-check")
            self.assertEqual(target.read_text(encoding="utf-8"), "project customized agent")
            candidate = p / ".codex/agents/web-searcher.agent-web-research.candidate.toml"
            self.assertTrue(candidate.exists())
            self.assertIn('name = "web-searcher"', candidate.read_text(encoding="utf-8"))

    def test_replace_agent_explicitly_uses_repository_agent(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            target = p / ".codex/agents/web-searcher.toml"
            target.parent.mkdir(parents=True)
            target.write_text("project customized agent", encoding="utf-8")
            self.run_install(p, "--update", "--replace-agent", "--skip-context7-check")
            text = target.read_text(encoding="utf-8")
            self.assertIn('name = "web-searcher"', text)
            self.assertNotEqual(text, "project customized agent")


if __name__ == "__main__":
    unittest.main()
