# -*- coding: utf-8 -*-
"""
report_store.py — 增量报告持久化与检索库（通用，按 agent 隔离）

解决两个问题：
  1) 每次报告只输出「当前迭代核心结论 + 相对上次的增量差异」，不再把历史完整报告一并附带。
  2) 历次分析过程 / 迭代记录 / 经验教训结构化落盘，会话中断或重启后完整保留且可检索。

==================== 数据结构（Schema）====================

迭代记录（追加写入 reports/iterations_<agent_id>.jsonl，一行一条 JSON）：
{
  "id":             "a1b2c3...",                 # uuid hex，全局唯一
  "agent_id":       "午盘",                        # 区分不同 AI agent / 任务
  "session_id":     "sess-xxxx",                  # 本次会话标识（中断重启后用于串联）
  "ts":             "<TIMESTAMP>",  # ISO8601 本地时区
  "iteration_no":   17,                            # 该 agent 自增序号（断点续号）
  "trigger":        "scheduled|manual",           # 触发方式
  "holdings_snapshot": [                            # 当前持仓快照（代码为键）
    {"code":"600000","name":"示例银行","qty":100,"cost":X.XX,"price":X.XX,"float_pnl":"+X.X%"}
  ],
  "market_context": {"主线":"半导体/CPU","板块涨幅":[...], "资金流":{...}},  # 自由结构
  "conclusions": [                                   # 本次荐股/结论
    {"code":"600036","action":"持有/买入","reason":"面板涨价","target":"6.30"}
  ],
  "decisions": [                                     # 本次持仓决策（代码为键）
    {"code":"600000","decision":"继续持有","note":"涨停不卖，开板减仓","price_levels":{"止损":5.96}}
  ],
  "diff_vs_prev": {                                  # 与上一次迭代的差异（自动算）
    "holdings_added":[...], "holdings_removed":[...], "holdings_changed":[...],
    "decisions_added":[...], "decisions_changed":[...], "conclusions_new":[...]
  },
  "lessons": [ {"lesson":"...","tag":"risk|timing|..."}, ... ],   # 本次经验教训
  "summary":        "一句话摘要",
  "extra":          {}                              # 任意附加字段
}

经验教训（追加写入 reports/lessons.jsonl，共享，跨 agent 检索）：
  {"ts":..., "agent_id":..., "iteration_id":..., "lesson":"...", "tag":"..."}

当前报告（覆盖写入 reports/current_<agent_id>.md）：
  仅含本次迭代的「增量差异 + 核心结论 + 决策 + 本次教训」，不重复历史。

索引（覆盖写入 reports/_idx_<agent_id>.json）：
  {"latest_id":..., "iteration_no":..., "ts":..., "count":...}  用于 O(1) 取最新。

==================== 保存策略 ================
- 追加写：每次迭代一条记录，永不修改历史 → 天然防丢失、可审计。
- 原子写：临时文件 + os.replace，避免中断产生半行损坏。
- 按 agent 隔离文件：两 agent 各写各的 iterations_<id>.jsonl，无写冲突。
- 共享 lessons 用「独占锁文件」(O_EXCL) 串行化，跨平台（Windows/Linux 均可用）。
- 轮转：单 agent 文件 > 2MB 或 > 2000 条时，整份移入 archive/iterations_<id>_<date>.jsonl，从 0 续写。
- 检索：query() 支持 agent/时间区间/标签/关键字/条数，跨 agent 扫描所有 iterations_*.jsonl。
"""

import os
import os.path as P
import json
import time
import uuid
import datetime
import glob

BASE_DIR = P.dirname(P.abspath(__file__))
REPORTS_DIR = P.join(BASE_DIR, "reports")
ARCHIVE_DIR = P.join(REPORTS_DIR, "archive")
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

def _lessons_file():
    return P.join(REPORTS_DIR, "lessons.jsonl")


ROTATE_MAX_BYTES = 2 * 1024 * 1024   # 2 MB
ROTATE_MAX_LINES = 2000


# ------------------------- 工具：时区、路径、原子/锁 -------------------------
def _now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()


def _safe(name):
    return "".join(c for c in name if c.isalnum() or c in "-_")


def _iter_file(agent_id):
    return P.join(REPORTS_DIR, f"iterations_{_safe(agent_id)}.jsonl")


def _current_file(agent_id):
    return P.join(REPORTS_DIR, f"current_{_safe(agent_id)}.md")


def _idx_file(agent_id):
    return P.join(REPORTS_DIR, f"_idx_{_safe(agent_id)}.json")


