"""SantaClara Aegis 外联作战进度看板（war-room）。
计划：2026-08-05 起 18 个工作日发 500 首触（→2026-08-28），其后 15 天发 300 跟进。
本脚本算计划 vs 实际、真实客户池、每日配额、风控状态，输出文本 + HTML。
运行：python growth/war_room.py
"""
import csv, datetime, html, os

fn = "prospects_email_ready.csv"
rows = list(csv.DictReader(open(fn, encoding="utf-8-sig", errors="replace")))

PLAN_START = datetime.date(2026, 8, 5)
TODAY = datetime.date.today()
FT_TARGET = 500          # 首触目标（家）
FU_TARGET = 300          # 跟进目标（封 R2/R3）
FT_DAYS = 18             # 首触窗口（工作日）
REGION_CAP = {"mi": 16, "ca": 10, "sz": 4, "tx": 12}
DAILY_CAP = sum(REGION_CAP.values())  # 35

def reg_of(x):
    s = (x.get("city", "") or "") + " " + (x.get("cluster", "") or "") + " " + (x.get("region") or "")
    s = s.lower()
    if "深圳" in s or "sz" in s or "gba" in s: return "sz"
    if any(k in s for k in ["mi","michigan","troy","auburn","ann arbor","detroit","warren"]): return "mi"
    if any(k in s for k in ["tx","texas","austin","dallas","houston","san antonio"]): return "tx"
    if any(k in s for k in ["ca","california","silicon","palo alto","sunnyvale","santa clara","san fran","berkeley","oakland"]): return "ca"
    return "?"

# 真实客户池：有邮箱、未被隔离、非 parked
def is_real(r):
    return bool((r.get("email") or "").strip()) and (r.get("status") or "").strip() not in ("blocked","parked","replied","deal","unsub")

real_pool = [r for r in rows if is_real(r)]
pool_by_reg = {}
for r in real_pool:
    pool_by_reg[reg_of(r)] = pool_by_reg.get(reg_of(r), 0) + 1

# 已发统计
ever_sent = [r for r in rows if (r.get("last_sent") or "").strip()]
distinct_sent = len(set((r.get("company") or "").strip().lower() for r in ever_sent if (r.get("company") or "").strip()))
follow_sent = sum(1 for r in rows if int(r.get("round") or 0) >= 2 and (r.get("last_sent") or "").strip())
pending_ft = [r for r in rows if int(r.get("round") or 0) == 0 and is_real(r)]
blocked = sum(1 for r in rows if (r.get("status") or "").strip() == "blocked")

# 工作日计数
def biz_days(a, b):
    n = 0
    d = a
    while d <= b:
        if d.weekday() < 5:
            n += 1
        d += datetime.timedelta(days=1)
    return n

elapsed = biz_days(PLAN_START, TODAY)
plan_ft = min(FT_TARGET, round(FT_TARGET * elapsed / FT_DAYS))
gap_ft = max(0, plan_ft - distinct_sent)
remaining_days = max(0, FT_DAYS - elapsed)
needed_per_day = round(gap_ft / remaining_days) if remaining_days else 0

# 风控状态（最近 SMTP 发送错误；排除 focus: 分类标记等非发送错误）
recent_err = {}
for r in ever_sent:
    e = (r.get("last_error") or "").strip()
    if e and not e.startswith("focus:") and "not_focus_fit" not in e:
        recent_err[e[:40]] = recent_err.get(e[:40], 0) + 1

def pct(a, b):
    return round(100.0 * a / b) if b else 0

