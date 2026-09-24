#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_lean.py - 将三个 MARVIS 任务 YAML 的活跃 prompt 改写为「配置驱动」精简版，
与 WorkBuddy 自动化提示词保持一致。持仓数据不再写死，改为运行时读取 portfolio.json。
仅替换首个 `prompt:` 行，executed_list 历史记录、status 等一律不动。
"""
import io
import shutil

BASE = r"<MARVIS_USER_DIR>\schedules"
M = "./stock-monitor/methodology.md"
P = "./stock-monitor/portfolio.json"
H = "<MARVIS_USER_DIR>/workspace/<CONV_ID>/output/stock_recommendations.md"

PROMPTS = {
    "9": (
        "盯盘任务-早盘(09:25)。步骤：(1)确认A股交易日，休市则输出'今日休市，无需操作'并结束；"
        f"(2)读取方法论 {M} 与持仓配置 {P}（取status=holding的全部持仓）；"
        "(3)按methodology第2-3节做早盘全市场扫描(集合竞价9:25主线)并启用trading-agent+a-share-analysis会审；"
        "(4)按methodology第4节荐3只可买股；(5)按methodology第5-6节对portfolio.json全部持仓做四段式盯盘分析；"
        f"(6)读取 {H} 复盘上批次并写经验总结；(7)按methodology第7节追加本批次推荐与持仓分析、更新持仓档案表。"
        "所有分析维度/标准/格式严格遵循methodology，持仓数据严格以portfolio.json为准。"
    ),
    "10": (
        "盯盘任务-尾盘(14:25)。步骤：(1)确认交易日，休市则结束；"
        f"(2)按methodology第2节更新当日指数/板块/资金流验证早盘主线；(3)按methodology第3节组织三组专家"
        "(trading-agent/a-share-analysis/stock-partner-team)独立会审并联合输出《共同研究决定的操作策略》"
        f"(3只可买股含买/卖价区间/持股时间/逻辑风险+全部持仓尾盘决策与次日预案)；(4)按methodology第5-6节对 {P} 全部持仓做四段式盯盘；"
        f"(5)读取 {H} 上批次复盘写经验总结，记录本批次、更新持仓档案表。约束见methodology第4/6节。"
    ),
    "11": (
        "盯盘任务-午盘(12:05)。步骤：(1)确认交易日，休市则结束；"
        f"(2)读取方法论 {M} 与持仓配置 {P}（status=holding）；"
        "(3)按methodology第3节加载三组专家(trading-agent/a-share-analysis/stock-partner-team)独立会审后联合决策，荐3只"
        "(排除创业板300/301，单票首仓<=可用资金（全额）)；(4)按methodology第5-6节对全部持仓做四段式盯盘，给出本时段操作与持仓时间决策；"
        f"(5)将持仓分析与三组推荐及联合决策对比，输出明确判断(持仓持有/止盈/止损卖出、是否买入推荐股)；"
        f"(6)读取 {H} 与上一次决策逐项复盘，追加本批推荐、更新持仓档案表。"
    ),
}

for tid, text in PROMPTS.items():
    p = f"{BASE}\\{tid}_1_0.yaml"
    raw = io.open(p, encoding="utf-8").read()
    L = raw.split("\n")
    shutil.copy2(p, p + ".bak_lean")
    replaced = False
    for i, x in enumerate(L):
        if x.startswith("prompt:") or x.startswith("prompt: "):
            old = x
            L[i] = "prompt: " + text
            print(f"[{tid}] 替换活跃prompt: {len(old)} -> {len(L[i])} 字符")
            replaced = True
            break
    if not replaced:
        print(f"[{tid}] 未找到 prompt: 行，跳过")
        continue
    io.open(p, "w", encoding="utf-8").write("\n".join(L))
    # 校验：活跃 prompt 不应再含写死持仓名
    ap = L[[j for j, x in enumerate(L) if x.startswith("prompt:")][0]]
    for name in ["示例股份甲", "示例股份乙", "示例银行", "示例传媒"]:
        if name in ap:
            print(f"  [警告 {tid}] 活跃prompt仍含写死持仓名: {name}")
print("done")
