"""发送前 DNS 预检（防御 163 硬退信风控）：扫描主表所有邮箱域名。
只隔离【明确不存在】的域（NXDOMAIN）；超时 / SERVFAIL / 其它解析异常一律放行（不确定=真实可能存在，不误杀客户）。
这样即使发送引擎的 nslookup 预检在某些环境失效，我们也已提前清掉确定不存在的域，绝不发往空域名。
运行：python growth/preflight_dns.py
"""
import csv, dns.resolver

fn = "prospects_email_ready.csv"
rows = list(csv.DictReader(open(fn, encoding="utf-8", errors="replace")))
cols = list(rows[0].keys())

def definite_nxdomain(d):
    """只有明确 NXDOMAIN 才返回 True；超时/servfail 等返回 False（放行）。"""
    for rtype in ("MX", "A"):
        try:
            dns.resolver.resolve(d, rtype, lifetime=5)
            return False  # 能解析，域名存在
        except dns.resolver.NXDOMAIN:
            return True   # 明确不存在
        except Exception:
            continue       # 超时/servfail/其它：不确定，继续试下一种记录
    return False  # 两种记录都异常（不确定），放行

seen = {}
blocked = 0
for r in rows:
    e = (r.get("email") or "").strip()
    if "@" not in e:
        continue
    d = e.split("@")[-1].strip().lower()
    if d in seen:
        bad = seen[d]
    else:
        bad = definite_nxdomain(d)
        seen[d] = bad
    if bad and (r.get("status") or "").strip() not in ("blocked", "replied", "deal", "unsub"):
        r["status"] = "blocked"
        r["last_error"] = "preflight:dns:nxdomain"
        blocked += 1

with open(fn, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
real = sum(1 for v in seen.values() if not v)
print("DNS 预检完成：隔离【明确不存在】域名 %d 个；保留 %d 个真实/不确定域名（不误杀）。" % (blocked, real))
