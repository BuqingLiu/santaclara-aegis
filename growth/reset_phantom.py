"""一次性修复：把'幽灵已触达'行（round>=1 但无 last_sent）重置为真正的首触（round=0）。
这些行从没真正发出去，却占着 R2/R3 跟进额度、歪曲 500 家首触计数。重置后它们回归首触池。
不动：有 last_sent 的真已发、replied/deal/unsub 等终态行。
"""
import csv

fn = "prospects_email_ready.csv"
rows = list(csv.DictReader(open(fn, encoding="utf-8", errors="replace")))
cols = list(rows[0].keys())
n = 0
for r in rows:
    has_sent = (r.get("last_sent") or "").strip()
    rd = int(r.get("round") or 0)
    st = (r.get("status") or "").strip()
    if rd >= 1 and not has_sent and st not in ("replied", "deal", "unsub"):
        r["round"] = "0"
        if st in ("contacted", "sent_all"):
            r["status"] = "pending"
        n += 1
with open(fn, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
print("重置幽灵已触达行 -> round=0：", n, "行")
