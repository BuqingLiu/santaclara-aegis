# -*- coding: utf-8 -*-
"""
每日构建 · 反复优化循环（总驱动器）
==================================
1) 文案进化：按 CSV 中「已联系 / 已回信」统计每类型(segment)回信率，对低于阈值的类型
   旋转 copy_bank.json 的 subject/opener 顺序（换一个角度再试），实现无 LLM 的自动 A/B 进化。
2) 通道健康巡检：SMTP 登录测试、POP3 收件箱可读测试、名单完整性（行数/区域分布/空邮箱），
   并对异常发 Telegram 告警（不真发营销邮件，只探测连通性）。
3) 写每日优化日志 OPTIMIZE_LOG.md + 更新 tracker.json 的 reply_rate / last_optimize。

完全自动、不向用户请示。信用底线之上：只统计真实回信，绝不伪造数据。
"""
import os, csv, json, datetime, ssl, smtplib, poplib, urllib.request, urllib.parse
BASE = os.path.dirname(os.path.abspath(__file__))
CSV  = os.path.join(BASE, "prospects_email_ready.csv")
BANK = os.path.join(BASE, "copy_bank.json")
TRACK= os.path.join(BASE, "tracker.json")
LOG  = os.path.join(BASE, "OPTIMIZE_LOG.md")
CFG  = os.path.join(BASE, "config.json")

def region_of(row):
    c = (row.get("city", "") or "").strip(); cl = (row.get("cluster", "") or "").strip()
    s = (c + " " + cl).upper()
    if "深圳" in c or "深圳" in cl or "华强" in cl: return "sz"
    if "TX" in cl or c.endswith("TX") or "TEXAS" in s: return "tx"
    if "MI" in cl or c.endswith("MI") or "MICHIGAN" in s: return "mi"
    return "mi"

def load_rows():
    if not os.path.exists(CSV): return []
    return list(csv.DictReader(open(CSV, encoding="utf-8-sig")))

def tg_alert(text):
    try:
        c = json.load(open(CFG, encoding="utf-8"))
        t = c.get("channels", {}).get("telegram", {})
        if not t.get("enabled"): return
        url = "https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s" % (
            t["token"], t["owner_chat_id"], urllib.parse.quote(text))
        urllib.request.urlopen(url, timeout=10)
    except Exception:
        pass

def health_smtp():
    try:
        c = json.load(open(CFG, encoding="utf-8"))["channels"]["email"]
        ctx = ssl.create_default_context()
        s = smtplib.SMTP_SSL(c["smtp_host"], c["smtp_port"], context=ctx, timeout=15)
        s.login(c["smtp_user"], c["smtp_pass"]); s.quit()
        return True, ""
    except Exception as e:
        return False, str(e)[:160]

def health_pop3():
    try:
        c = json.load(open(CFG, encoding="utf-8"))["channels"]["pop3"]
        p = poplib.POP3_SSL(c["host"], c["port"], timeout=15)
        p.user(c["user"]); p.pass_(c["pass"]); p.list(); p.quit()
        return True, ""
    except Exception as e:
        return False, str(e)[:160]

def rotate_bank():
    """对回信率低于阈值的 segment，旋转其 subject/opener 顺序（换角度）。返回旋转记录。"""
    rows = load_rows()
    seg_contact = {}; seg_reply = {}
    for r in rows:
        seg = r.get("segment", "") or "varied"
        st = r.get("status", "")
        if st in ("contacted", "sent_all"):
            seg_contact[seg] = seg_contact.get(seg, 0) + 1
        if st == "replied" or r.get("replied") == "true":
            seg_reply[seg] = seg_reply.get(seg, 0) + 1
    if not os.path.exists(BANK):
        return []
    bank = json.load(open(BANK, encoding="utf-8"))
    rotated = []
    FLOOR = 0.005   # 回信率 < 0.5% 且样本≥20 才旋转
    for key in ("subjects_en", "subjects_cn", "openers_en", "openers_cn"):
        d = bank.get(key, {})
        for seg, lst in d.items():
            if not isinstance(lst, list) or len(lst) < 2:
                continue
            ct = seg_contact.get(seg, 0); rp = seg_reply.get(seg, 0)
            rate = (rp / ct) if ct else 0
            if ct >= 20 and rate < FLOOR:
                lst.append(lst.pop(0))   # 把第一个角度移到末尾，换下一个角度
                rotated.append("%s/%s 回信率%.1f%%→旋转角度" % (key, seg, rate * 100))
    if rotated:
        json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return rotated

def main():
    now = datetime.datetime.now()
    rows = load_rows()
    total = len(rows)
    pending = sum(1 for r in rows if (r.get("status", "pending") or "pending") == "pending")
    r1_done = sum(1 for r in rows if r.get("status") in ("contacted", "sent_all"))
    replied = sum(1 for r in rows if r.get("status") == "replied" or r.get("replied") == "true")
    rate = (replied / r1_done) if r1_done else 0
    from collections import Counter
    pend_reg = Counter(region_of(r) for r in rows if (r.get("status", "pending") or "pending") == "pending")

    rotated = rotate_bank()

    smtp_ok, smtp_err = health_smtp()
    pop3_ok, pop3_err = health_pop3()
    csv_ok = total > 0
    empty_pending = sum(1 for r in rows if (r.get("status","pending")=="pending" and ("@" not in (r.get("email","") or ""))))

    log = []
    log.append("\n## %s" % now.strftime("%Y-%m-%d %H:%M"))
    log.append("- 名单: %d 行 | R1 已发 %d | 待发 %d | 回信 %d | 回信率 %.2f%%" % (
        total, r1_done, pending, replied, rate * 100))
    log.append("- 待发区域分布: MI=%d TX=%d SZ=%d" % (pend_reg.get("mi",0), pend_reg.get("tx",0), pend_reg.get("sz",0)))
    log.append("- 文案进化: %s" % ("；".join(rotated) if rotated else "各类型回信率达标，未旋转"))
    log.append("- SMTP: %s | POP3: %s | 名单完整: %s | 待发空邮箱: %d" % (
        "OK" if smtp_ok else "FAIL "+smtp_err, "OK" if pop3_ok else "FAIL "+pop3_err,
        "OK" if csv_ok else "NO", empty_pending))
    if not smtp_ok:
        tg_alert("⚠️ SantaClara 发信 SMTP 探测失败：%s（多半授权码失效，去 163 重生成并更新 config.json）" % smtp_err)
    if not pop3_ok:
        tg_alert("⚠️ SantaClara 收信 POP3 探测失败：%s" % pop3_err)
    if empty_pending:
        tg_alert("⚠️ 名单有 %d 个待发客户邮箱为空，请核查 prospects_email_ready.csv" % empty_pending)

    with open(LOG, "a", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")

    if os.path.exists(TRACK):
        try:
            t = json.load(open(TRACK, encoding="utf-8"))
            t.setdefault("funnel", {})["reply_rate"] = round(rate, 4)
            t["last_optimize"] = now.strftime("%Y-%m-%d %H:%M")
            t["health"] = {"smtp": smtp_ok, "pop3": pop3_ok, "csv_rows": total}
            json.dump(t, open(TRACK, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        except Exception:
            pass

    print("[optimize] R1已发=%d 待发=%d 回信=%d 回信率=%.2f%% | SMTP=%s POP3=%s | 旋转=%d" % (
        r1_done, pending, replied, rate*100, smtp_ok, pop3_ok, len(rotated)))

if __name__ == "__main__":
    main()
