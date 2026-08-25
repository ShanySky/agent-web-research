import argparse
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "exa-retrieval" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import exa_cli  # noqa: E402
import exa_common  # noqa: E402
import exa_transport  # noqa: E402


class ExaCliTests(unittest.TestCase):
    def test_find_payload_is_small_and_highlight_first(self):
        args = argparse.Namespace(query="codex search", limit=8, category=None)
        payload = exa_cli.build_find_payload(args)
        self.assertEqual(payload["type"], "auto")
        self.assertEqual(payload["contents"], {"highlights": True})
        self.assertNotIn("text", payload["contents"])

    def test_basic_limit_is_capped(self):
        args = argparse.Namespace(query="x", limit=26, category=None)
        with self.assertRaises(exa_cli.CliError):
            exa_cli.build_find_payload(args)

    def _advanced(self, **overrides):
        base = dict(
            query="x", limit=10, type="auto", category=None,
            include_domain=[], exclude_domain=[], after=None, before=None,
            location=None, additional_query=[], content="highlights",
            fresh_hours=None, allow_deep=False,
        )
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_deep_requires_gate(self):
        with self.assertRaises(exa_cli.CliError):
            exa_cli.build_advanced_payload(self._advanced(type="deep"))
        payload = exa_cli.build_advanced_payload(self._advanced(type="deep", allow_deep=True))
        self.assertEqual(payload["type"], "deep")

    def test_company_date_filter_rejected(self):
        with self.assertRaises(exa_cli.CliError):
            exa_cli.build_advanced_payload(self._advanced(category="company", after="2026-01-01"))

    def test_date_normalization(self):
        self.assertEqual(exa_cli.iso_date("2026-08-25"), "2026-08-25T00:00:00.000Z")
        self.assertEqual(exa_cli.iso_date("2026-08-25", end=True), "2026-08-25T23:59:59.999Z")

    def test_rest_402_error_preserves_tag_for_transport_policy(self):
        import io
        import urllib.error
        body = b'{"requestId":"req-1","error":"credits exhausted","tag":"NO_MORE_CREDITS"}'
        err = urllib.error.HTTPError(
            "https://api.exa.ai/search", 402, "Payment Required", {}, io.BytesIO(body)
        )
        with mock.patch("urllib.request.urlopen", side_effect=err):
            os.environ["EXA_API_KEY"] = "paid-key"
            with self.assertRaises(exa_common.ExaHttpError) as ctx:
                exa_common.request_json("POST", "/search", {"query": "x"}, retries=0)
        self.assertEqual(ctx.exception.status, 402)
        self.assertEqual(ctx.exception.tag, "NO_MORE_CREDITS")
        self.assertEqual(ctx.exception.request_id, "req-1")

    def test_missing_api_key_is_clear(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(exa_common.ExaError) as ctx:
                exa_common.api_key()
        self.assertIn("EXA_API_KEY", str(ctx.exception))

    def test_stdio_forces_utf8_even_when_pythonioencoding_is_gbk(self):
        sample = "北京 © ™ — “中文引号” café 日本語 한국어 🙂 🚀"
        code = (
            "import sys; "
            f"sys.path.insert(0, {str(SCRIPTS)!r}); "
            "from exa_common import configure_stdio, dump_json; "
            "configure_stdio(); "
            f"dump_json({{'text': {sample!r}}})"
        )
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "gbk"
        proc = subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        text = proc.stdout.decode("utf-8")
        self.assertIn(sample, text)
        self.assertEqual(proc.stderr.decode("utf-8"), "")

    def test_cli_main_forces_utf8_before_command_output(self):
        sample = "北京 © ™ — “中文引号” café 日本語 한국어 🙂 🚀"
        code = f"""
import sys
import types
sys.path.insert(0, {str(SCRIPTS)!r})
import exa_cli
sample = {sample!r}
class P:
    def parse_args(self, argv):
        return types.SimpleNamespace(func=lambda args: (print(sample), 0)[1])
exa_cli.parser = lambda: P()
raise SystemExit(exa_cli.main([]))
"""
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "gbk"
        proc = subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertEqual(proc.stdout.decode("utf-8").strip(), sample)
        self.assertEqual(proc.stderr.decode("utf-8"), "")

    def test_research_requires_cost_confirmation(self):
        args = argparse.Namespace(
            confirm_cost=False, query="research", effort="low", system_prompt=None,
            output_schema=None, previous_run_id=None, budget=None,
        )
        with self.assertRaises(exa_cli.CliError):
            exa_cli.build_research_payload(args)

    def test_beta_header(self):
        args = argparse.Namespace(beta=["one", "two"])
        self.assertEqual(exa_cli.agent_headers(args), {"Exa-Beta": "one,two"})

    def test_summary_uses_object_shape(self):
        payload = exa_cli.build_advanced_payload(self._advanced(content="summary"))
        self.assertEqual(payload["contents"]["summary"], {})

    def test_budget_only_for_auto_or_max(self):
        args = argparse.Namespace(
            confirm_cost=True, query="research", effort="low", system_prompt=None,
            output_schema=None, previous_run_id=None, budget=1.0,
        )
        with self.assertRaises(exa_cli.CliError):
            exa_cli.build_research_payload(args)
        args.effort = "auto"
        payload = exa_cli.build_research_payload(args)
        self.assertEqual(payload["budget"], {"maxCostDollars": 1.0})


class TransportAndMcpTests(unittest.TestCase):
    def setUp(self):
        self._old_path = list(sys.path)
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"EXA_MCP_CACHE_DIR": self.tmp.name}, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()
        sys.path[:] = self._old_path

    def test_auto_transport_without_key_uses_mcp(self):
        import exa_transport
        self.assertEqual(exa_transport.choose_transport(), "mcp")

    def test_auto_transport_with_key_uses_api(self):
        import exa_transport
        os.environ["EXA_API_KEY"] = "test-key"
        self.assertEqual(exa_transport.choose_transport(), "api")

    def test_api_forced_without_key_is_clear(self):
        import exa_transport
        os.environ["EXA_TRANSPORT"] = "api"
        with self.assertRaises(exa_common.ExaError):
            exa_transport.choose_transport()

    def test_research_requires_key(self):
        import exa_transport
        with self.assertRaises(exa_common.ExaError):
            exa_transport.choose_transport(requires_api=True)

    def test_mcp_basic_search_parser(self):
        text = """Title: Example\nURL: https://example.com\nPublished: 2026-08-25\nAuthor: A\nHighlights:\nhello world\n\n---\n\nTitle: Two\nURL: https://two.example\nPublished: N/A\nAuthor: N/A\nHighlights:\nsecond"""
        data = exa_cli._parse_mcp_basic_search(text)
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["url"], "https://example.com")
        self.assertEqual(data["results"][1]["publishedDate"], None)

    def test_mcp_read_parser(self):
        text = """# Page One\nURL: https://example.com\nPublished: 2026-08-25\nAuthor: A\n\nBody line 1\nBody line 2"""
        data = exa_cli._parse_mcp_read(text)
        self.assertEqual(data["results"][0]["title"], "Page One")
        self.assertIn("Body line 2", data["results"][0]["text"])

    def test_mcp_sse_parser(self):
        import exa_mcp
        body = 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n'
        parsed = exa_mcp._parse_body(body, "text/event-stream")
        self.assertTrue(parsed["result"]["ok"])

    def test_mcp_cached_session_skips_initialize(self):
        import exa_mcp
        exa_mcp._save_session("sid-1")
        result_payload = {
            "jsonrpc": "2.0", "id": 3,
            "result": {"content": [{"type": "text", "text": "Title: X\nURL: https://x"}]},
        }
        with mock.patch.object(exa_mcp, "_post", return_value=(result_payload, {})) as post:
            result = exa_mcp.call_tool("web_search_exa", {"query": "x", "numResults": 1})
        self.assertEqual(post.call_count, 1)
        self.assertTrue(result["_mcp_session_reused"])
        self.assertEqual(post.call_args.kwargs["session_id"], "sid-1")

    def test_mcp_expired_session_reinitializes_once(self):
        import exa_mcp
        exa_mcp._save_session("sid-old")
        init = {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": exa_mcp.MCP_PROTOCOL_VERSION}}
        tool = {
            "jsonrpc": "2.0", "id": 4,
            "result": {"content": [{"type": "text", "text": "Title: X\nURL: https://x"}]},
        }
        calls = []
        def fake_post(payload, *, session_id=None, auth_mode="anonymous"):
            calls.append((payload.get("method"), session_id))
            if len(calls) == 1:
                raise exa_mcp.McpHttpError(404, "session not found")
            if payload.get("method") == "initialize":
                return init, {"Mcp-Session-Id": "sid-new"}
            if payload.get("method") == "notifications/initialized":
                return {}, {}
            return tool, {}
        with mock.patch.object(exa_mcp, "_post", side_effect=fake_post):
            result = exa_mcp.call_tool("web_search_exa", {"query": "x"})
        self.assertFalse(result["_mcp_session_reused"])
        self.assertIn(("initialize", None), calls)
        self.assertIn(("tools/call", "sid-new"), calls)


    def test_mcp_rpc_session_error_reinitializes_once(self):
        import exa_mcp
        exa_mcp._save_session("sid-old")
        init = {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": exa_mcp.MCP_PROTOCOL_VERSION}}
        tool = {
            "jsonrpc": "2.0", "id": 4,
            "result": {"content": [{"type": "text", "text": "Title: X\nURL: https://x"}]},
        }
        calls = []
        def fake_post(payload, *, session_id=None, auth_mode="anonymous"):
            calls.append((payload.get("method"), session_id))
            if len(calls) == 1:
                return {"jsonrpc": "2.0", "id": 2, "error": {"code": -32000, "message": "Session expired"}}, {}
            if payload.get("method") == "initialize":
                return init, {"Mcp-Session-Id": "sid-new"}
            if payload.get("method") == "notifications/initialized":
                return {}, {}
            return tool, {}
        with mock.patch.object(exa_mcp, "_post", side_effect=fake_post):
            result = exa_mcp.call_tool("web_search_exa", {"query": "x"})
        self.assertFalse(result["_mcp_session_reused"])
        self.assertIn(("tools/call", "sid-new"), calls)


    def test_mcp_anonymous_mode_does_not_forward_api_key(self):
        import exa_mcp
        os.environ["EXA_API_KEY"] = "paid-key"
        captured = {}

        class FakeResponse:
            status = 200
            headers = {"Content-Type": "application/json"}
            def read(self):
                return b'{"jsonrpc":"2.0","id":1,"result":{}}'
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        def fake_urlopen(req, timeout=None):
            captured["headers"] = dict(req.header_items())
            return FakeResponse()

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            exa_mcp._post({"jsonrpc": "2.0", "id": 1, "method": "x"}, auth_mode="anonymous")
        headers = {k.lower(): v for k, v in captured["headers"].items()}
        self.assertNotIn("x-api-key", headers)

    def test_mcp_session_cache_separates_anonymous_and_authenticated(self):
        import exa_mcp
        exa_mcp._save_session("anon", "anonymous")
        os.environ["EXA_API_KEY"] = "paid-key"
        exa_mcp._save_session("auth", "authenticated")
        self.assertNotEqual(exa_mcp.cache_path_for_mode("anonymous"), exa_mcp.cache_path_for_mode("authenticated"))
        self.assertTrue(exa_mcp.cache_path_for_mode("anonymous").exists())
        self.assertTrue(exa_mcp.cache_path_for_mode("authenticated").exists())

    def test_auto_402_quota_falls_back_anonymous_and_caches_state(self):
        os.environ["EXA_API_KEY"] = "paid-key"
        seen = []
        err = exa_common.ExaHttpError(
            402,
            "credits exhausted",
            {"tag": "NO_MORE_CREDITS", "requestId": "req-402"},
        )

        def api_call():
            seen.append("api")
            raise err

        def mcp_call(anonymous):
            seen.append(("mcp", anonymous))
            return {"results": []}

        outcome = exa_transport.execute(api_call, mcp_call)
        self.assertEqual(outcome.transport, "mcp")
        self.assertEqual(seen, ["api", ("mcp", True)])
        self.assertEqual(outcome.data["_transport_meta"]["fallback_reason"], "api_quota_exhausted")
        self.assertEqual(outcome.data["_transport_meta"]["api_quota_tag"], "NO_MORE_CREDITS")
        self.assertTrue(exa_transport.quota_state_path().exists())

    def test_cached_quota_state_skips_api_until_probe(self):
        os.environ["EXA_API_KEY"] = "paid-key"
        os.environ["EXA_API_QUOTA_PROBE_SECONDS"] = "3600"
        err = exa_common.ExaHttpError(402, "budget", {"tag": "API_KEY_BUDGET_EXCEEDED"})
        with mock.patch.object(exa_transport.time, "time", return_value=1000.0):
            state = exa_transport._mark_quota_exhausted(err)
        self.assertEqual(state["next_probe_at"], 4600.0)

        api = mock.Mock(return_value={"results": [{"url": "api"}]})
        mcp = mock.Mock(return_value={"results": [{"url": "mcp"}]})
        with mock.patch.object(exa_transport.time, "time", return_value=1200.0):
            outcome = exa_transport.execute(api, mcp)
        api.assert_not_called()
        mcp.assert_called_once_with(True)
        self.assertEqual(outcome.transport, "mcp")
        self.assertEqual(outcome.data["_transport_meta"]["fallback_reason"], "api_quota_exhausted_cached")

    def test_quota_probe_success_restores_api_and_clears_state(self):
        os.environ["EXA_API_KEY"] = "paid-key"
        os.environ["EXA_API_QUOTA_PROBE_SECONDS"] = "60"
        err = exa_common.ExaHttpError(402, "budget", {"tag": "TEAM_BUDGET_EXCEEDED"})
        with mock.patch.object(exa_transport.time, "time", return_value=1000.0):
            exa_transport._mark_quota_exhausted(err)
        self.assertTrue(exa_transport.quota_state_path().exists())

        api = mock.Mock(return_value={"results": [{"url": "api"}]})
        mcp = mock.Mock(return_value={"results": [{"url": "mcp"}]})
        with mock.patch.object(exa_transport.time, "time", return_value=1061.0):
            outcome = exa_transport.execute(api, mcp)
        api.assert_called_once()
        mcp.assert_not_called()
        self.assertEqual(outcome.transport, "api")
        self.assertTrue(outcome.data["_transport_meta"]["api_quota_recovered"])
        self.assertFalse(exa_transport.quota_state_path().exists())

    def test_explicit_api_never_falls_back_on_402(self):
        os.environ["EXA_API_KEY"] = "paid-key"
        os.environ["EXA_TRANSPORT"] = "api"
        err = exa_common.ExaHttpError(402, "credits", {"tag": "NO_MORE_CREDITS"})
        mcp = mock.Mock(return_value={})
        with self.assertRaises(exa_common.ExaHttpError):
            exa_transport.execute(mock.Mock(side_effect=err), mcp)
        mcp.assert_not_called()

    def test_429_does_not_trigger_mcp_fallback(self):
        os.environ["EXA_API_KEY"] = "paid-key"
        err = exa_common.ExaHttpError(429, "rate limit", {})
        mcp = mock.Mock(return_value={})
        with self.assertRaises(exa_common.ExaHttpError):
            exa_transport.execute(mock.Mock(side_effect=err), mcp)
        mcp.assert_not_called()

    def test_unrecognized_402_tag_does_not_fallback(self):
        os.environ["EXA_API_KEY"] = "paid-key"
        err = exa_common.ExaHttpError(402, "other payment", {"tag": "SOMETHING_NEW"})
        mcp = mock.Mock(return_value={})
        with self.assertRaises(exa_common.ExaHttpError):
            exa_transport.execute(mock.Mock(side_effect=err), mcp)
        mcp.assert_not_called()

    def test_advanced_mcp_rejects_deep(self):
        args = argparse.Namespace(
            query="x", limit=10, type="deep", category=None,
            include_domain=[], exclude_domain=[], after=None, before=None,
            location=None, additional_query=[], content="highlights",
            fresh_hours=None, allow_deep=True, max_snippet_chars=1600,
        )
        with self.assertRaises(exa_cli.CliError):
            exa_cli.build_advanced_mcp_args(args)


if __name__ == "__main__":
    unittest.main()