lines = []
lines.append("=== SantaClara Aegis 外联作战看板 %s ===" % TODAY.isoformat())
lines.append("计划起点 2026-08-05 | 首触目标 %d 家 / %d 工作日(→%s) | 跟进目标 %d 封" % (FT_TARGET, FT_DAYS, (PLAN_START + datetime.timedelta(days=FT_DAYS*7//5)).isoformat(), FU_TARGET))
lines.append("--- 进度 ---")
lines.append("已过工作日: %d / %d | 剩余 %d 工作日" % (elapsed, FT_DAYS, remaining_days))
lines.append("首触: 计划应发 %d 家 | 实际已触达 %d 家 | 缺口 %d 家 | 需 %d 家/工作日补足" % (plan_ft, distinct_sent, gap_ft, needed_per_day))
lines.append("跟进(R2/R3): 已发 %d / %d 封" % (follow_sent, FU_TARGET))
lines.append("--- 真实客户池（可发）---")
lines.append("总计 %d 家 | 按区域 %s" % (len(real_pool), dict(pool_by_reg)))
lines.append("待发首触 %d 家 | 已隔离(blocked) %d 家" % (len(pending_ft), blocked))
lines.append("--- 每日配额（工作日）---")
lines.append("MI %d / TX %d / CA %d / SZ %d = %d 封/天（全局硬上限 45 防 163 风控）" % (REGION_CAP["mi"], REGION_CAP["tx"], REGION_CAP["ca"], REGION_CAP["sz"], DAILY_CAP))
if needed_per_day > DAILY_CAP:
    lines.append("⚠️ 缺口 %d/工作日 超过正常配额 %d，需靠缺失天数 2x 补发（已被全局 45 上限保护，顺延补齐）。" % (needed_per_day, DAILY_CAP))
lines.append("--- 风控状态 ---")
if recent_err:
    lines.append("最近发送错误样本: %s" % recent_err)
else:
    lines.append("无近期发送错误记录。")
lines.append("防御：DNS 预检隔离不存在域名 + 邮箱级硬退信自动隔离 + 163 日限额即停 + 每封 45~150s 真人节奏。")

report = "\n".join(lines)
print(report)

# HTML
def bar(a, b, color):
    w = pct(a, b)
    return '<div style="background:#eef2f7;border-radius:6px;height:14px;width:100%%;overflow:hidden"><div style="background:%s;height:100%%;width:%d%%"></div></div>' % (color, w)

html_doc = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>外联作战看板</title>
<style>body{font-family:-apple-system,Segoe UI,Roboto,'Microsoft YaHei',sans-serif;max-width:820px;margin:0 auto;padding:24px;background:#f7f9fc;color:#1a2233}
h1{font-size:22px;margin:0 0 2px}h2{font-size:15px;color:#667;font-weight:500;margin:0 0 16px}
.card{background:#fff;border:1px solid #e4e9f2;border-radius:12px;padding:16px 20px;margin:12px 0}
.kpis{display:flex;gap:12px;flex-wrap:wrap}.kpi{flex:1;min-width:120px;background:#fff;border:1px solid #e4e9f2;border-radius:12px;padding:14px}
.kpi .n{font-size:24px;font-weight:700;color:#0a6cff}.kpi .t{font-size:12px;color:#667;margin-top:2px}
.row{display:flex;justify-content:space-between;margin:8px 0;font-size:14px}.row b{color:#1a2233}
.warn{background:#fff7e6;border:1px solid #ffd591;border-radius:10px;padding:10px 14px;font-size:13px;color:#8a5a00}
.ok{color:#189a4a}.bad{color:#d4380d}</style></head><body>
<h1>SantaClara Aegis · 外联作战看板</h1><h2>%s · 计划 8/5 起 18 工作日 500 首触 + 300 跟进</h2>
<div class="kpis">
<div class="kpi"><div class="n">%d</div><div class="t">已触达公司 / 目标 500</div></div>
<div class="kpi"><div class="n">%d</div><div class="t">真实客户池（可发）</div></div>
<div class="kpi"><div class="n">%d</div><div class="t">待发首触</div></div>
<div class="kpi"><div class="n">%d</div><div class="t">跟进已发 / 300</div></div>
</div>
<div class="card"><div class="row"><b>首触进度</b><span>已 %d / 计划应 %d / 缺口 %d</span></div>%s
<div class="row" style="margin-top:6px"><span style="font-size:12px;color:#889">需 %d 家/工作日补足（剩余 %d 工作日）</span></div></div>
<div class="card"><div class="row"><b>真实客户池分区</b><span>MI %d · TX %d · CA %d · SZ %d</span></div>
<div class="row"><b>每日配额</b><span>MI%d+TX%d+CA%d+SZ%d = %d/天（全局硬上限 45 防 163 风控）</span></div>
<div class="row"><b>风控状态</b><span class="%s">%s</span></div></div>
<div class="warn">防御链：DNS 预检隔离不存在域名 · 邮箱级硬退信自动隔离 · 163 日限额即停 · 每封 45~150s 真人节奏 · 缺失天数自动 2x 补发（顺延不爆量）。所有客户均为官网真实抓取 + DNS 核验，绝不编造。</div>
<p style="color:#889;font-size:12px">源：prospects_email_ready.csv · 由 growth/war_room.py 生成</p></body></html>""" % (
    TODAY.isoformat(), distinct_sent, len(real_pool), len(pending_ft), follow_sent,
    distinct_sent, plan_ft, gap_ft, bar(distinct_sent, FT_TARGET, "#0a6cff"),
    needed_per_day, remaining_days,
    pool_by_reg.get("mi",0), pool_by_reg.get("tx",0), pool_by_reg.get("ca",0), pool_by_reg.get("sz",0),
    REGION_CAP["mi"], REGION_CAP["tx"], REGION_CAP["ca"], REGION_CAP["sz"], DAILY_CAP,
    "ok" if not recent_err else "bad", "无近期发送错误" if not recent_err else "有发送错误，见日志"
)
open("_war_room.html", "w", encoding="utf-8").write(html_doc)
print("\n[war_room] HTML 已写 _war_room.html")
