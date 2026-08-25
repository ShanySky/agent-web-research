# 关键官方来源（2026-08-25 核对）

## Codex

- OpenAI Plugins repository: https://github.com/openai/plugins
- Plugin creator: https://github.com/openai/plugins/blob/main/.agents/skills/plugin-creator/SKILL.md
- Plugin manifest spec: https://github.com/openai/plugins/blob/main/.agents/skills/plugin-creator/references/plugin-json-spec.md
- Codex plugin CLI implementation: https://github.com/openai/codex/blob/main/codex-rs/cli/src/plugin_cmd.rs
- Codex skills guidance/archive: https://github.com/llms-txt-archive/openai-platform/blob/main/codex/skills.md
- OpenAI skills repository deprecation notice: https://github.com/openai/skills

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
