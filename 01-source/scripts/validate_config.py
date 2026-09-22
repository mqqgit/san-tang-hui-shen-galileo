# -*- coding: utf-8 -*-
"""
盘前配置体检：校验盯盘所需的所有静态/动态数据源是否就绪。
由「盘前配置检查」自动化在工作日 09:00 调用，失败则触发告警。

校验项：
  1) portfolio.json 存在且为合法 JSON
  2) account.available_funds / total_assets 为数值
  3) 每个 position 字段完整（code/name/qty/cost/status），status 合法
  4) 至少存在 1 只 status=holding 的持仓（否则盯盘无标的）
  5) methodology.md 存在
  6) 历史文件 stock_recommendations.md 存在

退出码：0=通过，1=存在错误（供自动化判定是否告警）。
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = os.path.join(BASE, "portfolio.json")
METHOD = os.path.join(BASE, "methodology.md")
HIST = (r"<MARVIS_BASE_DIR>"
        r"\oAN1i2f4EBT8lINh1ZKte-wdB3h4\workspace\<CONV_ID>"
        r"\output\stock_recommendations.md")

errors = []

# 1) portfolio.json
if not os.path.exists(PORT):
    errors.append("portfolio.json 缺失")
    cfg = None
else:
    try:
        cfg = json.load(open(PORT, encoding="utf-8"))
    except Exception as e:
        errors.append("portfolio.json 解析失败: %s" % e)
        cfg = None

if cfg:
    acc = cfg.get("account", {})
    if not isinstance(acc.get("available_funds"), (int, float)):
        errors.append("account.available_funds 非数值")
    if not isinstance(acc.get("total_assets"), (int, float)):
        errors.append("account.total_assets 非数值")
    positions = cfg.get("positions", [])
    for i, p in enumerate(positions):
        for k in ("code", "name", "qty", "cost", "status"):
            if k not in p:
                errors.append("positions[%d] 缺字段 %s" % (i, k))
        if p.get("status") not in ("holding", "closed"):
            errors.append("positions[%d].status 非法: %s" % (i, p.get("status")))
    holding = [p for p in positions if p.get("status") == "holding"]
    if not holding:
        errors.append("无 holding 状态持仓，盯盘将无标的")

# 2) methodology.md
if not os.path.exists(METHOD):
    errors.append("methodology.md 缺失")

# 3) history
if not os.path.exists(HIST):
    errors.append("stock_recommendations.md 缺失")

holding_count = (len([p for p in (cfg or {}).get("positions", [])
                      if p.get("status") == "holding"]) if cfg else 0)

result = {
    "valid": len(errors) == 0,
    "errors": errors,
    "holding_count": holding_count,
    "checked_at": os.path.basename(PORT),
}
print(json.dumps(result, ensure_ascii=False))
sys.exit(0 if result["valid"] else 1)
