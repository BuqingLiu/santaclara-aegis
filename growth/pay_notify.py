# -*- coding: utf-8 -*-
"""
PayPal 到账自动通知（全自动闭环 #9）
====================================
PayPal 每笔到账会向账户邮箱发一封 "You received a payment" 邮件。
本脚本监控该邮箱（默认复用 channels.imap，即 8069dg@163.com；
请在 PayPal 账户里把 8069dg@163.com 加为通知邮箱，或把 PayPal 邮件转发到它），
识别到账邮件 -> 解析金额 -> 更新收入台账 + 推送 Telegram 告警给你。

不伪造任何数据：只有真实到账邮件才会被记入 PAYMENTS.json 与 tracker.paid。

用法：
  python growth/pay_notify.py --once     # 立即扫描一轮（自动化每 15 分钟调用）
依赖：config.json 的 channels.imap（监控邮箱）与 channels.telegram（告警推送）。
"""
import os, sys, json, imaplib, poplib, email, re, datetime, argparse, urllib.request, urllib.error
from email.header import decode_header, make_header
import send_smtp  # 用于到账后自动发送交付邮件（C3）

def _hdr(msg, name):
    """安全取邮件头：编码后的 Header 对象也能正确转成 str。"""
    v = msg.get(name)
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    try:
        return str(make_header(decode_header(v)))
    except Exception:
        return str(v)

BASE = os.path.dirname(os.path.abspath(__file__))
CFG   = os.path.join(BASE, "config.json")
TRACK = os.path.join(BASE, "tracker.json")
STATE = os.path.join(BASE, "pay_notify_state.json") if False else os.path.join(BASE, "pay_notify_state.json")
LEDGER= os.path.join(BASE, "PAYMENTS.json")
CHAT  = os.path.join(BASE, "tg_chatids.json")
RATE  = 7.25  # USD->CNY 近似，仅用于台账展示
SITE  = "https://buqingliu.github.io/santaclara-aegis/"
SAMPLE= "https://buqingliu.github.io/santaclara-aegis/samples/sample-scenario.html"
PAY   = "https://www.paypal.com/paypalme/LiuXiaochu2"

def _cfg():
    return json.load(open(CFG, encoding="utf-8"))

def _inbox_cfg(cfg):
    pn = cfg.get("channels", {}).get("paypal_notify")
    if pn and pn.get("host"):
        return pn
    pop = cfg.get("channels", {}).get("pop3", {})
    if pop and pop.get("enabled") and pop.get("host"):
        return pop
    return cfg.get("channels", {}).get("imap", {})

def _inbox_list(cfg):
    """返回所有需要监控的收款通知邮箱（支持多邮箱：163 + QQ 等）。

    优先读 channels.paypal_notify_accounts（列表：proto/host/port/user/pass/enabled/label/note）；
    未配置时退回旧的单邮箱逻辑，保证向后兼容。
    """
    accounts = cfg.get("channels", {}).get("paypal_notify_accounts")
    out = []
    if isinstance(accounts, list) and accounts:
        for a in accounts:
            lbl = a.get("label") or a.get("user") or "(未命名)"
            if not a.get("enabled"):
                print("[pay_notify] 跳过未启用邮箱: %s%s" % (lbl, ("  ※ " + a["note"]) if a.get("note") else ""))
                continue
            if a.get("host") and a.get("user") and a.get("pass"):
                out.append(a)
            else:
                print("[pay_notify] 邮箱配置不完整（缺 host/user/pass），跳过: %s" % lbl)
        if out:
            return out
    pop = cfg.get("channels", {}).get("pop3", {})
    if pop and pop.get("enabled") and pop.get("host"):
        p = dict(pop); p.setdefault("proto", "pop3"); p.setdefault("label", pop.get("user"))
        return [p]
    box = _inbox_cfg(cfg)
    if box.get("host"):
        b = dict(box)
        b.setdefault("proto", "pop3" if int(b.get("port", 995)) == 995 else "imap")
        b.setdefault("label", box.get("user"))
        return [b]
    return []

def _load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {"seen": []}

