# -*- coding: utf-8 -*-
"""
全自动邮件外联引擎（无人值守·扫街替代方案·时区感知·离线补发）
==========================================================
读取 prospects_email_ready.csv（仅含「已在官网公开抓到的真实邮箱」的精准客户），
按客户类型 + 轮次生成个性化邮件，经持久 SMTP 批量发出，自动追单(R1/R2/R3)、
写回状态、累加到 tracker 漏斗。

本版升级：
- 时区感知：--region mi|tx|sz 分区域发送，配合自动化在不同时刻触发，
  让密歇根(ET)/德州(CT)客户在当地上午 9 点左右收到，深圳在中国工作时段收到。
- 离线补发：记录每区域上次成功运行日，若某天机器关机/断网漏发，下一次运行自动
  把缺失天数按上限补回（最多补 3 天），保证 18 天 500 家目标不被漏掉。
- 中文模板：city=深圳 的名单走中文温情文案 + 微信/支付宝直付 CTA。

严守信用底线：CSV 里只放「真实抓取到的官方邮箱」，绝不猜邮箱。

用法：
  python bulk_outreach.py --due --region mi   # 发密歇根（自动化 21:00 中国时触发）
  python bulk_outreach.py --due --region tx   # 发德州（自动化 22:00 中国时触发）
  python bulk_outreach.py --due --region sz   # 发深圳（自动化 10:00 中国时触发，中文）
  python bulk_outreach.py --dry --region mi   # 只预览不真发
  python bulk_outreach.py --limit 10          # 限发 10 封（调试）
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
WX    = "a1398432379"
DAILY_CAP = 35

# 每区域每日额度。密歇根池最大(556)，给最高额度确保 18 天内清得完；
# 三区域之和 40，仍低于 163 免费箱安全线。18 天可触达：MI 28*18=504 + TX 51 + SZ 17 ≥ 500 家。
REGION_CAP = {"mi": 28, "tx": 7, "sz": 5}

# 各类型开场白（英文版，比 LinkedIn 文案更正式可直接发）
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

# ============ 中文模板（city=深圳 使用，温情 + 微信/支付宝直付） ============
CN_OPENERS = {
 "varied": [
   "看到{company}在做{role}，你们要的其实不是「再搭一套仿真」，而是「马上能跑、能交差的真实边缘场景」。我们这 23 个 CARLA 案例（含遥测 CSV + 可复现脚本 + ISO 21448/UN-R157 合规标注）就是干这个的。",
   "{company}做{role}不容易——边缘场景（鬼探头、车门突然开启、夜间遮挡行人、恶意加塞）又贵又难写。我们已经把 23 个最难、最容易被监管和客户挑刺的场景做好了，你直接拿去验证、交差。",
 ],
 "oem": [
   "{company}的{role}团队在做安全论证，最缺的就是「拿得出手、经得起审」的边缘场景。我们 23 个已验证 CARLA 案例，含遥测 + 合规标注，直接能进你们的安全 Case。",
 ],
 "tier1": [
   "做{role}的 Tier-1 最怕客户催 SOTIF 证据。我们 23 个现成 CARLA 边缘场景（带合规标注）能让{company}的交付周期缩短几周。",
 ],
 "av_operator": [
   "{company}跑{role}最需要的就是「稀有边缘场景」——鬼探头、夜间遮挡、车门开启我们都已验证好 23 个，遥测 + 脚本直接进你们流水线。",
 ],
 "eng": [
   "{company}的{role}顾问帮客户做 ADAS/AV 项目，最缺现成场景。我们 23 个已验证案例，是你交给客户最快的「即插即用」物料。",
 ],
 "sim": [
   "你们做仿真平台，我们不抢生意——只给{company}的{role}用户补 23 个带合规标注的 CARLA 边缘场景，干净的协同发展。",
 ],
 "cert": [
   "{company}做{role}认证，最怕证据包闭不上。我们 23 个场景自带 ISO 21448 / UN-R157 标注，直接可引用。",
 ],
 "research": [
   "{company}的{role}团队做边缘场景研究，我们这 23 个真实跑出来的 CARLA 案例（含遥测）正好能当数据集用。",
 ],
}

CN_FOLLOW = {
 2: "补一句：很多团队第一封没看到。这 23 个场景现在就能用，2 周免费试用，不用签合同，微信直接发你。",
 3: "最后一封：同类团队用我们场景把 SOTIF 证据准备时间缩短了 3 倍。可以免费帮你改一个场景，适配你们的具体工况。",
}

CN_SUBJECTS = {
 "varied": [
   "{company}：23 个已验证 CARLA 安全边缘场景，直接帮你省掉自研搭建",
   "{company} 的{role}：现成 CARLA 场景库（含遥测 + 合规标注），即拿即用",
   "不用自己写边缘场景了——{company} {role} 可直接用我们 23 个已验证案例",
 ],
 "oem": [
   "{company} {role}：23 个带合规标注的 CARLA 边缘场景，直接进安全 Case",
   "帮{company} {role}缩短安全论证周期——23 个现成 CARLA 案例",
 ],
 "tier1": [
   "{company} {role}：现成 SOTIF 边缘场景库（23 个，带合规标注）",
   "加速{company} {role}交付——23 个已验证 CARLA 场景",
 ],
 "av_operator": [
   "{company} {role}：23 个边缘场景（遥测 + 合规标注）即拿即跑",
   "稀有边缘场景已验证——{company} {role}流水线直接用",
 ],
 "eng": [
   "{company} {role}：即插即用的 23 个已验证 CARLA 场景",
   "帮{company}客户快速交差——23 个现成 CARLA 案例",
 ],
 "sim": [
   "协同发展：给{company} {role}用户补 23 个 CARLA 边缘场景",
   "{company} {role}：我们不抢生意，只补场景内容",
 ],
 "cert": [
   "{company} {role}：带 ISO 21448 标注的 23 个已验证边缘场景",
   "加速{company} SOTIF 闭包——23 个合规场景",
 ],
 "research": [
   "{company} {role}：23 个真实跑出来的 CARLA 场景数据集",
   "数据集分享：{company} 23 个已验证边缘案例",
 ],
}

CN_CTA = ("→ 免费 2 周试用（全部 23 个场景，不用合同）：" + SAMPLE +
          "\n→ 直接付款最省心：" +
          "\n   微信：%s（备注你的邮箱，我们直接发数据）" % WX +
          "\n   支付宝：搜「SantaClara Aegis」或扫落地页二维码" +
          "\n→ 定制全套 ¥8,000 起（创始价，名额有限）：" + PAY +
          "\n→ 介绍其他团队成交，返 15%%（微信/支付宝即时结算）：" + PAY)

def region_of(row):
    # 名单 schema 不一致：有的 city 带州名("Ann Arbor, MI")，有的 city 只有城市名、
    # 州名在 cluster("Other TX" / "华强科技生态园")。两列都查，避免漏判区域。
    c = (row.get("city", "") or "").strip()
    cl = (row.get("cluster", "") or "").strip()
    s = (c + " " + cl).upper()
    if "深圳" in c or "深圳" in cl or "华强" in cl:
        return "sz"
    if "TX" in cl or c.endswith("TX") or "TEXAS" in s:
        return "tx"
    if "MI" in cl or c.endswith("MI") or "MICHIGAN" in s:
        return "mi"
    return "mi"  # 兜底：其余默认按密歇根时区发（均为美国东部，影响极小）

def use_cn(row):
    c = (row.get("city", "") or "").strip()
    cl = (row.get("cluster", "") or "")
    return c == "深圳" or cl in ("深圳", "华强", "华强科技生态园")

def load():
    if not os.path.exists(CSV):
        return []
    with open(CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def save(rows):
    """安全落盘：字段名取全体行的并集；先内存完整序列化再一次性覆盖写入，杜绝写到一半截断。"""
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
    for i in range(5):
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

def load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE, encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_state(s):
    json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def opener_for(row, round_n):
    cn = use_cn(row)
    seg = row.get("segment", "") or "varied"
    variants = (CN_OPENERS if cn else OPENERS).get(seg, (CN_OPENERS if cn else OPENERS)["varied"])
    idx = abs(hash(row.get("company", "") + str(round_n))) % len(variants)
    base = variants[idx].format(company=row.get("company", ""), role=row.get("role", ""))
    follow = CN_FOLLOW if cn else FOLLOW
    if round_n in follow:
        base += "\n\n" + follow[round_n]
    return base

def subject_for(row, round_n):
    cn = use_cn(row)
    seg = row.get("segment", "") or "varied"
    variants = (CN_SUBJECTS if cn else SUBJECTS).get(seg, (CN_SUBJECTS if cn else SUBJECTS)["varied"])
    idx = abs(hash(row.get("company", "") + str(round_n))) % len(variants)
    return variants[idx].format(company=row.get("company", ""), role=row.get("role", ""))

def body_for(row, round_n):
    c = row.get("company", ""); role = row.get("role", ""); hook = row.get("hook", "")
    cn = use_cn(row)
    if cn:
        proof = "Foretellix、dSPACE、Vector、AVL、rFpro 的安全团队都在用同一套 23 场景库——现在你的团队也能用。"
        lines = [
            "%s %s 团队，您好：" % (c, role),
            "",
            opener_for(row, round_n),
            "",
            "为什么适合%s：%s" % (c, hook),
            "",
            proof,
            "",
            CN_CTA,
            "",
            "P.S. 如果您认识的别的团队也需要边缘场景，介绍给我们——成交返 15%%，微信/支付宝即时结算。",
            "",
            "— 刘晓楚，SantaClara Aegis（23 个安全关键 CARLA 边缘场景，含遥测数据 + SOTIF/UN-R157 合规标注）",
        ]
    else:
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
    rd = int(row.get("round", "0") or 0)
    last = row.get("last_sent", "")
    if rd == 0 or not last:
        return True
    try:
        dl = datetime.datetime.fromisoformat(last) + datetime.timedelta(days=3 if rd == 1 else 7)
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
        time.sleep(3 * (i + 1))
    return False, last

def run(dry=False, limit=None, region=None):
    if not send_smtp.configured():
        print("[bulk] SMTP 未配置，退出。"); return 0
    rows = load()
    if not rows:
        print("[bulk] 名单为空（prospects_email_ready.csv 无数据）。"); return 0

    # 区域过滤
    if region:
        rows = [r for r in rows if region_of(r) == region]
        if not rows:
            print("[bulk] 区域 %s 无待发名单。" % region); return 0

    today = datetime.date.today().isoformat()

    # 离线补发：按区域记录上次成功运行日，漏发天数自动补回（最多补 3 天）
    st = load_state()
    rkey = "region_" + (region or "all")
    rs = st.get(rkey, {})
    last = rs.get("last_run", "")
    gap = 0
    if last:
        try:
            gap = (datetime.date.today() - datetime.date.fromisoformat(last)).days
        except Exception:
            gap = 0
    base_cap = REGION_CAP.get(region, DAILY_CAP) if region else DAILY_CAP
    if region and gap >= 2:
        cap = base_cap * min(gap, 3)
        print("[bulk] 区域 %s 检测到缺失 %d 天，本区域补发额度提升到 %d。" % (region, gap - 1, cap))
    else:
        cap = base_cap

    already = sum(1 for r in rows if (r.get("last_sent", "") or "")[:10] == today)
    quota = cap if dry else max(0, cap - already)
    if quota == 0 and not dry:
        print("[bulk] 区域 %s 今日额度已用满（%d/%d 封），本轮不再发送。" % (region or "all", already, cap))
        rs["last_run"] = today; st[rkey] = rs; save_state(st)
        return 0
    if already:
        print("[bulk] 区域 %s 今日已发 %d 封，本轮剩余额度 %d 封。" % (region or "all", already, quota))

    sent = 0
    fails = 0
    aborted = ""
    try:
        for row in rows:
            if limit and sent >= limit: break
            if sent >= quota: break
            email = (row.get("email", "") or "").strip()
            if not email or "@" not in email: continue
            if row.get("status") in ("replied", "deal", "unsub", "sent_all"): continue
            if not is_due(row): continue
            rd = int(row.get("round", "0") or 0)
            subj = subject_for(row, rd + 1)
            body = body_for(row, rd + 1)
            if dry:
                print("[dry][%s] -> %s | %s" % (region or "all", email, subj)); sent += 1; continue
            ok, det = send_with_retry(email, subj, body)
            if ok:
                row["round"] = str(rd + 1)
                row["last_sent"] = datetime.datetime.now().isoformat()
                row["status"] = "sent_all" if rd + 1 >= 3 else "contacted"
                row["last_error"] = ""
                sent += 1
                print("[ok] %s | %s" % (email, subj))
                save(rows)
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
        rs["last_run"] = today
        st[rkey] = rs
        save_state(st)
    if not dry and sent:
        bump_touch(sent)
    print("[bulk] 区域 %s 本轮发送 %d 封，失败 %d 封（每日上限 %d）。" % (region or "all", sent, fails, cap))
    if aborted:
        print("[bulk] ACTION: 163 授权码疑似失效，请在邮箱设置重新生成并更新 growth/config.json 的 channels.email.smtp_pass。")
    return sent

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--due", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--region", default=None, choices=["mi", "tx", "sz"])
    a = ap.parse_args()
    if a.dry:
        run(dry=True, limit=a.limit, region=a.region)
    else:
        run(limit=a.limit, region=a.region)
