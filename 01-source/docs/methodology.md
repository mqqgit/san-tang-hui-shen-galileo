# 盯盘方法论（统一分析框架）v1

本文件是三个定时盯盘任务（早盘 / 午盘 / 尾盘）共享的**静态方法论**。
持仓、资金等动态数据**不在此处**，统一取自 `portfolio.json`。

- 改「分析维度 / 判断标准 / 输出格式」→ 改本文件（ rare ）。
- 改「持仓 / 资金」→ 只改 `portfolio.json`，**无需改动任何自动化任务提示词**，也不消耗重写 prompt 的 token。

---

## 0. 数据源
- 持仓 / 资金：`portfolio.json`（绝对路径由自动化提示词指定）。
  - 运行时读取，取 `positions` 中 `status:"holding"` 的全部标的参与盯盘；
  - `closed_positions` 仅作历史参考，不再分析。
- 历史与复盘：`stock_recommendations.md`（追加写，保留既有模板）。

## 1. 交易日判断
先用通用方法确认当日是否为 A 股交易日（周末 / 法定节假日休市）。
若休市，直接输出「今日休市，无需操作」并结束，不拉数据、不复盘。

## 2. 全市场扫描（荐股用）
- 数据：用 `westockdata` / `ths-advanced-analysis` 拉主要指数、行业 / 概念板块涨幅榜与主力资金流；用 `web_search` 抓当日财经快讯。
- 早盘：结合集合竞价 9:25 开盘价强弱研判当日主线。
- 午盘：复核早盘主线是否延续 / 切换。
- 尾盘：验证盘中主线，并为次日预案做准备。

## 3. 专家团配置
- 早盘：加载 `workbuddy-expert-bridge`，启用 `trading-agent` + `a-share-analysis` 两组会审。
- 午盘 / 尾盘：三组独立会审后联合决策——
  - 第一组 `trading-agent`（12 角色：技术面 / 基本面 / 新闻面 / 情绪面采集 → 多空辩论 → 交易决策 → 三方风险评估 → 报告）
  - 第二组 `a-share-analysis`（A 股研究团队）
  - 第三组 `stock-partner-team`（腾讯自选股投研专家团，投研主编圆汇众主持；成员：产业策略师星望远、信号派首席洲四方、估值分析师文衡价、逆向投资人坤候底、财报研究员钊审财、短线冲浪手磊追浪）
- 每组独立输出《本组会审报告 + 当日操作决策（3 只推荐股 / 换股 + 持仓操作建议）》；三组联合开会汇总异同与分歧，输出《共同研究决定的操作策略》。

## 4. 个股推荐规范
- 数量：每次 3 只可买股。
- 每只必须含：推荐买入价区间、目标卖出价区间、建议持股时间、推荐逻辑与风险点。
- 约束：仅 A 股；排除创业板（300 / 301 开头）；过滤 ST / 亏损爆雷 / 高位天量股；每只给出明确风控线。

## 5. 持仓盯盘（统一维度 / 标准 / 格式）
对 `portfolio.json` 中每只 `status:"holding"` 的持仓，按**四段式**输出：
1. **持仓概况**（代码 / 名称 / 股数 / 成本 / 现价 / 盈亏%）
2. **诊断分析**（价格走势、持仓状态、风险与机会研判；拉取实时行情 / 技术指标 / 资金流 / 龙虎榜）
3. **明确结论**（六选一：继续持有 / 加仓 / 减仓 / 止损 / 止盈 / 清仓观望，并给出对应价位）
4. **后续操作策略**（持仓时间决策：持有多久、何时止盈、何时止损）

## 6. 红线与资金纪律（含买入价格闸门 price gate）
- 红线：禁止转入新资金。
- 资金上限（取自 `portfolio.json` 的 `account.available_funds`，**运行时动态读取，每次荐股必算**；**上限 = 当前可用资金余额本身，不再按 20%/40% 比例折算**）：
  - 单票首仓 ≤ 可用资金（全额，即当前可用资金余额）；
  - 加仓后单票合计投入 ≤ 可用资金（全额）；
  - 可买金额不足一手（100 股）则不买。
- **买入价格闸门（price gate）计算规则**（荐股结论中必须显式写出，且每只推荐股的「推荐买入价区间上限」不得突破）：
  - 单票首仓预算 `B = 可用资金（全额，即 portfolio.json 的 account.available_funds）`；
  - 最小交易单位 = 100 股（1 手）；
  - 价格闸门 `P_max = B ÷ 100`（四舍五入到分）——即在 P_max 以内，至少可买入 1 手且不突破可用资金上限；
  - 任一只推荐股的「推荐买入价区间上限」必须 ≤ P_max，否则下调价格或放弃该标的；
  - 实际可买手数 `N = floor(B ÷ (推荐价 × 100))`，投入金额 `= N × 推荐价 × 100`，且 ≤ B（即 ≤ 可用资金）。
