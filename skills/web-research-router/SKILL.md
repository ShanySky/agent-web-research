---
name: web-research-router
description: 用于处理 Web Research 的路由歧义：判断由主代理还是专用研究代理执行，并在主代理自行检索时选择 Native Web Search、Exa，或在版本敏感的开发文档/API 用法问题上转交 Context7。仅在路由不明确、需要 fallback、或研究范围明显扩大时加载；普通且路径明确的简单检索无需加载。
---

# Web Research 路由

仅在常规 Web Research 路径不明确、需要回退，或任务规模扩大到需要重新判断执行方式时使用本 Skill。它主要解决两个问题：**谁来搜**，以及主代理自行检索时**用哪个后端/事实源**。

## 1. 先决定由谁执行

**主代理自行检索**：适合单点事实、单份文档、少量 issue/release、少量来源即可确认的低噪音任务，且结果需要直接参与当前推理。

**专用 Web Research 代理**：当任务需要多轮或多角度查询、多源交叉核验、较多网页阅读、社群/benchmark/竞品调查，或原始搜索结果会明显污染主上下文时使用。要求其返回精炼结论、关键证据、来源链接、时间信息、不确定项，以及实际使用的检索后端。

不要仅因为主代理缺少 Native Web Search 就派子代理；**执行者选择首先看工作量和噪音**。

## 2. 主代理自行检索时再选事实源

- **Context7**：当前/指定版本的 Library、Framework、SDK、API、CLI、Configuration、Migration、deprecated/replaced API 与官方开发文档用法。决定使用后加载 `context7-tech-docs` Skill。
- **Native Web Search**：可用时，一般 Web 事实、最新信息、网页浏览/导航及宿主原生页面交互默认优先。
- **Exa**：Native 不可用；或任务偏语义/概念发现、长尾技术/开发者资料、GitHub/论文发现、严格 domain/date/category 过滤；也可在 Native 合理尝试后结果明显不足时补查。

一个简单边界：**“这个技术在当前/指定版本应该怎么正确使用？”优先 Context7；“外界最近关于这个技术发生了什么？”优先 Native / Exa / GitHub 等开放互联网路径。**

决定使用 Exa 后，再加载 `exa-retrieval` Skill。高级过滤和 Exa Agent 研究能力只在确实需要时按需展开。

Context7 也可以由编码任务直接触发，不要求先进入本 Router：当 Agent 准备依据记忆编写版本敏感的第三方 API/配置，但存在真实不确定时，应直接使用 `context7-tech-docs` 做技术事实校准。

## 3. 回退与停止

首选路径获得足够证据后立即停止。只有结果明显不足时才切换事实源；不要为了“更稳”无目的多路重复查询。

Context7 找不到 Library、对应版本缺失、结果不足或 CLI/服务失败时，可以回退官方文档、GitHub、Native Web Search 或 Exa；不要让 Context7 成为单点依赖。若最终证据仍不足，明确说明未确认的部分。