def _save_state(seen):
    json.dump({"seen": list(seen)[-800:]}, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def _ledger(entry):
    data = []
    if os.path.exists(LEDGER):
        try:
            data = json.load(open(LEDGER, encoding="utf-8"))
        except Exception:
            data = []
    data.append(entry)
    json.dump(data, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def _bump_paid(usd, cny):
    if not os.path.exists(TRACK):
        return
    try:
        d = json.load(open(TRACK, encoding="utf-8"))
        f = d.setdefault("funnel", {})
        f["paid"] = int(f.get("paid", 0)) + 1
        d["paid_usd"] = round(float(d.get("paid_usd", 0)) + usd, 2)
        d["paid_cny"] = round(float(d.get("paid_cny", 0)) + cny, 2)
        json.dump(d, open(TRACK, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception as ex:
        print("[pay_notify] tracker 更新失败: %s" % ex)

def _tg_alert(text):
    cfg = _cfg().get("channels", {}).get("telegram", {})
    token = cfg.get("token", "")
    if not token:
        print("[pay_notify] Telegram 未配置，跳过告警推送（收入仍已记入台账）。")
        return
    owner = cfg.get("owner_chat_id")
    chat_ids = []
    if owner:
        chat_ids = [owner]
    else:
        try:
            data = json.load(open(CHAT, encoding="utf-8"))
            chat_ids = [x.get("chat_id") for x in data.get("all", []) if x.get("chat_id")]
        except Exception:
            chat_ids = []
    if not chat_ids:
        print("[pay_notify] 无可用 chat_id（请先在 Telegram 给机器人发一条消息以捕获您的 chat_id）。")
        return
    for cid in chat_ids:
        try:
            req = urllib.request.Request(
                "https://api.telegram.org/bot%s/sendMessage" % token,
                data=json.dumps({"chat_id": cid, "text": text}).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=20)
        except Exception as ex:
            print("[pay_notify] Telegram 推送 %s 失败: %s" % (cid, ex))

def _extract_payer_email(text):
    """从 PayPal 到账邮件正文里尽量解析出付款方邮箱，用于自动交付。"""
    m = re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", text)
    return m.group(0) if m else None

def _deliver_email(payer, usd, cny):
    """C3：真实到账后，经 SMTP 自动给买家发「交付邮件 + 邀转介绍」。"""
    if not send_smtp.configured():
        print("[pay_notify] SMTP 未配置，跳过交付邮件（收入仍已记账）。")
        return False
    subj = "Your SantaClara Aegis 23-scenario library is ready + 15%% referral"
    body = (
        "Hi,\n\n"
        "Thank you for your payment of $%.2f (approx RMB %.0f) for SantaClara Aegis.\n\n"
        "Your 23 safety-critical CARLA edge-case scenarios (telemetry CSV + reproducible "
        "scripts + ISO 21448 / UN-R157 SOTIF annotation) are ready:\n"
        "  Access / download: %s\n"
        "  Free sample scenario: %s\n\n"
        "Questions? Just reply to this email or message us on Telegram.\n\n"
        "One more thing: if you know another team that needs edge-case scenarios, introduce "
        "them to us -- we pay 15%% referral, settled via PayPal the moment they buy. "
        "Your referral link: %s\n\n"
        "-- Buqing Liu, SantaClara Aegis"
    ) % (usd, cny, SITE, SAMPLE, PAY)
    ok, det = send_smtp.send(payer, subj, body)
    if ok:
        print("[pay_notify] 已向买家 %s 发送交付邮件（含 15%% 转介绍）。" % payer)
    else:
        print("[pay_notify] 交付邮件发送失败 %s: %s" % (payer, det))
    return ok

def _parse_amount(text):
    m = re.search(r"(?:\$|USD)\s*([\d,]+(?:\.\d{2})?)", text, re.I)
    if m:
        return float(m.group(1).replace(",", ""))
    m = re.search(r"(?:¥|CNY|RMB)\s*([\d,]+(?:\.\d{2})?)", text)
    if m:
        return float(m.group(1).replace(",", "")) / RATE
    return None

def _fetch_imap(imap, since):
    msgs = []
    try:
        m = imaplib.IMAP4_SSL(imap["host"], int(imap.get("port", 993)), timeout=30)
        m.login(imap["user"], imap["pass"])
        typ, sel = m.select("INBOX")
        if typ != "OK":
            typ, sel = m.select()
        if typ != "OK":
            print("[pay_notify] IMAP 无法选收件箱: %s" % (sel,))
            m.logout(); return []
        print("[pay_notify] IMAP 已选中收件箱，信件数: %s" % (sel,))
        typ, data = m.search(None, "SINCE", since)
        ids = data[0].split() if data and data[0] else []
        for mid in ids:
            _, msg_data = m.fetch(mid, "(RFC822)")
            if msg_data and msg_data[0] is not None:
                msgs.append(msg_data[0][1])
        m.logout()
    except Exception as ex:
        print("[pay_notify] IMAP 读取失败: %s" % ex)
    return msgs

def _fetch_pop3(pop):
    msgs = []
    try:
        p = poplib.POP3_SSL(pop["host"], int(pop.get("port", 995)))
        p.user(pop["user"]); p.pass_(pop["pass"])
        count, _ = p.stat()
        print("[pay_notify] POP3 已登录，信件数: %d" % count)
        for i in range(1, count + 1):
            try:
                resp, lines, octets = p.retr(i)
                msgs.append(b"\n".join(lines))
            except Exception as ex:
                print("[pay_notify] POP3 retr %d 失败: %s" % (i, ex))
        p.quit()
    except Exception as ex:
        print("[pay_notify] POP3 读取失败: %s" % ex)
    return msgs

def _msg_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body += (part.get_payload(decode=True) or b"").decode("utf-8", "ignore")
    else:
        body = (msg.get_payload(decode=True) or b"").decode("utf-8", "ignore")
    return body

def run_once():
    cfg = _cfg()
    boxes = _inbox_list(cfg)
    if not boxes:
        print("[pay_notify] 监控邮箱未配置（channels.paypal_notify_accounts / pop3 / imap）。")
        return
    state = _load_state()
    seen = set(state.get("seen", []))

    since = (datetime.datetime.now() - datetime.timedelta(days=14)).strftime("%d-%b-%Y")
    raw_list = []
    for box in boxes:
        label = box.get("label") or box.get("user")
        proto = (box.get("proto") or ("pop3" if int(box.get("port", 995)) == 995 else "imap")).lower()
        print("[pay_notify] 扫描收款通知邮箱: %s (%s://%s)" % (label, proto, box.get("host")))
        if proto == "pop3":
            raw_list += _fetch_pop3(box)
        else:
            raw_list += _fetch_imap(box, since)

    found = 0
    for raw in raw_list:
        try:
            msg = email.message_from_bytes(raw)
            mid_id = _hdr(msg, "Message-ID") or _hdr(msg, "Date") + _hdr(msg, "From")
            if mid_id in seen:
                continue
            frm = _hdr(msg, "From").lower()
            subj = _hdr(msg, "Subject")
            is_paypal = ("paypal" in frm) or ("paypal" in subj.lower()) or ("received a payment" in subj.lower())
            if not is_paypal:
                seen.add(mid_id)
                continue
            subject = (msg.get("Subject") or "")
            body = _msg_body(msg)
            full = subject + "\n" + body
            usd = _parse_amount(full)
            if usd and usd > 0:
                cny = round(usd * RATE, 2)
                ts = datetime.datetime.now().isoformat()
                entry = {"at": ts, "usd": usd, "cny": cny, "subject": subject, "message_id": mid_id}
                _ledger(entry)
                _bump_paid(usd, cny)
                found += 1
                seen.add(mid_id)
                note = ("\U0001F4B0 PayPal 到账通知\n金额: $%.2f (≈¥%.2f)\n主题: %s\n时间: %s\n\n已自动记入收入台账 PAYMENTS.json + tracker.paid。") % (usd, cny, subject, ts)
                print("[pay_notify] 检测到到账: $%.2f | %s" % (usd, subject))
                _tg_alert(note)
                # C3：真实到账 -> 自动交付数据 + 邀转介绍
                payer = _extract_payer_email(full)
                if payer:
                    _deliver_email(payer, usd, cny)
                    entry["payer"] = payer
                    entry["delivered"] = True
                    _ledger(entry)  # 更新台账带上 payer/delivered
                else:
                    print("[pay_notify] 未能从邮件解析买家邮箱，请人工交付。主题: %s" % subject)
                    _tg_alert("⚠️ 到账但未能解析买家邮箱，请人工交付数据。主题: %s" % subject)
            else:
                seen.add(mid_id)
        except Exception as ex:
            print("[pay_notify] 处理邮件异常: %s" % ex)
            continue
    _save_state(seen)
    if found:
        print("[pay_notify] 本轮新增到账 %d 笔。" % found)
    else:
        print("[pay_notify] 本轮无新到账（已扫描 %d 封邮件）。" % len(raw_list))
    return found

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--once", action="store_true"); ap.parse_args()
    run_once()
