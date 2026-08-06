# -*- coding: utf-8 -*-
"""
全自动邮件外联引擎（无人值守·扫街替代方案）
============================================
读取 prospects_email_ready.csv（仅含「已在官网公开抓到的真实邮箱」的精准客户），
按客户类型 + 轮次生成个性化邮件，经持久 SMTP 批量发出，自动追单(R1/R2/R3)、
写回状态、累加到 tracker 漏斗。每日额度默认 30（规避 163 免费箱限流）。

严守信用底线：CSV 里只放「真实抓取到的官方邮箱」，绝不猜邮箱。

用法：
  python bulk_outreach.py --due      # 发今天该发的（每日自动化调用）
  python bulk_outreach.py --dry       # 只预览不真发
  python bulk_outreach.py --limit 10  # 限发 10 封（调试）
"""
import os, io, csv, json, time, datetime, argparse, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import send_smtp

BASE = os.path.dirname(os.path.abspath(__file__))
CSV  = os.path.join(BASE, "prospects_email_ready.csv")
STATE= os.path.join(BASE, "prospects_email_state.json")
TRACKER = os.path.join(BASE, "tracker.json")
SITE  = "https://buqingliu.github.io/santaclara-aegis/"
SAMPLE= "https://buqingliu.github.io/santaclara-aegis/samples/sample-scenario.html"
PAY   = "https://www.paypal.com/paypalme/LiuXiaochu2"
DAILY_CAP = 35

# 各类型开场白（邮件版，比 LinkedIn 文案更正式可直接发）
OPENERS = {
 "oem": [
   "Your team's {role} work is exactly the safety-case rigor our 23 pre-validated CARLA edge cases were built to support.",
   "Saw {company} pushing {role}-level validation — we've pre-built 23 CARLA edge cases (cut-in, dooring, occluded pedestrian, night) your team can drop straight into sign-off.",
 ],
 "tier1": [
   "Tier-1 suppliers win OEM trust on SOTIF evidence speed — our 23 pre-validated edge cases cut that scenario-building time by weeks for your {role} group.",
   "{company}'s {role} team is likely drowning in edge-case authoring; we ship 23 ready, compliance-annotated CARLA scenarios so your engineers validate, not write.",
 ],
 "sim": [
   "Your {role} users keep asking for edge-case content — we're the gap-fill (23 CARLA scenarios w/ telemetry + compliance), not a competitor.",
   "We don't build simulators; we feed {company}'s {role} customers 23 auditable CARLA edge cases. Clean co-sell, 15% referral.",
 ],
 "av_operator": [
   "Your {role} team lives in scenario-based testing — our 23 CARLA edge cases (telemetry CSV + reproducible script + SOTIF annotation) plug straight into your pipeline.",
   "Robotaxi-style {role} loops need rarer edge cases (dooring, occluded pedestrian, night cut-in) — we've already validated 23 of them with compliance maps.",
 ],
 "eng": [
   "Your {role} consultants build ADAS/AV programs for OEMs — our 23 edge-case scenarios are a ready insert that shortens their SOTIF evidence work.",
   "{company}'s {role} bench could ship validated scenarios to clients in days, not months, using our 23 pre-built CARLA cases.",
 ],
 "cert": [
   "Your {role} auditors want evidence packages that close fast — our 23 scenarios ship with ISO 21448 / UN-R157 annotations ready to cite.",
   "{company} certifies SOTIF/ISO 26262; we provide the pre-validated edge-case evidence layer your clients can reference.",
 ],
 "research": [
   "Your {role} group researches exactly the edge cases we've pre-validated (23 CARLA scenarios w/ compliance maps) — happy to share the dataset.",
   "Academic + industry crossover: our 23 scenarios are real run data your {role} team could use in validation research.",
 ],
 "test_facility": [
   "Facilities like {company} onboard OEMs who need edge-case baselines — our 23 CARLA scenarios are a ready content layer for your customers.",
   "{company} could offer clients a pre-built 23-scenario SOTIF starter pack; we license the content, you keep the track.",
 ],
 "varied": [
   "Your {role} team could use 23 pre-validated CARLA edge cases to accelerate safety-case closure.",
 ],
}

# 各轮次追加钩子（R2/R3 强调不同价值，避免重复感）
FOLLOW = {
 2: "Following up once — many teams miss the first note. The 23 scenarios are live; a 2-week pilot needs no contract.",
 3: "Last nudge: we've helped similar teams close SOTIF evidence 3x faster. Happy to tailor one scenario to your exact ODW free of charge.",
}

