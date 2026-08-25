# 关键官方来源（2026-08-25 核对）

## Codex

- OpenAI Plugins repository: https://github.com/openai/plugins
- Plugin creator: https://github.com/openai/plugins/blob/main/.agents/skills/plugin-creator/SKILL.md
- Plugin manifest spec: https://github.com/openai/plugins/blob/main/.agents/skills/plugin-creator/references/plugin-json-spec.md
- Codex plugin CLI implementation: https://github.com/openai/codex/blob/main/codex-rs/cli/src/plugin_cmd.rs
- Codex skills guidance/archive: https://github.com/llms-txt-archive/openai-platform/blob/main/codex/skills.md
- OpenAI skills repository deprecation notice: https://github.com/openai/skills

## Context7

- Context7 repository: https://github.com/upstash/context7
- Context7 CLI README: https://github.com/upstash/context7/blob/master/packages/cli/README.md
- Context7 CLI entrypoint: https://github.com/upstash/context7/blob/master/packages/cli/src/index.ts
- Context7 official CLI fallback/Skill template: https://github.com/upstash/context7/blob/master/packages/cli/src/setup/templates.ts
- Context7 CLI agent setup definitions: https://github.com/upstash/context7/blob/master/packages/cli/src/setup/agents.ts
- Context7 MCP package Node engine: https://github.com/upstash/context7/blob/master/packages/mcp/package.json
- Context7 server metadata: https://github.com/upstash/context7/blob/master/server.json

### Context7 Node 版本说明

Context7 顶层 README 当前仍写 `ctx7` CLI 需要 Node.js 18+，但其当前 MCP package 已明确要求 Node `>=20.18.1`，并依赖 `undici@7` 等已经转向 Node 20+ 的组件。为避免 Agent 工具环境踩到 Node 18 的依赖兼容问题，本项目把：

```text
Node >=20.18.1
```

作为**推荐基线**，并优先推荐 Node 22 LTS 作为独立 Agent 工具环境。这是本项目的稳定性建议，不应表述成 Context7 CLI 官方当前唯一最低要求。

## Exa

- Exa LLM index: https://exa.ai/llms.txt
- Search API for coding agents: https://exa.ai/docs/reference/search-api-guide-for-coding-agents
- Contents API for coding agents: https://exa.ai/docs/reference/contents-api-guide-for-coding-agents
- Agent API overview: https://exa.ai/docs/reference/agent-api/overview
- Exa MCP: https://exa.ai/docs/reference/exa-mcp
- Exa MCP server repository: https://github.com/exa-labs/exa-mcp-server
- OpenAPI spec: https://exa.ai/docs/exa-spec.json
- Pricing: https://exa.ai/pricing
- Error codes: https://exa.ai/docs/reference/error-codes

## 注意

Exa Search 当前推荐类型包括 `auto`、`fast`、`instant`、`deep-lite`、`deep`、`deep-reasoning`；旧资料中的 `neural`、`useAutoprompt`、`livecrawl` 等不应作为新实现默认参数。Exa Agent 在当前官方文档中仍标为 beta，并要求 `Exa-Beta: agent-2026-05-07` 请求头。

- Exa MCP protocol 2026-07-28 support issue #421: https://github.com/exa-labs/exa-mcp-server/issues/421
- Exa MCP client metadata/session TTL source: https://github.com/exa-labs/exa-mcp-server/blob/main/src/utils/mcpClientMetadata.ts
