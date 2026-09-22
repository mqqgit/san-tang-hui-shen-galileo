#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_portfolio.py - 盯盘持仓配置安全更新器（单一数据源）
----------------------------------------------------------------------
本脚本是修改持仓 / 资金的唯一入口。运行后只改 portfolio.json，
三个自动化任务提示词保持不变，因此不产生「重写 prompt」的 token 开销。

用法示例：
  python update_portfolio.py buy  --code 600036 --name 示例股份甲 --qty 100 --cost X.XX [--date <DATE>]
  python update_portfolio.py sell --code 600009 [--date <DATE>] [--note 清仓，不再跟踪]
  python update_portfolio.py funds --available XXXX.XX [--total 5255.13]
  python update_portfolio.py show

特性：
  - 自动备份（portfolio.json.bak_YYYYMMDD_HHMMSS）
  - 买入时若曾在 closed_positions，自动移回活跃持仓
  - 卖出时从活跃持仓移至 closed_positions
  - 数值 / 必填字段校验
"""
import argparse
import datetime
import json
import os
import shutil
import sys

CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portfolio.json")


def load():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def save(data, backup=True):
    if backup:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(CONFIG, CONFIG + f".bak_{ts}")
    data["updated_at"] = datetime.date.today().isoformat()
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def today():
    return datetime.date.today().isoformat()


def _find_active(data, code):
    for i, p in enumerate(data["positions"]):
        if p["code"] == code:
            return i
    return -1


def cmd_buy(args):
    if args.qty <= 0:
        sys.exit("错误：股数必须 > 0")
    if args.cost <= 0:
        sys.exit("错误：成本必须 > 0")
    d = load()
    code = args.code
    # 若曾清仓，移回活跃
    d["closed_positions"] = [c for c in d["closed_positions"] if c["code"] != code]
    idx = _find_active(d, code)
    rec = {"code": code, "name": args.name, "qty": args.qty,
           "cost": args.cost, "buy_date": args.date or today(), "status": "holding"}
    if idx >= 0:
        d["positions"][idx].update(rec)
        print(f"更新活跃持仓: {code} {args.name} {args.qty}股 成本{args.cost} ({rec['buy_date']})")
    else:
        d["positions"].append(rec)
        print(f"新增活跃持仓: {code} {args.name} {args.qty}股 成本{args.cost} ({rec['buy_date']})")
    save(d)


def cmd_sell(args):
    d = load()
    idx = _find_active(d, args.code)
    if idx < 0:
        sys.exit(f"错误：未找到活跃持仓 {args.code}，无法卖出")
    rec = d["positions"].pop(idx)
    rec["status"] = "closed"
    rec["closed_date"] = args.date or today()
    rec["note"] = args.note or "清仓，不再跟踪"
    d["closed_positions"].append(rec)
    print(f"清仓: {args.code} {rec['name']} @ {rec['closed_date']} | {rec['note']}")
    save(d)


def cmd_funds(args):
    d = load()
    if args.available is not None:
        if args.available < 0:
            sys.exit("错误：可用资金不能为负")
        d["account"]["available_funds"] = args.available
    if args.total is not None:
        if args.total < 0:
            sys.exit("错误：总资产不能为负")
        d["account"]["total_assets"] = args.total
    print(f"资金更新: 可用={d['account']['available_funds']}  总资产={d['account'].get('total_assets')}")
    save(d)


def cmd_show(args):
    d = load()
    print(json.dumps(d, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description="盯盘持仓配置更新器（单一数据源）")
    sub = ap.add_subparsers(dest="cmd")

    b = sub.add_parser("buy", help="买入或更新一只活跃持仓")
    b.add_argument("--code", required=True, help="股票代码，如 600036")
    b.add_argument("--name", required=True, help="股票名称，如 示例股份甲")
    b.add_argument("--qty", type=int, required=True, help="股数（100 的整数倍）")
    b.add_argument("--cost", type=float, required=True, help="买入成本价")
    b.add_argument("--date", help="买入日期 YYYY-MM-DD，缺省为今天")

    s = sub.add_parser("sell", help="清仓一只活跃持仓")
    s.add_argument("--code", required=True)
    s.add_argument("--date")
    s.add_argument("--note")

    f = sub.add_parser("funds", help="更新账户资金")
    f.add_argument("--available", type=float, help="可用资金")
    f.add_argument("--total", type=float, help="总资产")

    sub.add_parser("show", help="打印当前配置")

    args = ap.parse_args()
    if args.cmd == "buy":
        cmd_buy(args)
    elif args.cmd == "sell":
        cmd_sell(args)
    elif args.cmd == "funds":
        cmd_funds(args)
    elif args.cmd == "show":
        cmd_show(args)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