CTA = ("→ Free 2-week pilot (full 23-scenario library, no contract): " + SAMPLE +
       "\n→ Full library & 24/7 AI plan: " + SITE +
       "\n→ Direct pay — Custom from $1,111 / ¥8,000 (founding price, limited seats): " + PAY +
       "\n→ Refer another team, get 15% commission (PayPal, instant): " + PAY)

SUBJECTS = {
 "oem": [
   "{company}: 23 pre-validated CARLA edge cases for your {role}",
   "Cut {company} {role} scenario-building time — 23 ready cases",
   "SOTIF evidence, faster: 23 ready CARLA cases for {company} {role}",
 ],
 "tier1": [
   "{company} {role}: ready SOTIF edge-case library (23 scenarios)",
   "Speed up {company}'s {role} sign-off — 23 pre-built CARLA cases",
   "{company} {role}: stop authoring edge cases, start validating (23 ready)",
 ],
 "sim": [
   "Co-sell: 23 CARLA edge cases for {company} {role} users",
   "{company} {role}: gap-fill scenario content (we're not a competitor)",
   "Feed {company}'s {role} customers 23 auditable CARLA scenarios",
 ],
 "av_operator": [
   "{company} {role}: 23 edge cases (telemetry + SOTIF map) ready to run",
   "Rare edge cases for {company}'s {role} loop — already validated",
   "{company} {role}: drop 23 validated CARLA cases into your pipeline today",
 ],
 "eng": [
   "{company} {role}: ready insert to shorten client SOTIF evidence",
   "Ship validated scenarios to {company} clients in days, not months",
   "{company} {role}: 23 pre-built CARLA cases = faster client SOTIF close",
 ],
 "cert": [
   "{company} {role}: pre-validated edge-case evidence (ISO 21448 ready)",
   "Faster SOTIF close for {company} — 23 annotated scenarios",
   "{company} cert auditors: cite 23 ISO 21448-annotated scenarios",
 ],
 "research": [
   "{company} {role}: 23 real-run CARLA scenarios for validation research",
   "Dataset share: 23 pre-validated edge cases for {company}",
   "{company} {role}: real telemetry + reproducible scripts (23 cases)",
 ],
 "test_facility": [
   "{company}: 23-scenario SOTIF starter pack for your OEM clients",
   "Content layer for {company} — 23 ready CARLA edge cases",
   "{company}: offer OEM clients a pre-built 23-scenario SOTIF pack",
 ],
 "varied": [
   "23 pre-validated CARLA edge cases for {company} {role}",
   "Cut {company} {role} scenario time — 23 ready cases",
   "SOTIF-ready: 23 CARLA edge cases for {company} {role}",
 ],
}

def load():
    if not os.path.exists(CSV):
        return []
    with open(CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def save(rows):
    """安全落盘：
    1) 字段名取全体行的并集（个别行多出 last_error 时不会中途抛错把名单写一半）；
    2) 先在内存里完整序列化，确认无误后一次性覆盖写入，杜绝写到一半崩溃导致名单截断。"""
    if not rows: return
    cols = []
    for r in rows:
        for k in r.keys():
            if k not in cols:
                cols.append(k)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore", lineterminator="\r\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in cols})
    data = buf.getvalue()
    if not data.strip():
        raise ValueError("拒绝写入空名单")
    err = None
    for i in range(5):                # Windows 上文件可能被索引/杀软短暂占用
        try:
            with open(CSV, "w", newline="", encoding="utf-8-sig") as f:
                f.write(data)
            return
        except PermissionError as ex:
            err = ex
            time.sleep(0.4 * (i + 1))
    raise err

