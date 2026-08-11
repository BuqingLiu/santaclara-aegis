# -*- coding: utf-8 -*-
"""
dev.to 全自动对账发布器（彻底替代「手动去 Drafts 点发布」）
========================================================
老板看不懂专业后台，所以这一步必须全自动：
1) GET /articles/me 拉取你 dev.to 账号下所有文章（含草稿）。
2) 对 growth/content/ 下每篇草稿：
   - 若已在 dev.to（按标题匹配）且还是草稿 → 自动 PUT 发布（published=true）；
   - 若已在 dev.to 且已发布 → 记入 published.json，避免重复；
   - 若 dev.to 里没有 → 自动 POST 发布（带 canonical_url 回链落地页，规避新号 403）。
3) 全程不依赖人工打开后台。每天跑一次即可。

信用底线：只发布我们自己写的技术干货，绝不刷量、绝不买粉。
"""
import os, sys, json, glob, urllib.request, urllib.error
BASE  = os.path.dirname(os.path.abspath(__file__))
CFG   = os.path.join(BASE, "config.json")
CONTENT = os.path.join(BASE, "content")
PUBLISHED = os.path.join(CONTENT, "published.json")

def _cfg():
    return json.load(open(CFG, encoding="utf-8")).get("channels", {}).get("devto", {})

def _api(key, method, url, data=None):
    h = {"api-key": key, "User-Agent": "Mozilla/5.0"}
    if data is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return True, json.load(r)
    except urllib.error.HTTPError as e:
        return False, "HTTP %s: %s" % (e.code, e.read().decode("utf-8")[:240])
    except Exception as ex:
        return False, "失败: %s" % ex

def _tg_alert(full_cfg, msg):
    """API 失败时 TG 告警老板，不用他盯后台。"""
    tg = full_cfg.get("channels", {}).get("telegram", {})
    if not tg.get("enabled"):
        return
    token = tg.get("token")
    chat = tg.get("owner_chat_id")
    if not token or not chat:
        return
    url = "https://api.telegram.org/bot%s/sendMessage" % token
    data = json.dumps({"chat_id": chat, "text": msg, "parse_mode": "HTML"}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
    except Exception as ex:
        print("[devto_reconcile] TG 告警发送失败: %s" % ex)

def _published_set():
    if os.path.exists(PUBLISHED):
        try: return set(json.load(open(PUBLISHED, encoding="utf-8")))
        except Exception: return set()
    return set()

def _mark(name):
    s = _published_set(); s.add(name)
    json.dump(sorted(s), open(PUBLISHED, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def _parse_frontmatter(text):
    meta = {"title": "Untitled", "tags": [], "published": True}
    if not text.startswith("---"): return meta, text
    end = text.find("\n---", 3)
    if end < 0: return meta, text
    fm = text[3:end].strip(); body = text[end+4:].lstrip("\n")
    for line in fm.splitlines():
        if line.lower().startswith("title:"): meta["title"] = line.split(":",1)[1].strip()
        elif line.lower().startswith("tags:"): meta["tags"] = [t.strip() for t in line.split(":",1)[1].split(",") if t.strip()]
        elif line.lower().startswith("published:"): meta["published"] = line.split(":",1)[1].strip().lower() in ("true","1","yes")
    return meta, body

def run():
    full_cfg = json.load(open(CFG, encoding="utf-8"))
    c = full_cfg.get("channels", {}).get("devto", {})
    key = c.get("key", "")
    if not c.get("enabled") or not key or key.startswith("PASTE"):
        print("[devto_reconcile] 未启用或 key 未填。"); return
    ok, articles = _api(key, "GET", "https://dev.to/api/articles/me")
    if not ok:
        err = "[devto_reconcile] 拉取文章失败：%s" % articles
        print(err)
        _tg_alert(full_cfg, "dev.to API 异常（请老板重生成 API key 并更新 config.json）：%s" % articles)
        return
    # 标题 -> 文章对象
    by_title = {}
    for a in (articles or []):
        t = (a.get("title") or "").strip().lower()
        if t: by_title[t] = a
    print("[devto_reconcile] dev.to 账号下文章 %d 篇（含草稿）。" % len(articles))

    done = _published_set()
    published_cnt = 0; drafted_cnt = 0; posted_cnt = 0
    for f in sorted(glob.glob(os.path.join(CONTENT, "*.md"))):
        name = os.path.basename(f)
        if name == "published.json": continue
        if name in done:
            print("[devto_reconcile] 已处理(跳过) -> %s" % name); published_cnt += 1
            continue
        meta, body = _parse_frontmatter(open(f, encoding="utf-8").read())
        title = (meta.get("title") or "").strip()
        tkey = title.lower()
        canonical = full_cfg.get("landing", "")
        if tkey in by_title:
            art = by_title[tkey]
            if not art.get("published"):
                payload = json.dumps({"article": {"published": True}}).encode("utf-8")
                ok2, res = _api(key, "PUT", "https://dev.to/api/articles/%s" % art.get("id"), payload)
                if ok2:
                    print("[devto_reconcile] 已发布草稿 -> %s" % title); drafted_cnt += 1
                else:
                    print("[devto_reconcile] 发布草稿失败 %s: %s" % (title, res)); continue
            else:
                print("[devto_reconcile] 已发布(跳过) -> %s" % title); published_cnt += 1
            _mark(name); continue
        # dev.to 没有这篇 -> POST
        article = {"title": title, "body_markdown": body, "tags": meta.get("tags", [])[:4], "published": True}
        if canonical: article["canonical_url"] = canonical
        payload = json.dumps({"article": article}).encode("utf-8")
        ok3, res = _api(key, "POST", "https://dev.to/api/articles", payload)
        if ok3:
            print("[devto_reconcile] 已发布新文 -> %s (%s)" % (title, res.get("url") if isinstance(res, dict) else res))
            posted_cnt += 1; _mark(name)
        else:
            print("[devto_reconcile] 发布新文失败 %s: %s" % (title, res))
    print("[devto_reconcile] 本轮：新发 %d | 草稿转发布 %d | 已发布跳过 %d" % (posted_cnt, drafted_cnt, published_cnt))

if __name__ == "__main__":
    run()
