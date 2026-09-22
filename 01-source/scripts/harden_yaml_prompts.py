# -*- coding: utf-8 -*-
"""为三个 MARVIS 源 YAML 的活跃 prompt 追加统一运维约束块（保留 executed_list 历史）。"""
import os

BASE = r"<MARVIS_USER_DIR>\schedules"

OPS = ("【运维约束·无人值守】每次运行无论成败必须执行："
       "①超时——单标的行情/数据抓取单项≤90秒，超时则放弃该项、沿用上一次已知数据并记warning，不中断整体；"
       "②重试——遇网络/超时等瞬时失败最多重试2次、间隔约30秒，仍失败则记warning继续，不中止运行；"
       "③日志——结束前调用 python "
       "./stock-monitor/log_run.py "
       "--task <TASK> --status ok|warn|fail --msg <一句话摘要> --holdings <N只>；"
       "④告警——若发生阻断性失败(portfolio.json无效/缺失、methodology.md缺失、全部数据源不可用、无holding持仓)，"
       "除记fail日志外须通过 agent-mail 发送告警邮件至账户绑定邮箱，并在 monitor_log.md 置[FAIL]；"
       "非阻断性warning仅记录不邮件。详见 methodology §8。")

for tid, task in [("9", "早盘"), ("10", "尾盘"), ("11", "午盘")]:
    p = os.path.join(BASE, "%s_1_0.yaml" % tid)
    lines = open(p, encoding="utf-8").read().split("\n")
    idx = next(i for i, l in enumerate(lines) if l.startswith("prompt: "))
    cur = lines[idx][len("prompt: "):]
    if "运维约束" in cur:
        print("TASK %s 已含运维约束，跳过" % tid)
        continue
    lines[idx] = "prompt: " + cur + OPS.replace("<TASK>", task)
    open(p, "w", encoding="utf-8").write("\n".join(lines))
    print("TASK %s 已追加运维约束，新长度=%d" % (tid, len(lines[idx])))