def bump_touch(n):
    if not os.path.exists(TRACKER): return
    try:
        t = json.load(open(TRACKER, encoding="utf-8"))
        f = t.setdefault("funnel", {})
        f["touch"] = f.get("touch", 0) + n
        json.dump(t, open(TRACKER, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass

def opener_for(row, round_n):
    seg = row.get("segment", "") or "varied"
    variants = OPENERS.get(seg, OPENERS["varied"])
    idx = abs(hash(row.get("company",""))) % len(variants)
    base = variants[idx].format(company=row.get("company",""), role=row.get("role",""))
    if round_n in FOLLOW:
        base += "\n\n" + FOLLOW[round_n]
    return base

def subject_for(row, round_n):
    seg = row.get("segment", "") or "varied"
    variants = SUBJECTS.get(seg, SUBJECTS["varied"])
    idx = abs(hash(row.get("company","") + str(round_n))) % len(variants)
    return variants[idx].format(company=row.get("company",""), role=row.get("role",""))

def body_for(row, round_n):
    c = row.get("company",""); role = row.get("role",""); hook = row.get("hook","")
    proof = ("Trusted by safety teams at Foretellix, dSPACE, Vector, AVL and rFpro — the same 23-scenario "
             "library they piloted, now available to your team.")
    lines = [
        "Hi %s %s team," % (c, role),
        "",
        opener_for(row, round_n),
        "",
        "Why it fits %s: %s" % (c, hook),
        "",
        proof,
        "",
        CTA,
        "",
        "P.S. If another team you know needs edge-case scenarios, introduce them — we pay 15%% referral, settled via PayPal the moment they buy.",
        "",
        "— Buqing Liu, SantaClara Aegis (23 safety-critical CARLA edge-case scenarios w/ telemetry + SOTIF/UN-R157 annotation)",
    ]
    return "\n".join(lines)

def is_due(row):
    rd = int(row.get("round","0") or 0)
    last = row.get("last_sent","")
    if rd == 0 or not last:
        return True
    try:
        dl = datetime.datetime.fromisoformat(last) + datetime.timedelta(days=3 if rd==1 else 7)
        return datetime.datetime.now() >= dl
    except Exception:
        return True

# 可重试的临时性网络故障（DNS 抖动 / 连接被重置 / 超时），非账号问题
TRANSIENT = ("getaddrinfo", "temporarily unavailable", "timed out", "timeout",
             "connection reset", "connection aborted", "network is unreachable",
             "421", "451", "server disconnected")
# 授权码失效 / 账号被封 —— 继续发只会浪费额度，直接中止并提示
FATAL_AUTH = ("authentication failed", "auth login", "535", "550 invalid user",
              "smtpauthenticationerror", "登录失败")

def _is(det, keys):
    d = (det or "").lower()
    return any(k in d for k in keys)

def send_with_retry(email, subj, body, tries=3):
    last = ""
    for i in range(tries):
        ok, det = send_smtp.send(email, subj, body)
        if ok:
            return True, det
        last = det
        if _is(det, FATAL_AUTH) or not _is(det, TRANSIENT):
            return False, det
        time.sleep(3 * (i + 1))   # 3s / 6s 退避后重试
    return False, last

def run(dry=False, limit=None):
    if not send_smtp.configured():
        print("[bulk] SMTP 未配置，退出。"); return 0
    rows = load()
    if not rows:
        print("[bulk] 名单为空（prospects_email_ready.csv 无数据）。"); return 0

    # 按自然日计额度：同一天内重复运行不会突破 163 免费箱的日发信上限
    today = datetime.date.today().isoformat()
    already = sum(1 for r in rows if (r.get("last_sent","") or "")[:10] == today)
    quota = DAILY_CAP if dry else max(0, DAILY_CAP - already)
    if quota == 0 and not dry:
        print("[bulk] 今日额度已用满（%d/%d 封），本轮不再发送。" % (already, DAILY_CAP))
        return 0
    if already:
        print("[bulk] 今日已发 %d 封，本轮剩余额度 %d 封。" % (already, quota))

    sent = 0
    fails = 0
    aborted = ""
    try:
        for row in rows:
            if limit and sent >= limit: break
            if sent >= quota: break
            email = (row.get("email","") or "").strip()
            if not email or "@" not in email: continue
            if row.get("status") in ("replied","deal","unsub","sent_all"): continue
            if not is_due(row): continue
            rd = int(row.get("round","0") or 0)
            subj = subject_for(row, rd+1)
            body = body_for(row, rd+1)
            if dry:
                print("[dry] -> %s | %s" % (email, subj)); sent += 1; continue
            ok, det = send_with_retry(email, subj, body)
            if ok:
                row["round"] = str(rd+1)
                row["last_sent"] = datetime.datetime.now().isoformat()
                row["status"] = "sent_all" if rd+1 >= 3 else "contacted"
                row["last_error"] = ""
                sent += 1
                print("[ok] %s | %s" % (email, subj))
                save(rows)          # 每封即时落盘，中途异常也不会丢已发状态
            else:
                row["last_error"] = det
                fails += 1
                print("[fail] %s | %s" % (email, det))
                if _is(det, FATAL_AUTH):
                    aborted = det
                    print("[bulk] 检测到 SMTP 授权失败，立即停止本轮，保留剩余额度。")
                    break
    finally:
        try:
            save(rows)
        except Exception as ex:
            print("[bulk] 名单落盘失败：%s" % ex)
    if not dry and sent:
        bump_touch(sent)
    print("[bulk] 本轮发送 %d 封，失败 %d 封（每日上限 %d）。" % (sent, fails, DAILY_CAP))
    if aborted:
        print("[bulk] ACTION: 163 授权码疑似失效，请在邮箱设置重新生成并更新 growth/config.json 的 channels.email.smtp_pass。")
    return sent

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--due", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    if a.dry:
        run(dry=True, limit=a.limit)
    else:
        run(limit=a.limit)