def _atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def _atomic_append_jsonl(path, record):
    """追加一行 JSON；对共享文件用独占锁串行化，单 agent 文件直接追加。"""
    line = json.dumps(record, ensure_ascii=False)
    shared = (path == _lessons_file())
    if shared:
        lock = path + ".lock"
        deadline = time.time() + 10
        while True:
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.close(fd)
                break
            except FileExistsError:
                if time.time() > deadline:
                    raise TimeoutError("lessons lock timeout")
                time.sleep(0.05)
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        finally:
            try:
                os.remove(lock)
            except OSError:
                pass
    else:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


# ------------------------- 读取 / 最新 -------------------------
def load_iterations(agent_id, limit=None):
    p = _iter_file(agent_id)
    if not P.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    if limit:
        out = out[-limit:]
    return out


def get_latest(agent_id):
    its = load_iterations(agent_id)
    return its[-1] if its else None


def get_index(agent_id):
    p = _idx_file(agent_id)
    if not P.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


# ------------------------- diff 计算 -------------------------
def _keymap(records, kf="code"):
    return {r.get(kf): r for r in records}


def compute_diff(prev, cur):
    diff = {
        "holdings_added": [], "holdings_removed": [], "holdings_changed": [],
        "decisions_added": [], "decisions_changed": [], "conclusions_new": [],
    }
    cs = cur.get("holdings_snapshot", []) or []
    cd = cur.get("decisions", []) or []
    cc = cur.get("conclusions", []) or []
    if not prev:
        diff["holdings_added"] = cs
        diff["decisions_added"] = cd
        diff["conclusions_new"] = cc
        return diff
    ph = _keymap(prev.get("holdings_snapshot", []) or [])
    ch = _keymap(cs)
    for code, r in ch.items():
        if code not in ph:
            diff["holdings_added"].append(r)
        elif r != ph[code]:
            diff["holdings_changed"].append({"code": code, "prev": ph[code], "cur": r})
    for code in ph:
        if code not in ch:
            diff["holdings_removed"].append(ph[code])
    pd = _keymap(prev.get("decisions", []) or [])
    for code, r in _keymap(cd).items():
        if code not in pd:
            diff["decisions_added"].append(r)
        elif r.get("decision") != pd[code].get("decision"):
            diff["decisions_changed"].append(
                {"code": code, "prev": pd[code].get("decision"), "cur": r.get("decision")})
    pc = {c.get("code") for c in (prev.get("conclusions", []) or [])}
    for r in cc:
        if r.get("code") not in pc:
            diff["conclusions_new"].append(r)
    return diff


# ------------------------- 写入迭代 -------------------------
def add_iteration(agent_id, session_id=None, trigger="manual",
                 holdings_snapshot=None, market_context=None,
                 conclusions=None, decisions=None, lessons=None,
                 summary=None, extra=None):
    prev = get_latest(agent_id)
    iteration_no = (prev["iteration_no"] + 1) if prev else 1
    cur_core = {
        "holdings_snapshot": holdings_snapshot or [],
        "decisions": decisions or [],
        "conclusions": conclusions or [],
    }
    rec = {
        "id": uuid.uuid4().hex,
        "agent_id": agent_id,
        "session_id": session_id,
        "ts": _now(),
        "iteration_no": iteration_no,
        "trigger": trigger,
        "holdings_snapshot": holdings_snapshot or [],
        "market_context": market_context or {},
        "conclusions": conclusions or [],
        "decisions": decisions or [],
        "diff_vs_prev": compute_diff(prev, cur_core),
        "lessons": lessons or [],
        "summary": summary or "",
        "extra": extra or {},
    }
    _atomic_append_jsonl(_iter_file(agent_id), rec)

    idx = {"latest_id": rec["id"], "iteration_no": iteration_no,
           "ts": rec["ts"], "count": iteration_no}
    _atomic_write(_idx_file(agent_id), json.dumps(idx, ensure_ascii=False, indent=2))

    if lessons:
        for l in lessons:
            _atomic_append_jsonl(_lessons_file(), {
                "ts": rec["ts"], "agent_id": agent_id, "iteration_id": rec["id"],
                "lesson": l.get("lesson") if isinstance(l, dict) else l,
                "tag": l.get("tag", "") if isinstance(l, dict) else "",
            })
    _maybe_rotate(agent_id)
    return rec


def _maybe_rotate(agent_id):
    p = _iter_file(agent_id)
    if not P.exists(p):
        return
    size = os.path.getsize(p)
    n = sum(1 for _ in open(p, encoding="utf-8"))
    if size < ROTATE_MAX_BYTES and n < ROTATE_MAX_LINES:
        return
    date = datetime.date.today().isoformat()
    dst = P.join(ARCHIVE_DIR, f"iterations_{_safe(agent_id)}_{date}.jsonl")
    # 避免同日重复轮转覆盖
    i = 1
    while P.exists(dst):
        dst = P.join(ARCHIVE_DIR, f"iterations_{_safe(agent_id)}_{date}_{i}.jsonl")
        i += 1
    os.replace(p, dst)


