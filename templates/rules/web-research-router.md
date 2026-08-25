# Web Research 路由规则

目标：让 Web Research 的执行与事实源选择稳定、可预测、易排错。先决定**谁来搜**，再决定主代理自行检索时**用什么事实源**。

## 1. 先决定执行者

**主代理自行检索**：单点事实、文档、issue、release 等低噪音任务；通常少量查询与来源即可确认，结果需要直接参与当前推理。

**派 `web-searcher`**：需要多轮/多角度查询、多源交叉核验、较多网页阅读、社群/benchmark/竞品调查，或原始搜索结果会明显污染主上下文。只接收其精炼结论、关键证据、来源、时间信息与实际使用的检索后端。

不要仅因为主代理缺少 Native Web Search 就派子代理；先按任务规模和噪音决定执行者。

## 2. 主代理自行检索时再选事实源

- **Context7**：当前/指定版本的 Library、Framework、SDK、API、CLI、Configuration、Migration、deprecated/replaced API 与官方开发文档用法。需要时使用 `context7-tech-docs` Skill。
- **Native Web Search**：可用时，一般 Web、最新事实、网页浏览/导航默认优先。
- **Exa Retrieval**：Native 不可用；或偏语义/概念发现、长尾技术资料、GitHub/论文/开发者资料发现、严格 domain/date/category 过滤；也可作为 Native 合理尝试后结果明显不足时的补查。

简单边界：**“这个技术在当前/指定版本应该怎么正确使用？”优先 Context7；“外界最近关于这个技术发生了什么？”优先开放互联网检索。**

Context7 也可由编码任务直接触发：准备依据记忆编写版本敏感的第三方 API/配置，但存在真实不确定时，不必先加载本 Router，直接使用 `context7-tech-docs` 校准技术事实。

## 3. 回退与停止

首选事实源获得足够证据即停止，不要无目的重复查询。Context7 找不到 Library、版本缺失、结果不足或 CLI/服务失败时，可回退官方文档、GitHub、Native Web Search 或 Exa。若最终证据仍不足，明确说明未确认部分。
