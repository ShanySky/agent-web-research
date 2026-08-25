# 现成方案复用审计

核实日期：2026-08-25。

## 1. 结论

已经存在“Exa + Agent Skill + CLI”的成熟先例，因此**不应从概念上重复发明**。但没有发现一个现成项目同时满足以下项目特定需求：

- 与 Codex Native Search 共存而不重名；
- 两层 Router：执行者（main/subagent）与检索后端（Native/Exa）分离；
- 复用现有 GPT-5.4 `web-searcher`；
- `.agents/custom-rules` 可配置规则目录；
- Codex Plugin + Direct 双安装；
- 安装时安全合并 AGENTS / agent，不静默覆盖。

因此本包采用“**复用验证过的思想与可替代实现，自己维护项目特定路由/安装层**”策略。

## 2. CodeAlive-AI/exa-skills

地址：https://github.com/CodeAlive-AI/exa-skills

### 可直接复用/参考

- 明确支持 Codex 与其它 SKILL.md Agent；
- 无 MCP，直接 Exa REST；
- Python stdlib、零第三方依赖；
- `SKILL.md + scripts + references` progressive disclosure；
- Search / Contents / Answer / Similar 等通用能力；
- MIT License。

### 为什么本包不直接 vendor

- 它的目标是通用 Exa skills 集合，不负责 Codex Native vs Exa 路由；
- 没有你的 `web-searcher` 两层协作规则；
- 没有本项目的 Plugin/Direct 安装、AGENTS patch、规则路径需求；
- vendor 会引入上游同步与许可证通知维护成本。

### 何时可替换本包 CLI

如果未来不想维护自有 Exa client，可把本包 `scripts/` 替换为/转发到 CodeAlive 的 CLI，只要继续保持本包的稳定 contract 和 provider 标记即可。

## 3. HKUDS/CLI-Anything：cli-anything-exa

地址：https://github.com/HKUDS/CLI-Anything/blob/main/skills/cli-anything-exa/SKILL.md

### 可直接复用/参考

- 已有 Agent-native `cli-anything-exa`；
- search / contents；
- auto/fast/instant/deep/deep-reasoning；
- domain/date/category/location；
- highlights/text/summary；
- JSON 输出；
- 完整测试体系。

### 为什么不作为本包强依赖

- 需要额外安装 Python 包/CLI；
- 本包希望 Project AI 拿到 ZIP 即可工作，stdlib-only；
- 仍需要我们自己的 Router、agent、安装与规则层。

### 如果项目已经安装 CLI-Anything

可以让项目 AI 做一层 adapter，把 `exa.py` 的 `find/read/advanced` 调用改为 `cli-anything-exa`，无需改变 AGENTS 两层路由。

## 4. Exa 官方 exa-mcp-server / Skills

地址：https://github.com/exa-labs/exa-mcp-server

当前 MCP 核心：

- `web_search_exa`
- `web_fetch_exa`
- `web_search_advanced_exa`
- `agent_run`

官方 Skill 也采用 basic + advanced / agent 的分层，并强调语义搜索与在复杂研究中使用子代理隔离大量结果。这与本包设计高度一致。

### 为什么仍不用全局 MCP 作为默认

不是因为 MCP 不好，而是本项目当前痛点恰好是：

- custom model 的 built-in search 可用性变化；
- 想降低不使用 Exa 时的工具负担；
- 想让 Skill/CLI 可以按需披露；
- 想保留 Shell 这一最基础、跨模型的执行面。

新版采用 MCP 作为“无 Key 匿名 fallback transport”，但仍不把 MCP 注册给宿主；有 Key 时 REST 仍是主路径。MCP 复杂度被限制在 Python transport 层，并通过 session cache 避免每次 CLI 都重新 initialize。

## 5. OpenAI Codex Plugin

地址：https://github.com/openai/plugins

当前官方插件结构要求 `.codex-plugin/plugin.json`，并通过 marketplace 安装。官方仓库示例包含 `skills/`，因此本包将 `exa-retrieval` 包成 Codex Plugin。

同时保留 Direct，因为当前社区仍报告：

- 某些 Windows 版本本地/personal marketplace 发现异常；
- plugin list 与实际 cache payload/skill 暴露可能不一致；
- 安装后的现有线程不会自动重建 prompt。

所以 Plugin 是“更好的分发入口”，不是单点依赖。

## 6. 复用原则

1. 不复制第三方实现即可解决的问题，只引用/适配。
2. 不把第三方 API 的全部参数直接泄漏到 Skill。
3. Router 与 CLI contract 由本包控制；底层 provider 实现可替换。
4. 新增能力必须有真实使用场景，否则继续放在 reference/未来扩展。
