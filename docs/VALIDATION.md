# 验证记录

验证日期：2026-08-25。

## 已完成

- Python `compileall`：通过。
- Windows/字符编码：在外部 `PYTHONIOENCODING=gbk` 的恶劣环境下，公共输出层和 `exa_cli.main()` 入口均强制 UTF-8；中文、`©`、长破折号、日韩文字与 emoji 输出通过，未出现 `UnicodeEncodeError`。
- 离线单元测试：40/40 通过。
- Transport Router：无 Key `auto -> mcp`；有 Key `auto -> api`；三类官方 402 quota/budget 错误会匿名 fallback 并缓存 cooldown；到 probe 时间 REST 成功会自动恢复；429/未知 402/显式 api 不 fallback。
- Hosted MCP：SSE JSON-RPC 解析、基础 search/read 结果解析、advanced JSON 结果路径、匿名不转发 API Key、匿名/认证 session cache 隔离覆盖。
- MCP session：跨 CLI 进程缓存逻辑覆盖；缓存 session 直接 `tools/call`，不重复 initialize / tools/list。
- MCP session 失效：HTTP 400/404/410 与 JSON-RPC session error 均会透明重建一次。
- Advanced：普通过滤可走 MCP；deep 模式仍要求 REST + Key；基础/高级 category 分层已覆盖实现。
- Research：继续要求 `EXA_API_KEY` 与显式成本确认。
- Direct 安装：默认安装两个 Skill 且不创建规则目录；可选自定义 `.agents/custom-rules` 路径通过。
- 真实临时项目 Direct 安装 + `scripts/verify.py`：通过；无 `EXA_API_KEY` 时正确识别为 `auto -> anonymous Hosted MCP`，不再误报缺 Key。
- 已有 `web-searcher.toml`：确认保留原文件并生成 candidate。
- 重复安装：内容相同时判定 `already current`，不制造 candidate 垃圾文件。
- AGENTS marker patch：严格幂等。
- Plugin 模式 dry-run：能生成 marketplace/add 命令，不修改插件状态。
- `marketplace.json`、repo marketplace、`.codex-plugin/plugin.json`：JSON 解析通过，local source 路径存在。

运行测试：

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## Live 验证状态

本执行环境无法解析外网域名 `mcp.exa.ai`，因此没有伪称完成真实 Hosted MCP POST。协议实现依据 Exa 当前 hosted server 源码、MCP 2025-11-25 行为以及 2026-08-19 的上游协议探测 issue #421；同时提供本机 live smoke：

```bash
# 无 Key，验证 Hosted MCP anonymous fallback
python tests/live_smoke.py --transport mcp

# 有 Key，验证 REST
python tests/live_smoke.py --transport api
```

匿名 MCP 会消耗 Exa free-tier tool-call 配额；REST 需要 `EXA_API_KEY`，可能产生 API 使用量。

## Plugin 运行时说明

本环境验证了 marketplace/manifest 结构和安装器 dry-run，没有在用户实际 Codex Windows 环境执行插件安装。若当前 Codex 的 local marketplace/cache 行为异常，README 保留 Direct fallback，并建议安装/升级插件后开启新线程验证 Skill discovery。
