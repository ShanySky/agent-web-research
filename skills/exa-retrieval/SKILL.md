---
name: exa-retrieval
description: 使用 Exa 进行网页语义检索、概念发现、长尾技术资料与 GitHub/论文/开发者资料检索；当宿主原生网页检索不可用、结果明显不足，或需要精确 domain/date/category 过滤时使用。
---

# Exa 检索

这是 **Exa 检索能力**，不是 Native Web Search。先按项目路由确认“由当前代理自行检索”，再决定使用 Native 还是 Exa。

将 `<skill-dir>` 替换为本 `SKILL.md` 所在目录。日常只需：

```bash
python "<skill-dir>/scripts/exa.py" find "<query>"
python "<skill-dir>/scripts/exa.py" read "<url>"
```

`find` 默认返回 highlights；`read` 读取已知 URL。默认 `EXA_TRANSPORT=auto`：有 `EXA_API_KEY` 时优先 REST；无 Key 时走匿名 Exa Hosted MCP；若 REST 因 Exa 明确的 402 credits/budget 耗尽而失败，基础检索和可等价执行的常规高级检索会临时切到匿名 MCP，并在冷却后自动 probe REST，额度恢复后自动切回。无需把 Exa MCP 注册给宿主。

CLI 自身统一以 UTF-8 输出，不依赖 Windows PowerShell/CMD 的默认代码页。需要机器可读结果时加 `--json`。输出会标记 `provider=exa`、`transport=api|mcp`，额度降级或恢复时还会带相应 transport metadata，便于排错。

优先使用 Exa 的场景：

- Native Web Search 不可用；
- 需要语义/概念发现，而不是普通关键词查找；
- 查找长尾技术资料、开发者资料、GitHub、论文或文档；
- Native 已做合理尝试但结果明显不足；
- 需要精确的 domain/date/category 等过滤。

Native 可用时，一般 Web、最新事实和网页浏览默认仍优先 Native；不要无目的双搜。

只有需要 domain/date/category、搜索模式或内容模式时，才读取 `references/advanced.md`（或运行 `advanced --help`）。匿名 MCP 支持常规 advanced；deep 模式需要 Key。只有需要 Exa Agent 多步研究时，才读取 `references/research.md`；该能力需要 Key。项目已有 `web-searcher` 时，一般复杂研究优先按 Execution Router 派子代理，以隔离搜索噪音。
