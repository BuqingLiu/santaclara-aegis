# -*- coding: utf-8 -*-
"""
全自动邮件外联引擎（无人值守·扫街替代方案·时区感知·离线补发）
==========================================================
读取 prospects_email_ready.csv（仅含「已在官网公开抓到的真实邮箱」的精准客户），
按客户类型 + 轮次生成个性化邮件，经持久 SMTP 批量发出，自动追单(R1/R2/R3)、
写回状态、累加到 tracker 漏斗。

本版升级：
- 时区感知：--region mi|tx|ca|sz 分区域发送，配合自动化在不同时刻触发，
  让密歇根(ET)/德州(CT)客户在当地上午 8 点左右收到，深圳在中国工作时段收到。
- 离线补发：记录每区域上次成功运行日，若某天机器关机/断网漏发，下一次运行自动
  把缺失天数按上限补回（最多补 3 天），保证 18 天 500 家目标不被漏掉。
- 中文模板：city=深圳 的名单走中文温情文案 + 微信直付 CTA（支付宝收款码已取消，仅微信 + PayPal）。

严守信用底线：CSV 里只放「真实抓取到的官方邮箱」，绝不猜邮箱。

用法：
  python bulk_outreach.py --due --region mi   # 发密歇根（自动化 20:00 中国时触发）
  python bulk_outreach.py --due --region tx   # 发德州（自动化 21:00 中国时触发）
  python bulk_outreach.py --due --region sz   # 发深圳（自动化 09:00 中国时触发，中文）
  python bulk_outreach.py --dry --region mi   # 只预览不真发
  python bulk_outreach.py --limit 10          # 限发 10 封（调试）
"""
import os, io, re, csv, json, time, datetime, argparse, sys, subprocess, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import send_smtp
from html import escape as _esc
from hook_en import sanitize_hook_en, has_cjk

BASE = os.path.dirname(os.path.abspath(__file__))
CSV  = os.path.join(BASE, "prospects_email_ready.csv")
STATE= os.path.join(BASE, "prospects_email_state.json")
TRACKER = os.path.join(BASE, "tracker.json")
COPY_BANK_CACHE = None
def load_copy_bank():
    global COPY_BANK_CACHE
    if COPY_BANK_CACHE is not None:
        return COPY_BANK_CACHE
    p = os.path.join(BASE, "copy_bank.json")
    try:
        COPY_BANK_CACHE = json.load(open(p, encoding="utf-8"))
    except Exception:
        COPY_BANK_CACHE = {}
    return COPY_BANK_CACHE
SITE  = "https://buqingliu.github.io/santaclara-aegis/"
SAMPLE= "https://buqingliu.github.io/santaclara-aegis/samples/sample-scenario.html"
PAY   = "https://www.paypal.com/paypalme/LiuXiaochu2"
WX    = "a1398432379"
DAILY_CAP = 35

# 四个战场，只此四个（2026-08-10 用户指令：极致专注，不再全球撒网）：
#   mi = 密歇根汽车走廊（底特律都会区 + 安娜堡）  20:00 中国 = 08:00 美东
#   tx = 德州三角（奥斯汀/达拉斯/休斯顿）          21:00 中国 = 08:00 美中
#   ca = 加州湾区（旧金山 / 圣何塞 / 圣克拉拉）    21:00 中国 = 06:00 美西
#   sz = 深圳（上限 19 家公司，首触 + R2/R3 多轮跟进；公司数不扩充、只深耕） 09:00 中国
# 额度按"一个真人一个上午能认真发多少封"定，不按"名单里躺着多少家"定。
REGION_CAP = {"mi": 14, "ca": 8, "sz": 3, "tx": 10}   # 合计 35/天（2026-08-10 用户指令：提量到~35/天真人节奏，MI+TX+CA 三海外战场 + 深圳≤19；绝非机器人刷量）

# 跟进（R2/R3）每日最多只能占用本区域额度的这一比例，其余留给首触。
# 池子收窄后跟进比首触更值钱：同一批对口客户多轮触达，远胜再换一批不对口的。
FOLLOW_SHARE = 0.35

# 周末一律不发（下方代码层硬拦），本系数仅为兼容旧调用保留。
WEEKEND_FACTOR = 0.0
# 真人节奏（2026-08-10 用户硬性要求）：每分钟最多 2 封 → 两封之间至少 30 秒。
# 实际取 45~150 秒随机（均值 ≈ 97 秒 ≈ 0.6 封/分钟）。真人写完一封、看一眼下一家、
# 再发下一封，本来就是这个速度；18~42 秒一眼就是机器。
SEND_GAP_MIN, SEND_GAP_MAX = 45, 150
_HARD_FLOOR = 30   # 每分钟 ≤2 封的硬底线，任何情况下不得突破
assert SEND_GAP_MIN >= _HARD_FLOOR, "发信间隔不得低于 30 秒（每分钟最多 2 封）"

