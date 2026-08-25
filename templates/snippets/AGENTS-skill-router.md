<!-- web-research-router:start -->
- 网页检索先按工作量分流：简单、低噪音检索由主代理完成；多轮、多源或高噪音调研派 `web-searcher`，只接收精炼结论和来源。主代理无原生网页检索时可用 `exa-retrieval`；原生可用时一般 Web/时效信息优先原生，语义/长尾/精确过滤可用 Exa。涉及版本敏感或不确定的第三方 Library/Framework/SDK/API/CLI 用法时，使用 `context7-tech-docs` 做技术事实校准；已有可靠同版本资料或无真实知识缺口时无需查询。路由不清、需要切换事实源或任务范围明显扩大时，加载 `web-research-router` Skill。
<!-- web-research-router:end -->
