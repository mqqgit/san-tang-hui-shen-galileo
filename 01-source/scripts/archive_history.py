# -*- coding: utf-8 -*-
"""
盯盘历史按月滚动归档：避免 stock_recommendations.md 无限膨胀抬高 token 消耗。
由「历史归档」自动化在每月 1 日 08:00 调用。

策略（清晰、可预测、不破坏结构与参考表）：
  1) 仅当主文件体积超过阈值（默认 30KB，约两周数据）才归档，避免重复轮转；
  2) 将整份当前主文件移动为 archive/stock_recommendations_archive_YYYY-MM.md；
  3) 依 portfolio.json 重新生成主文件：标准头 + 当前「实盘持仓档案表」(始终与 portfolio.json 同步)
     + 「上月末快照」(取旧文件末尾约 8KB，在条目边界处截断，保证跨月复盘有上下文)。
退出码：0（无论是否实际归档均成功；缺失/未超限视为正常）。
"""
import json
import os
import sys
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = os.path.join(BASE, "portfolio.json")
HIST = (r"<MARVIS_BASE_DIR>"
        r"\oAN1i2f4EBT8lINh1ZKte-wdB3h4\workspace\<CONV_ID>"
        r"\output\stock_recommendations.md")
ARCHIVE_DIR = os.path.join(os.path.dirname(HIST), "archive")
THRESHOLD = 30 * 1024     # 30KB
TAIL_KEEP = 8 * 1024      # 保留旧文件末尾约 8KB 作为上月末快照


def gen_holdings_table(cfg):
    rows = ["## 实盘持仓档案表（截至 %s，由 portfolio.json 生成）" % cfg.get("updated_at", ""),
            "",
            "| 代码 | 名称 | 股数 | 成本价 | 买入日 | 状态 |",
            "|---|---|---|---|---|---|"]
    for p in cfg.get("positions", []):
        rows.append("| %s | %s | %s | %.3f | %s | %s |" % (
            p.get("code"), p.get("name"), p.get("qty"),
            p.get("cost", 0), p.get("buy_date", ""), p.get("status")))
    for c in cfg.get("closed_positions", []):
        rows.append("| %s | %s | — | — | 清仓 %s | closed |" % (
            c.get("code"), c.get("name"), c.get("closed_date", "")))
    return "\n".join(rows)


def main():
    if not os.path.exists(HIST):
        print(json.dumps({"archived": 0, "reason": "history missing"}, ensure_ascii=False))
        return
    size = os.path.getsize(HIST)
    if size <= THRESHOLD:
        print(json.dumps({"archived": 0, "reason": "below threshold", "size": size},
                         ensure_ascii=False))
        return

    old = open(HIST, encoding="utf-8").read()
    now = datetime.datetime.now()
    ym = now.strftime("%Y-%m")
    prev_ym = (now.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")

    # 取旧文件末尾约 TAIL_KEEP 字节，截断到条目边界（最近的 '\n### ' 或 '\n---'）
    cut = max(0, len(old) - TAIL_KEEP)
    boundary = old.rfind("\n### ", cut)
    if boundary < 0:
        boundary = old.rfind("\n---", cut)
    if boundary < 0:
        boundary = cut
    tail = old[boundary:].lstrip("\n")

    # 加载 portfolio.json（缺失则给空表，不阻断归档）
    try:
        cfg = json.load(open(PORT, encoding="utf-8"))
    except Exception:
        cfg = {"updated_at": ym, "positions": [], "closed_positions": []}

    new_main = (
        "# 盯盘记录（%s）\n\n"
        "> 本文件由自动盯盘任务追加写入；历史按月归档至 archive/。\n"
        "> 持仓动态真相源为 portfolio.json，下表由脚本据其生成并保持一致。\n\n"
        "%s\n\n"
        "## 上月末快照（%s，完整记录见 archive/）\n\n"
        "%s\n"
    ) % (ym, gen_holdings_table(cfg), prev_ym, tail)

    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    arch_path = os.path.join(ARCHIVE_DIR, "stock_recommendations_archive_%s.md" % prev_ym)
    with open(arch_path, "w", encoding="utf-8") as f:
        f.write(old)
    open(HIST, "w", encoding="utf-8").write(new_main)

    print(json.dumps({"archived": len(old), "archive": arch_path,
                      "new_main": len(new_main)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