- **当前示例**：可用资金 XXXX.XX → 单票首仓预算 XXXX.XX → 价格闸门 **XX.XX 元/股**（1 手）。（该值为动态值，随 portfolio.json 中可用资金变化自动重算，勿写死。）

## 7. 复盘与记录（增量报告机制，见 §9）
- **复盘输入**：用 `report_cli.py query --agent <早盘|午盘|尾盘> --limit 1` 读取上一次迭代记录，逐只复盘（是否触发买入、达成卖出、盈亏% 及原因）。
- **本次产出**：运行结束后**必须**调用 `report_cli.py add --agent <时段> --payload <本次payload>.json`，由脚本自动计算「相对上次的增量差异」并生成**仅含本次增量 + 核心结论**的当前报告（`reports/current_<时段>.md`）。各任务**只输出该当前报告**，严禁把历史完整报告一并附带。
- `stock_recommendations.md` 降为**人类可读的归档备份**（由 §9 脚本可选同步生成），不再是主数据源；历史权威源为 `reports/iterations_<时段>.jsonl`。
- 历史文件会随时间增长，由 `report_store` 自动轮转（单文件 > 2MB 或 > 2000 条移入 `archive/`），无需手动归档。

---

## 8. 调度与运维规范（无人值守）

本方案的全部定时任务统一登记在 WorkBuddy 定时任务系统中，由自动调度按周期触发，无需人工干预。

### 8.1 任务清单

| 任务 | 触发频率 / 时间 | 启动方式 | 超时限制 | 失败重试 | 日志 | 告警 |
|---|---|---|---|---|---|---|
| 盘前配置检查 | 每工作日 09:00 | 自动(cron) | 脚本≤60s | 不重试，失败即告警 | log_run | agent-mail |
| 荐股-早盘全市场会审 | 每工作日 09:25 | 自动(cron) | 单标的抓取≤90s | 瞬时失败重试2次/30s | log_run | agent-mail |
| 午盘会审盯盘 | 每工作日 12:05 | 自动(cron) | 单标的抓取≤90s | 瞬时失败重试2次/30s | log_run | agent-mail |
| 荐股-尾盘全市场会审 | 每工作日 14:25 | 自动(cron) | 单标的抓取≤90s | 瞬时失败重试2次/30s | log_run | agent-mail |
| 历史归档 | 每月 1 日 08:00 | 自动(cron) | 脚本≤120s | 不重试，失败即告警 | log_run | agent-mail |

> 说明：WorkBuddy 自动化 schema 无原生「超时/重试」字段，故超时与重试以**提示词约束 + 脚本级保护**实现（见 8.2）。

### 8.2 统一运维约束（各盯盘任务提示词内嵌，必须执行）

1. **超时**：单只标的行情/数据抓取单项 ≤ 90 秒；任一项超时则放弃该项、沿用上一次已知数据并记 warning，不中断整体运行。
2. **重试**：遇网络/超时等瞬时失败，最多重试 2 次、每次间隔约 30 秒；2 次仍失败则记 warning 继续，不中止运行。
3. **日志**：无论成功或异常，运行结束必须调用 `log_run.py` 写入 `monitor_log.jsonl` 与 `monitor_log.md`（参数：`--task <早盘|午盘|尾盘|盘前检查|历史归档> --status ok|warn|fail --msg "<摘要>" --holdings "<N只>"`）。
4. **告警**：发生**阻断性失败**（portfolio.json 无效/缺失、methodology.md 缺失、全部数据源不可用、无 holding 持仓）时，除记 fail 日志外，须通过已连接的 `agent-mail` 发送告警邮件至账户绑定邮箱，并在 `monitor_log.md` 置 [FAIL]；非阻断性 warning 仅记录，不邮件。

### 8.3 支撑脚本（位于 stock-monitor/）

- `log_run.py`：结构化运行日志写入器（人读 `monitor_log.md` + 机读 `monitor_log.jsonl`）。
- `validate_config.py`：盘前配置体检，输出 JSON（valid/errors/holding_count），退出码 0/1。
- `archive_history.py`：按月滚动归档——整份历史移入 `archive/stock_recommendations_archive_YYYY-MM.md`，主文件按 portfolio.json 重新生成「实盘持仓档案表」+「上月末快照」。
- `update_portfolio.py`：**手动**更新持仓/资金（买入/清仓/改资金），含备份与校验——不在定时任务中，交易发生后由人工调用。
- `sync_lean.py`：将 MARVIS 源 YAML 导出同步为精简版（仅在 methodology 变更时手动调用）。
- `report_store.py`：增量报告持久化与检索库（见 §9）。每次迭代写一条结构化记录到 `reports/iterations_<agent>.jsonl`，自动算增量差异，生成仅增量的当前报告，支持按 agent / 时间 / 关键字检索；会话中断重启后完整保留。
- `report_cli.py`：报告工具 CLI（`add` / `report` / `query` / `lessons` / `demo`）。

