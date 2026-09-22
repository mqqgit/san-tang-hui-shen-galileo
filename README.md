# 三堂会审伽利略（公开子集）

> A股自动盯盘系统的**开源框架子集**。本仓库仅包含可公开的工具代码与分析框架，
> **不包含任何真实持仓、成本价、资金、券商或执行日志**（这些保留在私有的本地完整备份中）。

## 这是什么
一套面向 A 股的个人盯盘自动化方案，由三个时段（早盘 / 午盘 / 尾盘）的定时任务驱动，
配合 Marvis（长期 cron 任务）与 WorkBuddy（定时自动化）两类调度器，实现：
- **配置驱动**：单一数据源 `portfolio.json`，改一处即可同步所有任务，零 token 重写；
- **增量报告**：每次运行只输出当前迭代的核心结论与增量差异，历史结构化持久化（`report_store.py` / `report_cli.py`）；
- **无人值守运维约束**：超时、重试、执行日志、阻断性失败邮件告警。

## 目录结构
```
01-source/
  scripts/        工具脚本（见下）
  docs/
    methodology.md   分析方法论、价格闸门公式、运维规范、增量报告规范（示例数字已脱敏）
  config/
    payload_example.json  report_cli.py 的示例载荷（脱敏）
02-task-definitions/
  workbuddy-automations.md  WorkBuddy 五个定时自动化的 ID / 频率 / 提示词要点（路径已脱敏）
```

## 脚本说明
| 脚本 | 用途 |
|------|------|
| `update_portfolio.py` | 更新 `portfolio.json` 持仓 / 资金（单一数据源） |
| `validate_config.py` | 校验 `portfolio.json` 合法性（阻断性失败检测） |
| `log_run.py` | 每次任务结束写入执行日志（ok / warn / fail） |
| `report_store.py` | 增量报告持久化（按 agent 隔离、原子写、轮转） |
| `report_cli.py` | 增量报告命令行（add / report / query / lessons） |
| `sync_lean.py` | 将 Marvis 任务 YAML 改写为「配置驱动」精简 prompt |
| `harden_yaml_prompts.py` | Marvis YAML 提示词加固（注入运维约束） |
| `archive_history.py` | 历史归档（按月轮转荐股历史文件） |

> 注：`append_snapshot.py` 为一次性真实快照脚本（含真实数据），未纳入本公开仓库。

## 如何使用
1. 准备你自己的 `portfolio.json`（持仓 / 可用资金 / 红线），替换示例。
2. 将 `01-source/scripts` 与 `methodology.md` 接入你自己的调度器（Marvis / WorkBuddy / crontab 等）。
3. 脚本中的 `<MARVIS_USER_DIR>`、`./stock-monitor` 等路径占位符需按你的环境替换。

## 安全说明
本仓库所有示例数据（股票名称、代码、成本价、价格、金额、日期）均已替换为 `<DATE>` / `X.XX` / `示例*` 等占位符，
不包含任何真实个人账户信息。真实执行数据与私有备份请自行保管，勿提交到公开仓库。
