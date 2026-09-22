# WorkBuddy 定时自动化清单

> 本文件文档化 WorkBuddy「定时任务」模块中，与股票盯盘系统相关的 5 个自动化。
> 完整 prompt 不在 WorkBuddy 本地落盘，此处记录 ID、频率与提示词要点，便于跨环境恢复与对照。

## WorkBuddy 自动化
| 名称 | 自动化 ID | 频率 | 触发时间 | 提示词要点 |
|------|-----------|------|----------|------------|
| 早盘盯盘 | `3a8cffe7-8baf-42e4-bfda-6a0f3d17b8a0` | 每日 | 09:25 | 全市场扫描（集合竞价主线）+ 持仓四段式分析 + 追加 `stock_recommendations.md` |
| 午盘盯盘 | `68a373f2-6b76-47f2-9c7f-4709256d2bb4` | 每日 | 12:05 | 三组专家（trading-agent / a-share-analysis / stock-partner-team）独立会审 + 持仓决策 |
| 尾盘盯盘 | `1bf05f2e-3574-49ad-8635-34a8111d7810` | 每日 | 14:25 | 三组专家联合决策 + 次日预案 |
| 盘前配置检查 | `d7f5a4b0-9394-479a-b509-44ce0a6b64c0` | 每日 | 09:00 | 校验 `portfolio.json` / `methodology.md` 完整性，异常告警 |
| 历史归档 | `73ab11da` | 每月 1 日 | 08:00 | 归档 `stock_recommendations.md`（按月轮转） |

### 运维约束（三时段盯盘共用）
1. **超时**：单标的行情/数据抓取 ≤ 90 秒，超时放弃该项、沿用上一次已知数据并记 warning，不中断整体。
2. **重试**：网络/超时等瞬时失败最多重试 2 次、间隔约 30 秒，仍失败记 warning 继续，不中止。
3. **日志**：结束时调用 `log_run.py --task <时段> --status ok|warn|fail --msg <摘要> --holdings <N只>`。
4. **告警**：阻断性失败（portfolio.json 无效/缺失、methodology.md 缺失、全部数据源不可用、无 holding 持仓）除记 fail 外须经 agent-mail 发告警邮件并在 `monitor_log.md` 置 `[FAIL]`；非阻断性 warning 仅记录不邮件。

## Marvis 任务（对照）
| task_id | 标题 | 触发时间 | 状态 | 备份文件 |
|---------|------|----------|------|----------|
| 9  | 荐股-早盘全市场会审 | 09:25 | status:1（启用） | `marvis/9_1_0.yaml` |
| 10 | 荐股-尾盘全市场会审 | 14:25 | status:1（启用） | `marvis/10_1_0.yaml` |
| 11 | 午盘会审盯盘 | 12:05 | status:1（启用） | `marvis/11_1_1.yaml` |

> Marvis 三个 YAML 内含完整 prompt（含上述运维约束）与历史执行记录，已完整备份于 `02-task-definitions/marvis/`。
> 另有 1 个 PAUSED 的云端任务（生成昨日 AI 重点资讯总结）为只读、无法删除，未纳入备份。
