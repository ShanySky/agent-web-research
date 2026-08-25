<!-- web-research-router:start -->
- 网页检索采用两层路由：先判断执行者。单点事实/文档/issue 等通常少量来源即可确认、预期噪音低的检索由主代理完成；需要多轮查询、多源交叉核验、较多网页阅读或可能产生大量噪音时，派 `web-searcher`，只接收精炼结论、关键证据、来源和时间信息。主代理自行检索时再选事实源：当前/指定版本的 Library/Framework/SDK/API/CLI、配置、迁移或 deprecated API 用法优先 `context7-tech-docs`；一般 Web、最新事实与网页浏览在原生检索可用时优先原生能力；原生不可用，或偏语义/概念发现、长尾技术资料、GitHub/论文/开发者资料发现、精确域名/日期/类别过滤时，使用 `exa-retrieval`。Context7 或首选 Web 后端结果明显不足时才补查其他可靠来源，不要无目的重复查询。即使主代理没有原生检索，也不要仅因此派子代理。
<!-- web-research-router:end -->
