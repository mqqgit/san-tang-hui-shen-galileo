# -*- coding: utf-8 -*-
"""
盯盘运行日志写入器：统一记录每次自动任务的执行结果，支持无人值守审计。

用法：
  python log_run.py --task 早盘 --status ok   --msg "完成，4只持仓已分析" --holdings "4只"
  python log_run.py --task 午盘 --status warn --msg "示例股份甲行情超时，沿用上次数据" --holdings "4只"
  python log_run.py --task 尾盘 --status fail --msg "portfolio.json 解析失败" --alert

参数：
  --task      任务名（早盘/午盘/尾盘/盘前检查/历史归档）
  --status    ok | warn | fail
  --msg       一句话摘要
  --holdings  持仓数量描述（可选）
  --alert     显式置为告警（fail 时默认即为告警）

输出：
  - monitor_log.jsonl : 机器可读，每行一条 JSON，便于后续统计分析
  - monitor_log.md    : 人读时间线，每次运行追加一行
"""
import argparse
import json
import os
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
JSONL = os.path.join(BASE, "monitor_log.jsonl")
MD = os.path.join(BASE, "monitor_log.md")

TAG = {"ok": "[OK]", "warn": "[WARN]", "fail": "[FAIL]"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--status", required=True, choices=["ok", "warn", "fail"])
    ap.add_argument("--msg", default="")
    ap.add_argument("--holdings", default="")
    ap.add_argument("--alert", action="store_true")
    args = ap.parse_args()

    now = datetime.datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    is_alert = bool(args.alert) or (args.status == "fail")
    rec = {
        "ts": ts,
        "task": args.task,
        "status": args.status,
        "holdings": args.holdings,
        "msg": args.msg,
        "alert": is_alert,
    }

    with open(JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    line = "- `%s` %s **%s** [%s] 持仓:%s %s\n" % (
        ts, TAG[args.status], args.task, args.status,
        args.holdings or "—", args.msg,
    )
    with open(MD, "a", encoding="utf-8") as f:
        f.write(line)

    print("LOGGED " + json.dumps(rec, ensure_ascii=False))


if __name__ == "__main__":
    main()
