# -*- coding: utf-8 -*-
"""
report_cli.py — 增量报告工具命令行入口

子命令：
  add     按 agent 写入一次迭代（payload 来自 JSON 文件）
  report  打印某 agent 的「仅增量」当前报告（并落盘 current_<agent>.md）
  query   检索迭代记录（支持 --agent/--since/--until/--keyword/--limit）
  lessons 检索经验教训（--tag/--keyword）
  demo    用两个 agent 各两次迭代演示 delta-only 输出与跨 agent 检索

示例：
  python report_cli.py add --agent 午盘 --payload payload.json
  python report_cli.py report --agent 午盘
  python report_cli.py query --agent 午盘 --keyword 综艺
  python report_cli.py demo
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report_store as rs


def cmd_add(args):
    payload = json.load(open(args.payload, encoding="utf-8"))
    rec = rs.add_iteration(
        agent_id=args.agent,
        session_id=payload.get("session_id"),
        trigger=payload.get("trigger", "manual"),
        holdings_snapshot=payload.get("holdings_snapshot"),
        market_context=payload.get("market_context"),
        conclusions=payload.get("conclusions"),
        decisions=payload.get("decisions"),
        lessons=payload.get("lessons"),
        summary=payload.get("summary"),
        extra=payload.get("extra"),
    )
    text = rs.gen_current_report(args.agent, rec)
    print(f"[OK] agent={args.agent} 迭代 #{rec['iteration_no']} 已写入")
    print("---- 当前报告（仅增量） ----")
    print(text)


def cmd_report(args):
    text = rs.gen_current_report(args.agent)
    print(text)


def cmd_query(args):
    rows = rs.query(agent_id=args.agent, since=args.since, until=args.until,
                    keyword=args.keyword, limit=args.limit)
    print(f"命中 {len(rows)} 条迭代记录：")
    for r in rows:
        print(f"  #{r['iteration_no']:>3} [{r['agent_id']}] {r['ts']} | {r['summary'] or '-'}"
              f" | 增量: +{len(r['diff_vs_prev']['holdings_added'])}持仓"
              f" / {len(r['diff_vs_prev']['decisions_changed'])}决策变"
              f" / +{len(r['diff_vs_prev']['conclusions_new'])}新荐股")


def cmd_lessons(args):
    rows = rs.query_lessons(tag=args.tag, keyword=args.keyword, limit=args.limit)
    print(f"命中 {len(rows)} 条经验教训：")
    for r in rows:
        print(f"  [{r['agent_id']}] ({r.get('tag','')}) {r['ts']} :: {r['lesson']}")


def cmd_demo(args):
    import shutil
    # 用临时子目录演示，避免污染真实 reports/
    demo_dir = os.path.join(rs.REPORTS_DIR, "_demo")
    if os.path.exists(demo_dir):
        shutil.rmtree(demo_dir)
    os.makedirs(demo_dir)
    orig = rs.REPORTS_DIR
    rs.REPORTS_DIR = demo_dir
    rs.ARCHIVE_DIR = os.path.join(demo_dir, "archive")
    os.makedirs(rs.ARCHIVE_DIR, exist_ok=True)

    print("=== 模拟两个 AI agent 并发独立写入（各自文件，零冲突）===\n")
    # agent_A 第一次
    rs.add_iteration("agent_A", session_id="s1", trigger="scheduled",
        holdings_snapshot=[{"code":"600000","name":"示例银行","qty":100,"cost":X.XX,"price":X.XX,"float_pnl":"+X.X%"}],
        conclusions=[{"code":"600036","action":"持有","reason":"面板涨价","target":"6.30"}],
        decisions=[{"code":"600000","decision":"继续持有","note":"涨停不卖"}],
        lessons=[{"lesson":"一字涨停不急于卖，看开板量能","tag":"timing"}],
        summary="A首报：综艺持有，京东方观察")
    # agent_B 第一次（不同 agent，独立文件）
    rs.add_iteration("agent_B", session_id="s2", trigger="scheduled",
        holdings_snapshot=[{"code":"600016","name":"示例股份乙","qty":100,"cost":X.XX,"price":X.XX,"float_pnl":"-X.X%"}],
        conclusions=[{"code":"600016","action":"持有","reason":"面板双雄低位"}],
        decisions=[{"code":"600016","decision":"继续持有","note":"失守MA60减半"}],
        summary="B首报：TCL持有")
    # agent_A 第二次：综艺决策变 + 新荐股
    rs.add_iteration("agent_A", session_id="s1", trigger="scheduled",
        holdings_snapshot=[{"code":"600000","name":"示例银行","qty":100,"cost":X.XX,"price":X.XX,"float_pnl":"+X.X%"}],
        conclusions=[{"code":"600036","action":"持有","reason":"面板涨价","target":"6.30"},
                     {"code":"600584","action":"买入","reason":"半导体低位","target":"9.50"}],
        decisions=[{"code":"600000","decision":"减仓","note":"开板放量，部分止盈","price_levels":{"止损":5.96}}],
        lessons=[{"lesson":"开板放量即减仓，不贪","tag":"risk"}],
        summary="A次报：综艺转减仓，新增长电建议")
    # agent_B 第二次：清仓 TCL
    rs.add_iteration("agent_B", session_id="s2", trigger="manual",
        holdings_snapshot=[],
        conclusions=[],
        decisions=[],
        summary="B次报：TCL已清仓，无持仓")

    print("\n--- agent_A 当前报告（仅增量，不重复历史）---")
    print(rs.gen_current_report("agent_A"))
    print("--- agent_B 当前报告（仅增量）---")
    print(rs.gen_current_report("agent_B"))

    print("--- 跨 agent 检索（全部，按时间）---")
    for r in rs.query():
        print(f"  #{r['iteration_no']} [{r['agent_id']}] {r['ts']} | {r['summary']}")

    print("\n--- 检索经验教训（tag=risk）---")
    for r in rs.query_lessons(tag="risk"):
        print(f"  [{r['agent_id']}] {r['lesson']}")

    # 还原 + 清理演示目录
    rs.REPORTS_DIR = orig
    rs.ARCHIVE_DIR = os.path.join(orig, "archive")
    shutil.rmtree(demo_dir)
    print("\n[demo] 演示完成，临时目录已清理（真实 reports/ 未受影响）。")


def main():
    ap = argparse.ArgumentParser(description="增量报告持久化与检索工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add"); p.add_argument("--agent", required=True); p.add_argument("--payload", required=True); p.set_defaults(func=cmd_add)
    p = sub.add_parser("report"); p.add_argument("--agent", required=True); p.set_defaults(func=cmd_report)
    p = sub.add_parser("query"); p.add_argument("--agent"); p.add_argument("--since"); p.add_argument("--until"); p.add_argument("--keyword"); p.add_argument("--limit", type=int, default=50); p.set_defaults(func=cmd_query)
    p = sub.add_parser("lessons"); p.add_argument("--tag"); p.add_argument("--keyword"); p.add_argument("--limit", type=int, default=50); p.set_defaults(func=cmd_lessons)
    p = sub.add_parser("demo"); p.set_defaults(func=cmd_demo)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