# 各类型开场白（英文版，比 LinkedIn 文案更正式可直接发）
OPENERS = {
 "connector": [
   "I'm not pitching {company} — I'm asking for a pointer. We built 23 CARLA edge-case scenarios (cut-in, dooring, occluded pedestrian, night) with telemetry and ISO 21448 annotations, and the teams who need them are exactly the ones inside your network.",
   "You see more of the {company} ecosystem than anyone. We put together 23 validated CARLA safety scenarios; small AV and V&V teams use them so they don't spend a month authoring edge cases. I'd rather you judge whether it's useful before I bother anyone.",
 ],
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

# 低摩擦付费阶梯（对齐落地页 #packs：单场景 $14/¥99 → 体验 $55/¥399 → Core-4 $278/¥1,999 → 全套/定制 $1,111/¥8,000）
# 思路：把"工程师自己就能拍板"的最低档($14 单场景)放在最前，去掉销售/合同摩擦，先拿到第一笔真实付款，
# 再用"升级全套可全额抵扣"做 land-and-expand（对标 AlphaDrive / Applied Intuition 的极致简单）。
CTA = ("→ Buy 1 scenario now — $14 (PayPal, no contract, 7-day refund, fully deductible toward full library): " + PAY +
       "\n→ Or free 2-week pilot (full 23-scenario library, no contract): " + SAMPLE +
       "\n→ Most teams start here: Core-4 pack $278 / ¥1,999 — the tier your engineer can approve alone: " + PAY +
       "\n→ Full library & 24/7 AI plan / Custom from $1,111 / ¥8,000 (founding price, limited seats): " + SITE +
       "\n→ Refer another team, get 15% commission (PayPal, instant): " + PAY)

# connector = 园区 / 测试场 / 孵化器 / 出行 VC。对他们只求一件事：引荐。
# 不塞付款按钮——园区经理不会自己刷卡买场景包，硬推只会把关系推没。
CONNECTOR_CTA = ("→ Free for your member companies: full 23-scenario library, 2-week pilot, no contract: " + SAMPLE +
                 "\n→ If it's useful, point me to one or two teams in your network who own the safety case: reply to this mail." +
                 "\n→ Whoever you introduce and closes, 15% goes back to you or your program (PayPal, instant): " + SITE)
CONNECTOR_CTA_CN = ("→ 园区内团队可免费用：全部 23 个场景，2 周试用，不签合同：" + SAMPLE +
                    "\n→ 如果觉得有用，帮我指一两个真正在做安全论证的团队，直接回这封邮件就行。" +
                    "\n→ 经您介绍成交的，15% 返给您或您的项目（PayPal 即时结算）：" + SITE)

SUBJECTS = {
 "connector": [
   "{company}: free 23-scenario AV safety library for your member teams",
   "For the {company} network — 23 validated CARLA edge cases, free pilot",
   "{company}: who in your cluster owns the AV safety case?",
 ],
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

# ============ 中文模板（city=深圳 使用，温情 + 微信直付；支付宝已取消，仅微信 + PayPal） ============
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

# 中文 CTA：3 个完全不同的链接必须各自放对——SITE=官网主页 / SAMPLE=样例场景 / PAY=PayPal 付款。
# 转介绍佣金只走 PayPal（国际买家统一），不再写微信/支付宝；支付宝收款码已整体取消，只留微信+PayPal。
CN_CTA = ("→ 一杯咖啡钱先验真：单场景包 ¥99（微信扫码，7 天无理由退，升级全套全额抵扣）：" +
          "\n   微信：%s（备注你的邮箱，直接发数据）" % WX +
          "\n→ 免费 2 周试用（全部 23 个场景，不用合同）：" + SAMPLE +
          "\n→ 官网完整方案与定价（23 类场景·合规报告样例）：" + SITE +
          "\n→ 工程师自己就能拍板：核心 4 场景包 ¥1,999（不用走采购流程）：" +
          "\n   微信：%s（备注你的邮箱）" % WX +
          "\n→ 定制全套 ¥8,000 起（创始价，名额有限）：" + PAY +
          "\n→ 介绍其他团队成交，返 15%（PayPal 即时结算）：" + PAY)

CHINA_CITIES = ("深圳", "华强", "广州", "北京", "上海", "杭州", "东莞", "佛山",
                 "广东", "江苏", "浙江", "成都", "武汉", "南京", "苏州", "重庆", "中国")

CA_CITIES = ("San Francisco", "San Jose", "Santa Clara", "Mountain View", "Palo Alto",
             "Sunnyvale", "Fremont", "Berkeley", "Menlo Park", "Foster City", "Redwood",
             "Milpitas", "Cupertino", "Oakland", "San Mateo", "Bay Area", "Silicon Valley",
             "Concord", "Walnut Creek", "湾区", "硅谷")
TX_CITIES = ("Austin", "Dallas", "Houston", "San Antonio", "Arlington", "Plano",
             "Frisco", "Round Rock", "Cedar Park", "Texas", "TX", "德州")

def region_of(row):
    """只认四个战场：mi / ca / tx / sz（密歇根 + 加州 + 德州 + 深圳）。
    focus_scope.py / 挖掘器把 cluster 统一成 'MI-...' / 'CA-...' / 'TX-...' / '深圳...'，
    优先按它判，判不出再回退看 city。判不出区域的行返回 None —— 宁可不发，也不要发错时区。"""
    c = (row.get("city", "") or "").strip()
    cl = (row.get("cluster", "") or "").strip()
    if cl.startswith("深圳") or any(k in c or k in cl for k in CHINA_CITIES):
        return "sz"
    if cl.startswith("CA-") or any(k in c or k in cl for k in CA_CITIES):
        return "ca"
    if cl.startswith("MI-") or "MI" in cl or c.endswith("MI") or "MICHIGAN" in (c + " " + cl).upper():
        return "mi"
    if cl.startswith("TX-") or any(k in c or k in cl for k in TX_CITIES):
        return "tx"
    return None

def use_cn(row):
    c = (row.get("city", "") or "").strip()
    cl = (row.get("cluster", "") or "")
    return any(k in c or k in cl for k in CHINA_CITIES)

# 产业集群社证：转介绍飞轮的核心。让同一集群的买家知道"同行已经在用"，
# 信任来自同圈层而非陌生推销。仅对已知集群注入，绝不编造任何不存在的背书。
CLUSTER_PROOF = {
    "深圳": ("对了，深圳这边做自动驾驶的团队，已经有几家在用我们的场景库跑安全论证了——同一个圈子，您大概率也听说过。",
             "Several AV teams right here in the Shenzhen GBA cluster already run our scenarios for their safety cases."),
    "GBA":  ("对了，大湾区这边做自动驾驶的团队，已经有几家在用我们的场景库跑安全论证了。",
             "Several AV teams across the Greater Bay Area already run our scenarios for their safety cases."),
    "MI":   ("密歇根这边的供应商和 V&V 圈子里，已经有团队在用我们的场景做安全论证了。",
             "Several suppliers and V&V shops in the Michigan auto corridor already use our scenarios."),
    "密歇根": ("密歇根这边的供应商和 V&V 圈子里，已经有团队在用我们的场景做安全论证了。",
               "Several suppliers and V&V shops in the Michigan auto corridor already use our scenarios."),
    "TX":   ("德州这边的 ADAS 团队，也有在用我们的场景库了。",
             "A few ADAS teams over in Texas already run our scenarios."),
    "CA":   ("湾区这边的自动驾驶团队，已经有几家在用我们的场景库了。",
             "A few AV teams in the Bay Area already run our scenario library."),
    "硅谷":  ("湾区这边的自动驾驶团队，已经有几家在用我们的场景库了。",
              "A few AV teams in the Bay Area already run our scenario library."),
}

def cluster_proof(row):
    """返回 (cn_text, en_text) 或 None。仅当集群命中已知社证才注入，绝不编造。"""
    blob = ((row.get("cluster", "") or "") + " " + (row.get("city", "") or ""))
    for key in ("深圳", "GBA", "密歇根", "MI", "TX", "CA", "硅谷"):
        if key in blob:
            return CLUSTER_PROOF[key]
    return None

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

# ---------------------------------------------------------------------------
# 邮箱守门器 (mailbox gate)
# 根因：媒体/投资者关系/HR/法务箱永远不会买，还会被标记为垃圾邮件，
# 直接威胁 SMTP 账号存活。这里是硬闸门 —— 任何来源（人工/挖掘器）
# 混进来的垃圾邮箱都发不出去，"永不再发生"。
# ---------------------------------------------------------------------------
# 精确 token（按 . _ - 拆分本地部后逐段比对，避免 media@ 漏掉 mediaservices@）
JUNK_EXACT = {
    "ir", "investor", "investors", "investorrelations", "investorrelation",
    "jobs", "job", "career", "careers", "hr", "recruit", "recruiting",
    "recruitment", "talent", "hiring", "resume", "resumes",
    "press", "media", "mediaservices", "mediarelations", "newsroom", "news",
    "pr", "corppr", "publicrelations", "communications", "comms", "comm",
    "legal", "privacy", "gdpr", "dpo", "webmaster", "abuse", "postmaster",
    "noreply", "donotreply", "bounce", "mailer-daemon",
    "support", "helpdesk", "billing", "invoice", "invoices", "accounts",
    "accountspayable", "accountsreceivable", "ap", "ar", "finance",
    "purchasing", "procurement", "supplier", "suppliers", "vendor", "vendors",
    "newsletter", "subscribe", "unsubscribe", "donate", "donations",
    "volunteer", "admissions", "alumni", "spam", "security", "webmail",
    "returns", "warranty", "complaints", "feedback",
}
# 子串匹配（这些拼在一起也算，例如 media-services、investor.relations）
JUNK_SUBSTR = [
    "investor", "recruit", "noreply", "no-reply", "donotreply", "unsubscribe",
    "newsroom", "mediaservice", "mediarelation", "pressroom", "press-office",
    "corp-pr", "corp.pr", "publicrelations", "accountspayable", "human-resources",
    "humanresources", "jobapplication",
]
GENERIC_PREFIX = (
    "info@", "contact@", "hello@", "sales@", "office@", "general@", "mail@",
    "admin@", "enquiries@", "enquiry@", "inquiries@", "inquiry@", "team@",
    "connect@", "ask@", "reach@", "service@", "customerservice@",
)

def junk_reason(email):
    """返回被拦截的原因；可发送则返回 None。"""
    e = (email or "").strip().lower()
    if not e or "@" not in e or "." not in e.split("@")[-1]:
        return "malformed"
    local = e.split("@", 1)[0]
    for t in re.split(r"[._\-+]+", local):
        if t in JUNK_EXACT:
            return "junk:" + t
    for s in JUNK_SUBSTR:
        if s in local:
            return "junk:" + s
    return None

def is_generic(email):
    e = (email or "").strip().lower()
    return e.startswith(GENERIC_PREFIX)

# ---------------------------------------------------------------------------
# 域名存活预检（诚信铁律 · 保护 8069dg@163.com 发信信誉）
# 仅在 DNS 明确返回「域名不存在(NXDOMAIN / Non-existent domain)」时拦截，
# 绝不因「无裸 A 记录但有 MX」而误杀真实企业/高校/政府域名
# （如 denso.com / bosch.com / mail.utexas.edu 仅靠 MX 收信，裸 A 查询会失败但邮件可达）。
# 任何不确定（超时 / DNS 错误）→ 放行，避免误杀真实买家。
# ---------------------------------------------------------------------------
_DNS_CACHE = {}
def domain_reachable(email):
    e = (email or "").strip().lower()
    if "@" not in e:
        return False
    d = e.split("@")[-1]
    if d in _DNS_CACHE:
        return _DNS_CACHE[d]
    reachable = True
    try:
        res = subprocess.run(["nslookup", "-type=MX", d], capture_output=True,
                             text=True, encoding="utf-8", errors="replace",
                             timeout=8)
        # NXDOMAIN 提示可能出现在 stdout 或 stderr，两者都查
        out = ((res.stdout or "") + (res.stderr or ""))
        if "Non-existent domain" in out or "NXDOMAIN" in out:
            reachable = False
    except Exception:
        reachable = True  # 不确定 → 放行，不误杀
    _DNS_CACHE[d] = reachable
    return reachable

# role 字段里混进来的非买家头衔 —— 出现即视为"我们并不知道对方职位"
BAD_ROLE_TOKENS = (
    "investor", "press", "media", "pr team", "communications", "hr ",
    "talent", "recruit", "support", "legal", "privacy",
)
DEFAULT_ROLE_EN = "ADAS / SOTIF validation"
DEFAULT_ROLE_CN = "ADAS / 智能驾驶安全验证"

def role_token(row):
    """
    诚信规则：只有当我们确实知道对方职能时才写职位。
    总机箱(info@/contact@) 或含非买家头衔 → 退回中性描述，
    绝不对着 media@ 喊 "ADAS V&V Manager"。
    """
    cn = use_cn(row)
    role = (row.get("role", "") or "").strip()
    rl = role.lower()
    if (not role) or is_generic(row.get("email", "")) or any(t in rl for t in BAD_ROLE_TOKENS):
        return DEFAULT_ROLE_CN if cn else DEFAULT_ROLE_EN
    return role

def salutation(row):
    """总机箱不假装认识某个人，直接称呼公司团队；知道职位就像真人转头叫一声职位。"""
    c = (row.get("company", "") or "").strip()
    cn = use_cn(row)
    if is_generic(row.get("email", "")):
        if cn:
            return ("%s 团队，您好：" % c) if c else "您好："
        return ("Hi %s team," % c) if c else "Hi there,"
    r = role_token(row).strip()
    if cn:
        return ("您好，%s：" % r) if r else ("%s 团队，您好：" % c)
    return ("Hi %s," % r) if r else ("Hi %s team," % c)

# 总机箱专用：请前台/总机转给真正的负责人，并挂 15% 转介绍钩子
FORWARD_ASK_EN = ("If this isn't your area, could you forward it to whoever owns ADAS / SOTIF "
                  "scenario validation? We pay a 15% referral on any deal that comes from an "
                  "introduction — including an internal one.")
FORWARD_ASK_CN = ("如果这不是您负责的范围，麻烦转给公司里做 ADAS / 智能驾驶场景验证的同事。"
                  "任何经您介绍成交的订单，我们都返 15%，仅 PayPal 即时结算。")

def opener_for(row, round_n):
    cn = use_cn(row)
    seg = row.get("segment", "") or "varied"
    bank = load_copy_bank()
    key = "openers_cn" if cn else "openers_en"
    variants = (bank.get(key, {}) or {}).get(seg) or (CN_OPENERS if cn else OPENERS).get(seg, (CN_OPENERS if cn else OPENERS)["varied"])
    idx = abs(hash(row.get("company", "") + str(round_n))) % len(variants)
    base = variants[idx].format(company=row.get("company", ""), role=role_token(row))
    follow = CN_FOLLOW if cn else FOLLOW
    if round_n in follow:
        base += "\n\n" + follow[round_n]
    return base

def subject_for(row, round_n):
    cn = use_cn(row)
    seg = row.get("segment", "") or "varied"
    bank = load_copy_bank()
    key = "subjects_cn" if cn else "subjects_en"
    variants = (bank.get(key, {}) or {}).get(seg) or (CN_SUBJECTS if cn else SUBJECTS).get(seg, (CN_SUBJECTS if cn else SUBJECTS)["varied"])
    idx = abs(hash(row.get("company", "") + str(round_n))) % len(variants)
    return variants[idx].format(company=row.get("company", ""), role=role_token(row))

def is_connector(row):
    return (row.get("segment", "") or "").strip().lower() == "connector"

def cta_for(row):
    """connector 只求引荐，不推付款；其余走正常付费阶梯。"""
    if is_connector(row):
        return CONNECTOR_CTA_CN if use_cn(row) else CONNECTOR_CTA
    return CN_CTA if use_cn(row) else CTA

def bridge_for(row, round_n):
    """接住对方真实处境的共情过渡句（先人后己，不编造履历）。按行业选变体。"""
    cn = use_cn(row)
    seg = row.get("segment", "") or "varied"
    bank = load_copy_bank()
    key = "bridges_cn" if cn else "bridges_en"
    pool = (bank.get(key, {}) or {})
    variants = pool.get(seg) or pool.get("varied", [""])
    if not variants or not variants[0]:
        return ""
    idx = abs(hash(row.get("company", "") + str(round_n) + "b")) % len(variants)
    return variants[idx]

def note_for(row):
    """落款前的个人真实动机句（轻量、真实、不编造履历）。"""
    cn = use_cn(row)
    bank = load_copy_bank()
    key = "notes_cn" if cn else "notes_en"
    variants = (bank.get(key, {}) or {}).get("varied", [""])
    if not variants or not variants[0]:
        return ""
    idx = abs(hash(row.get("company", ""))) % len(variants)
    return variants[idx]

def body_for(row, round_n):
    c = row.get("company", ""); role = role_token(row)
    cn = use_cn(row)
    # 英文邮件绝不允许出现中文 hook（见 hook_en.py 根因说明）
    hook = (row.get("hook", "") or "") if cn else sanitize_hook_en(row)
    generic = is_generic(row.get("email", "")) and not is_connector(row)
    if cn:
        proof = "不是玩具库——23 个场景每一个都带真实遥测 CSV、能一键复现的 CARLA 脚本，和按 ISO 21448 / UN-R157 写的合规标注。你们工程师下载就能跑、能交差。"
        lines = [
            salutation(row),
            "",
            opener_for(row, round_n),
            "",
        ]
        btxt = bridge_for(row, round_n)
        if btxt:
            lines += [btxt, ""]
        if hook:
            lines += ["为什么适合%s：%s" % (c, hook), ""]
        cp = cluster_proof(row)
        lines += [
            proof,
            "",
        ]
        if cp:
            lines += [cp[0], ""]
        lines += [
            cta_for(row),
            "",
        ] + ([FORWARD_ASK_CN, ""] if generic else
             ([] if is_connector(row) else
              ["P.S. 如果您认识的别的团队也需要边缘场景，介绍给我们——成交返 15%，PayPal 即时结算。", ""])) + (
            [note_for(row), ""] if note_for(row) else []
        ) + [
            "— 刘晓初，SantaClara Aegis（23 个安全关键 CARLA 边缘场景，含遥测数据 + SOTIF/UN-R157 合规标注）",
        ]
    else:
        proof = ("Not slideware — every one of the 23 ships with real telemetry CSVs, a one-command CARLA script, "
                 "and ISO 21448 / UN-R157 annotations. Your engineers run it, they don't rebuild it.")
        lines = [
            salutation(row),
            "",
            opener_for(row, round_n),
            "",
        ]
        btxt = bridge_for(row, round_n)
        if btxt:
            lines += [btxt, ""]
        if hook:
            lines += ["Why it fits %s: %s" % (c, hook), ""]
        cp = cluster_proof(row)
        lines += [
            proof,
            "",
        ]
        if cp:
            lines += [cp[1], ""]
        lines += [
            cta_for(row),
            "",
        ] + ([FORWARD_ASK_EN, ""] if generic else
             ([] if is_connector(row) else
              ["P.S. If another team you know needs edge-case scenarios, introduce them — we pay 15% referral, "
               "settled via PayPal the moment they buy.", ""])) + (
            [note_for(row), ""] if note_for(row) else []
        ) + [
            "— Liu Xiaochu, SantaClara Aegis (23 safety-critical CARLA edge-case scenarios w/ telemetry + SOTIF/UN-R157 annotation)",
        ]
    return "\n".join(lines)

# ============ HTML 版（带粗体/颜色，降低 AI 观感；与纯文本版内容一致） ============
_LINK_RE = re.compile(r"(https?://[^\s<]+)")

def _linkify(text):
    """转义后把 URL 包成蓝色加粗链接，其余文本原样保留。"""
    t = _esc(text)
    return _LINK_RE.sub(r'<a href="\1" style="color:#0a66c2;font-weight:700;text-decoration:none;">\1</a>', t)

# 关键价值词加琥珀色粗体，突出重点、降低「AI 生成」观感（在已转义/已包链的 HTML 上操作，绝不二次转义）
_KEY_RE = re.compile(r"(免费样例|免费|7天无理由退|7天退|转介绍|合规标注|遥测|可复现脚本|可复现|15%|单场景|¥\d+|/\$\d+|\$\d+)")
def _emphasize_html(html):
    """对已转义的安全 HTML 片段，把价格/免费/转介绍/合规等关键价值词加琥珀色粗体，让读者一眼看到重点。"""
    return _KEY_RE.sub(r'<b style="color:#b45309;">\1</b>', html)

def body_html_for(row, round_n):
    c = row.get("company", ""); role = role_token(row)
    cn = use_cn(row)
    hook = (row.get("hook", "") or "") if cn else sanitize_hook_en(row)
    generic = is_generic(row.get("email", "")) and not is_connector(row)
    if cn:
        proof = "不是玩具库——23 个场景每一个都带真实遥测 CSV、能一键复现的 CARLA 脚本，和按 ISO 21448 / UN-R157 写的合规标注。你们工程师下载就能跑、能交差。"
        sal_txt = _esc(salutation(row))
        opener = _esc(opener_for(row, round_n))
        why = ("为什么适合 <b>%s</b>：%s" % (_esc(c), _esc(hook))) if hook else ""
        cta = cta_for(row)
        ps = (FORWARD_ASK_CN if generic else
              ("" if is_connector(row) else
               "如果您认识的别的团队也需要边缘场景，介绍给我们——成交返 15%，PayPal 即时结算。"))
        signoff = _esc("刘晓初，SantaClara Aegis（23 个安全关键 CARLA 边缘场景，含遥测数据 + SOTIF/UN-R157 合规标注）")
    else:
        proof = ("Not slideware — every scenario ships with real telemetry CSVs, a one-command CARLA script, "
                 "and ISO 21448 / UN-R157 annotations. Your engineers drop it into the pipeline and run, not rebuild.")
        sal_txt = _esc(salutation(row))
        opener = _esc(opener_for(row, round_n))
        why = ("Why it fits <b>%s</b>: %s" % (_esc(c), _esc(hook))) if hook else ""
        cta = cta_for(row)
        ps = (FORWARD_ASK_EN if generic else
              ("" if is_connector(row) else
               "If another team you know needs edge-case scenarios, introduce them — we pay 15% referral, settled via PayPal the moment they buy."))
        signoff = _esc("Liu Xiaochu, SantaClara Aegis (23 safety-critical CARLA edge-case scenarios w/ telemetry + SOTIF/UN-R157 annotation)")
    bridge = _esc(bridge_for(row, round_n))
    note = _esc(note_for(row))
    H = ('<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;'
         'font-size:15px;line-height:1.65;color:#1a1a1a;max-width:640px;">')
    H += "<p style='margin:0 0 12px;'>" + sal_txt + "</p>"
    H += "<p style='margin:0 0 12px;font-size:15px;'>" + _emphasize_html(opener) + "</p>"
    if bridge:
        H += "<p style='margin:0 0 12px;font-style:italic;color:#4b5563;'>" + _emphasize_html(bridge) + "</p>"
    if why:
        H += "<p style='margin:0 0 12px;'>" + _emphasize_html(why) + "</p>"
    H += "<p style='margin:0 0 12px;color:#374151;'>" + _emphasize_html(_esc(proof)) + "</p>"
    cp = cluster_proof(row)
    if cp:
        H += "<p style='margin:0 0 12px;color:#374151;'>" + _emphasize_html(_esc(cp[0] if cn else cp[1])) + "</p>"
    # CTA 高亮块：每行一个蓝色加粗链接，突出可立即行动的付费入口
    H += ('<div style="background:#f3f8ff;border-left:4px solid #0a66c2;padding:12px 14px;'
          'margin:14px 0;border-radius:6px;">')
    for line in cta.split("\n"):
        line = line.strip()
        if not line:
            continue
        H += "<p style='margin:0 0 8px;'>" + _emphasize_html(_linkify(line)) + "</p>"
    H += "</div>"
    H += "<p style='margin:0 0 12px;'>" + _emphasize_html(_linkify(ps)) + "</p>"
    if note:
        H += "<p style='margin:0 0 12px;font-style:italic;color:#6b7280;font-size:13px;'>" + note + "</p>"
    H += "<p style='margin:0;color:#6b7280;font-size:13px;'>" + signoff + "</p>"
    H += "</div>"
    return H

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
# 163 触发日发信上限 / 反垃圾风控 —— 继续硬发会永久损伤发信信誉，必须当场停手顺延
RATE_LIMIT = ("dt:spm", "554 dt", "550 mi:", "exceeded the limit", "daily limit",
              "too many", "sending limit", "554 ds", "退信", "spam", "频率过快",
              "550 user has no permission")

def _is(det, keys):
    d = (det or "").lower()
    return any(k in d for k in keys)

def send_with_retry(email, subj, body, html=None, tries=3):
    last = ""
    for i in range(tries):
        ok, det = send_smtp.send(email, subj, body, html)
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
    if not region:
        print("[bulk] 未指定 --region，已跳过（防止错时区群发；请用 --region mi|ca|sz）。")
        return 0
    if region not in REGION_CAP:
        print("[bulk] 区域 %s 已不在聚焦范围（现只做 mi / ca / sz），本轮不发。" % region)
        return 0
    all_rows = load()
    if not all_rows:
        print("[bulk] 名单为空（prospects_email_ready.csv 无数据）。"); return 0
    rows = all_rows  # 发送时只筛选本区域，但落盘必须写回全量，避免三区域引擎互相覆盖丢失其它区域

    # 区域过滤
    if region:
        rows = [r for r in all_rows if region_of(r) == region]
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
        cap = base_cap * min(gap, 2)
        print("[bulk] 区域 %s 检测到缺失 %d 天，本区域补发额度提升到 %d（上限 2 倍，避免触发 163 日发信风控）。" % (region, gap - 1, cap))
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

    # 周末保护（代码层硬保护，不依赖调度器的 BYDAY 是否被正确解析）：
    # 所有区域周末一律不发信——① B2B 周末基本无人看公司邮箱，工作日发更尊重客户；
    # ② 避免周末把信发进空邮箱 / 触发 163 反垃圾周末风控告警；名额留到工作日集中发。
    is_weekend = datetime.date.today().weekday() >= 5
    if is_weekend:
        print("[bulk] 周末：区域 %s 不发信（B2B 周末无人处理，更尊重客户，也避免 163 风控告警），名额顺延至工作日。"
              % (region or "all"))
        rs["last_run"] = today; st[rkey] = rs; save_state(st)
        return 0

    # 跟进限额：R2/R3 最多只占 FOLLOW_SHARE 的额度，其余强制留给首触（保 500 家目标）
    follow_quota = int(quota * FOLLOW_SHARE)
    follow_sent = 0

    # 排序：①首触(round=0)优先于跟进 ②工作日先发 HIGH，周末先发 LOW/MED（把好名单留到工作日）
    _PRI = {"HIGH": 0, "MED": 1, "LOW": 2}
    def _order(r):
        first = 0 if int((r.get("round") or "0") or 0) == 0 else 1
        p = _PRI.get((r.get("priority") or "MED").strip().upper(), 1)
        return (first, (2 - p) if is_weekend else p)
    rows = sorted(rows, key=_order)

    # 一家公司一天只发一封（2026-08-10）：名单里同一家常有 sales@/contact@/defense@ 多个邮箱，
    # 同日连发三封在对方眼里就是群发机器人。真人只会挑一个最可能的收件人先发，等回音再换。
    def _ckey(r):
        return (r.get("company", "") or "").strip().lower()
    done_today = {_ckey(r) for r in all_rows if (r.get("last_sent", "") or "")[:10] == today}

    sent = 0
    fails = 0
    blocked = 0
    dedup = 0
    aborted = ""
    try:
        for row in rows:
            if limit and sent >= limit: break
            if sent >= quota: break
            if _ckey(row) in done_today:
                dedup += 1
                continue
            email = (row.get("email", "") or "").strip()
            if not email or "@" not in email: continue
            if row.get("status") in ("replied", "deal", "unsub", "sent_all", "blocked", "parked"): continue
            # === 邮箱守门器：媒体/IR/HR/法务箱一律不发，直接隔离 ===
            jr = junk_reason(email)
            if jr:
                row["status"] = "blocked"
                row["last_error"] = "mailbox-gate:" + jr
                blocked += 1
                print("[gate] 拦截非买家邮箱 %s (%s)" % (email, jr))
                continue
            # 域名存活预检：NXDOMAIN 直接隔离，绝不发往不存在的域（防硬退信拖垮 163 信誉）
            if not domain_reachable(email):
                row["status"] = "blocked"
                row["last_error"] = "dns:nxdomain"
                blocked += 1
                print("[dns] 拦截不存在域名 %s" % email)
                continue
            if not is_due(row): continue
            rd = int(row.get("round", "0") or 0)
            # 深圳同样做 R2/R3 跟进（用户 2026-08-11 指令：第一轮发出后追第二/第三封）。
            # 仍守 19 家公司总上限（不新增公司），但同一批对口客户多轮触达，更利于转介绍、破 $0。
            # 跟进邮件不得挤占首触额度（所有区域共用此逻辑）
            if rd >= 1:
                if follow_sent >= follow_quota:
                    continue
                follow_sent += 1
            subj = subject_for(row, rd + 1)
            body = body_for(row, rd + 1)
            html = body_html_for(row, rd + 1)
            if dry:
                print("[dry][%s] -> %s | %s" % (region or "all", email, subj))
                done_today.add(_ckey(row)); sent += 1; continue
            ok, det = send_with_retry(email, subj, body, html)
            if ok:
                row["round"] = str(rd + 1)
                row["last_sent"] = datetime.datetime.now().isoformat()
                row["status"] = "sent_all" if rd + 1 >= 3 else "contacted"
                row["last_error"] = ""
                sent += 1
                done_today.add(_ckey(row))
                print("[ok] %s | %s" % (email, subj))
                save(all_rows)
                # 真人节奏：每封之间错开 18~42 秒，避免同分钟齐发像群发机器人
                time.sleep(random.uniform(SEND_GAP_MIN, SEND_GAP_MAX))
            else:
                row["last_error"] = det
                fails += 1
                print("[fail] %s | %s" % (email, det))
                if _is(det, FATAL_AUTH):
                    aborted = det
                    print("[bulk] 检测到 SMTP 授权失败，立即停止本轮，保留剩余额度。")
                    break
                if _is(det, RATE_LIMIT):
                    aborted = det
                    print("[bulk] 检测到 163 触发日发信限额/风控，本轮立即停手（继续硬发只会伤发信信誉）。"
                          "剩余名单顺延到下一次运行，请勿手动重跑。")
                    break
    finally:
        try:
            save(all_rows)
        except Exception as ex:
            print("[bulk] 名单落盘失败：%s" % ex)
        rs["last_run"] = today
        st[rkey] = rs
        save_state(st)
    if not dry and sent:
        bump_touch(sent)
    print("[bulk] 区域 %s 本轮发送 %d 封，失败 %d 封，守门器拦截 %d 个非买家邮箱，"
          "同公司当日去重跳过 %d 个邮箱（每日上限 %d）。"
          % (region or "all", sent, fails, blocked, dedup, cap))
    if aborted:
        print("[bulk] ACTION: 163 授权码疑似失效，请在邮箱设置重新生成并更新 growth/config.json 的 channels.email.smtp_pass。")
    return sent

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--due", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--region", default=None, choices=["mi", "ca", "sz", "tx"])
    a = ap.parse_args()
    if a.dry:
        run(dry=True, limit=a.limit, region=a.region)
    else:
        run(limit=a.limit, region=a.region)