# ------------------------- 生成「仅增量」当前报告 -------------------------
def gen_current_report(agent_id, rec=None):
    if rec is None:
        rec = get_latest(agent_id)
    if not rec:
        text = f"# {agent_id} 当前报告\n\n（暂无迭代记录）\n"
        _atomic_write(_current_file(agent_id), text)
        return text

    d = rec["diff_vs_prev"]
    L = []
    L.append(f"# {agent_id} 迭代报告 #{rec['iteration_no']}  ({rec['ts']})")
    L.append(f"> 触发：{rec['trigger']}  | 会话：{rec['session_id'] or '-'}  | 摘要：{rec['summary'] or '-'}")
    L.append("")
    L.append("## 增量差异（相对上一次迭代，自动计算）")
    if d["holdings_added"]:
        L.append("- 新增持仓：" + ", ".join(f"{h['name']}({h['code']})" for h in d["holdings_added"]))
    if d["holdings_removed"]:
        L.append("- 移除/清仓：" + ", ".join(f"{h['name']}({h['code']})" for h in d["holdings_removed"]))
    if d["holdings_changed"]:
        L.append("- 持仓变动：" + "; ".join(f"{c['code']} 价格/状态变更" for c in d["holdings_changed"]))
    if d["decisions_added"]:
        L.append("- 新增决策：" + ", ".join(f"{x['code']}:{x['decision']}" for x in d["decisions_added"]))
    if d["decisions_changed"]:
        L.append("- 决策变更：" + "; ".join(f"{c['code']} {c['prev']}→{c['cur']}" for c in d["decisions_changed"]))
    if d["conclusions_new"]:
        L.append("- 新荐股/新结论：" + ", ".join(f"{c['code']}" for c in d["conclusions_new"]))
    if not any([d["holdings_added"], d["holdings_removed"], d["holdings_changed"],
                d["decisions_added"], d["decisions_changed"], d["conclusions_new"]]):
        L.append("- （相对上次无变化）")
    L.append("")
    L.append("## 当前核心结论（仅本次）")
    if rec["conclusions"]:
        for c in rec["conclusions"]:
            L.append(f"- {c.get('code','')} {c.get('action','')}：{c.get('reason','')}  目标:{c.get('target','')}")
    else:
        L.append("- （无）")
    L.append("")
    L.append("## 当前持仓决策（仅本次）")
    if rec["decisions"]:
        for x in rec["decisions"]:
            L.append(f"- {x.get('code','')} → {x.get('decision','')}  {x.get('note','')}")
    else:
        L.append("- （无）")
    L.append("")
    if rec["lessons"]:
        L.append("## 本次经验教训")
        for l in rec["lessons"]:
            txt = l["lesson"] if isinstance(l, dict) else l
            L.append(f"- {txt}")
        L.append("")
    L.append("---")
    L.append(f"完整历史与逐次迭代记录见 `reports/iterations_{_safe(agent_id)}.jsonl`（共 {rec['iteration_no']} 次）。"
             f"本报告仅含本次增量，不重复历史全文。")
    text = "\n".join(L) + "\n"
    _atomic_write(_current_file(agent_id), text)
    return text


# ------------------------- 检索 -------------------------
def query(agent_id=None, since=None, until=None, tag=None, keyword=None, limit=50):
    files = [_iter_file(agent_id)] if agent_id else sorted(glob.glob(P.join(REPORTS_DIR, "iterations_*.jsonl")))
    out = []
    for p in files:
        if not P.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if since and r["ts"] < since:
                    continue
                if until and r["ts"] > until:
                    continue
                if keyword and keyword not in json.dumps(r, ensure_ascii=False):
                    continue
                out.append(r)
    out.sort(key=lambda r: r["ts"])
    return out[-limit:] if limit else out


def query_lessons(tag=None, keyword=None, limit=50):
    if not P.exists(_lessons_file()):
        return []
    out = []
    with open(_lessons_file(), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if tag and r.get("tag") != tag:
                continue
            if keyword and keyword not in json.dumps(r, ensure_ascii=False):
                continue
            out.append(r)
    out.sort(key=lambda r: r["ts"])
    return out[-limit:] if limit else out


def add_lesson(agent_id, lesson, tag="", session_id=None):
    _atomic_append_jsonl(_lessons_file(), {
        "ts": _now(), "agent_id": agent_id, "iteration_id": "",
        "lesson": lesson, "tag": tag,
    })
    return True


if __name__ == "__main__":
    print("report_store loaded. functions: add_iteration, gen_current_report, query, add_lesson")
