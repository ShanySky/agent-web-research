<!-- web-research-router:start -->
- 网页检索先按工作量路由：简单、低噪音检索由主代理完成；多轮、多源或高噪音调研交给 `web-searcher`，只返回精炼结论和来源。主代理自行检索时，一般 Web/时效信息优先原生检索；原生不可用或偏语义、长尾技术资料、精确过滤检索时使用 `exa-retrieval`；结果明显不足才跨后端补查。边界与 fallback 规则见 `{{RULE_PATH}}`。
<!-- web-research-router:end -->
