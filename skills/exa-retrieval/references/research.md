# Exa Agent 深度研究

> `research` 走 Exa Agent REST API，必须配置 `EXA_API_KEY`；匿名 Hosted MCP fallback 不覆盖该能力。

`research` 会创建 Exa Agent run。它相当于“Codex 再调用一个外部研究 Agent”，成本、延迟和可观测性都高于普通 Search，因此默认不披露、不默认调用。

## 优先级

项目已有 `web-searcher` 时：

- 普通多轮、多源 Web 调研：优先 `web-searcher`，利用子代理上下文隔离。
- 只有需要 Exa Agent 自己完成较强多步研究、结构化输出，或 `web-searcher`/Native 不适合时，才使用 `research`。

## 创建新 run

必须显式确认成本：

```bash
python "<skill-dir>/scripts/exa.py" research \
  "<research task>" \
  --effort low \
  --confirm-cost
```

可选：

```text
--effort minimal|low|medium|high|xhigh|auto|max
--system-prompt TEXT
--output-schema FILE.json
--previous-run-id ID
--budget USD              # 主要用于 Exa 支持预算的 effort
--beta TOKEN              # Exa-Beta header，可重复
--poll-interval SEC
--max-wait SEC
--json
```

## 查询已有 run

```bash
python "<skill-dir>/scripts/exa.py" research --run-id agent_run_xxx
```

如果等待时间达到 `--max-wait`，CLI 会返回当前状态和 `run_id`；远端 run 可能仍继续执行，可稍后用 `--run-id` 再查。

## 成本与停止

- 不要用 `research` 替代一次普通 `find`。
- 不要为了“更稳”无条件提升 effort。
- 得到足够证据后不再额外启动第二个 research run。
- API 返回 `costDollars` 时保留该字段，便于追踪成本。