### 8.4 数据流向与漂移防护

```
portfolio.json ──(运行时读取)──> 三个盯盘任务 ──> stock_recommendations.md(追加)
      ▲                                  │
      │ update_portfolio.py(人工)          └─> monitor_log.jsonl / .md(日志)
methodology.md(分析框架，rare 变更)
```
- 持仓变动 = 只改 `portfolio.json`（或调用 `update_portfolio.py`），**绝不**重写任何自动化提示词，零 token 重写开销。
- MARVIS 源 `schedules/*.yaml` 与 WorkBuddy 自动化提示词保持一致，由 `sync_lean.py` 同步。

---

## 9. 增量报告机制（解决「报告越滚越长 + 会话中断丢上下文」）

### 9.1 问题
两个 AI agent 同时运行，每次生成新报告都把之前完整报告一并附带 → 整体过长、token 浪费、且历史散落在对话里，会话一断就丢。

### 9.2 方案
**分离「实时输出」与「历史存储」**：每次只输出增量，历史结构化落盘。

- **输出层（短）**：`reports/current_<agent>.md` —— 仅本次迭代的「增量差异 + 核心结论 + 决策 + 本次教训」，绝不重复历史全文。这是各任务实际发给用户的报告。
- **存储层（全）**：`reports/iterations_<agent>.jsonl` —— 每次迭代追加一条结构化记录（见 9.3），永不修改历史，天然防丢、可审计。
- **索引层（快）**：`reports/_idx_<agent>.json` —— 记录最新 id / 序号 / 时间，O(1) 取最新，断点续号。
- **经验层（跨 agent）**：`reports/lessons.jsonl` —— 所有 agent 的经验教训汇总，按 tag 检索。

### 9.3 数据结构（Schema）

迭代记录（一行一条 JSON，追加写入）：
```json
{
  "id": "a1b2c3...", "agent_id": "午盘", "session_id": "sess-xxx",
  "ts": "<TIMESTAMP>", "iteration_no": 17,
  "trigger": "scheduled|manual",
  "holdings_snapshot": [
    {"code":"600000","name":"示例银行","qty":100,"cost":X.XX,"price":X.XX,"float_pnl":"+X.X%"}
  ],
  "market_context": {"主线":"半导体/CPU","资金流":{}},
  "conclusions": [ {"code":"600036","action":"持有","reason":"面板涨价","target":"6.30"} ],
  "decisions":   [ {"code":"600000","decision":"减仓","note":"开板放量","price_levels":{"止损":5.96}} ],
  "diff_vs_prev": { "holdings_added":[], "holdings_removed":[], "holdings_changed":[],
                    "decisions_added":[], "decisions_changed":[], "conclusions_new":[] },
  "lessons": [ {"lesson":"开板放量即减仓","tag":"risk"} ],
  "summary": "一句话摘要", "extra": {}
}
```
经验教训（追加写入 `lessons.jsonl`）：`{"ts","agent_id","iteration_id","lesson","tag"}`。

### 9.4 保存策略
- **追加写 + 永不改历史**：每迭代一条，断点也可据 `iteration_no` 续号；会话中断后重新读取 `_idx_<agent>.json` 即恢复到最新状态。
- **按 agent 隔离文件**：两个 agent 各写各的 `iterations_<agent>.jsonl`，**零写冲突**；`lessons.jsonl` 为共享经验教训，用独占锁文件（`O_EXCL`）串行化写入，跨平台（Windows/Linux 均可用）。
- **原子写**：临时文件 + `os.replace`，避免中断产生半行损坏。
- **自动轮转**：单文件 > 2MB 或 > 2000 条时整份移入 `archive/iterations_<agent>_<date>.jsonl`，从 0 续写，不丢历史。
- **检索**：`report_cli.py query` 支持 `--agent / --since / --until / --keyword / --limit`，跨 agent 扫描所有 `iterations_*.jsonl`；`lessons` 子命令支持 `--tag / --keyword`。

### 9.5 三个盯盘任务如何调用（替代无限追加 stock_recommendations.md）
每次运行结束前，把本次分析按 9.3 的字段组装成 `payload.json`，执行：
```
python report_cli.py add --agent <早盘|午盘|尾盘> --payload payload.json
```
脚本会：① 追加迭代记录到 `iterations_<时段>.jsonl`；② 与上一次自动算增量差异；③ 生成 `current_<时段>.md`（仅增量）；④ 更新索引。
**任务输出 = 该 `current_<时段>.md` 的内容**，不再附带历史。复盘时 `report_cli.py query --agent <时段> --limit 1` 取上次即可。
