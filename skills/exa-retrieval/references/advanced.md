# Exa 高级检索

仅在基础 `find/read` 无法表达需求时读取。

## 用法

```bash
python "<skill-dir>/scripts/exa.py" advanced "<query>" [options]
```

常用选项：

```text
-n, --limit N
--type instant|fast|auto|deep-lite|deep|deep-reasoning
--category company|publication|news|pdf|github|personal site|people|financial report
--include-domain DOMAIN      # 可重复
--exclude-domain DOMAIN      # 可重复
--after YYYY-MM-DD           # published date
--before YYYY-MM-DD
--location US                # ISO 两字母国家码
--content highlights|text|summary|none
--fresh-hours N              # Exa contents.maxAgeHours
--additional-query QUERY     # deep variants，可重复
--allow-deep                 # deep* 必须显式给出
--json
```

## 选择原则

- 默认仍用 `type=auto`；低延迟才用 `fast/instant`。
- `deep-lite/deep/deep-reasoning` 可能更慢、更贵；必须显式 `--allow-deep`。
- domain/date/category 有明确过滤需求时才用 Advanced；不要因为它“参数多”就默认使用。
- `company` 和 `people` category 不支持 published-date 与 exclude-domain 组合；CLI 会提前拒绝。
- `additional-query` 只适用于 deep variants。
- 优先 highlights；只有确实需要长正文时才用 text，再自行控制上下文。

## Query 写法

Exa 偏语义检索。描述“想找到什么样的页面/资料”，而不是只堆关键词或复杂 Boolean。时间敏感任务应明确日期范围；找 GitHub 时可用 `--include-domain github.com`。

## 停止规则

首选 query 获得足够高质量来源后停止。只有结果明显不足时再：

1. 改写语义角度；
2. 加精确 filter；
3. 必要时切另一个后端。

不要自动把同一个问题在 Native 和 Exa 上各跑一遍。


## Transport 说明

- `EXA_TRANSPORT=auto`：有 `EXA_API_KEY` 时优先 REST；无 Key 时 `auto/fast/instant` + 常规过滤走 Hosted MCP。若 REST 返回官方 402 credits/budget 耗尽 tag，支持的 advanced 调用会临时切匿名 MCP，并在默认 1 小时后 probe REST 自动恢复。若显式 `EXA_TRANSPORT=mcp` 且存在 Key，Key 会通过 `x-api-key` header 发送，不放入 URL。
- `deep-lite` / `deep` / `deep-reasoning` 只走 REST，需要 `EXA_API_KEY` 与显式 `--allow-deep`。`--content none` 也要求 REST，因为当前 Hosted MCP advanced tool 会返回正文内容，无法保持 `none` 的稳定语义。
- Hosted MCP 不会注册到宿主；Python CLI 内部通过 MCP `2025-11-25` 调用并复用本地 session cache。
- 不要为了“可能更强”无目的使用 deep；先用基础 find 或常规 advanced。
