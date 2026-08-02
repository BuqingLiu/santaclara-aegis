# -*- coding: utf-8 -*-
"""
dev.to 自动发文（全自动闭环 #7 · 服务 9 个月 $150K/月北极星）
============================================================
自动把「真实技术干货」发到 dev.to，文内带落地页 + 免费样例 + Telegram 机器人链接，
换取持续的自然搜索/社区流量（复利型入站，区别于冷邮一次性触达）。

队列机制（提频关键）：
- growth/content/ 下所有 *.md 都是候选草稿（frontmatter 写 title/tags/published）；
- growth/content/published.json 记录已发过的草稿名；
- 每次运行自动挑「下一篇未发过的」发布，发完即记。这样提频也不会重复发同一篇。
- 想更频繁？多放几篇草稿到 content/ 即可（自动化每 N 天跑一次，每次发一篇新文）。

用法：
  python growth/content_publisher.py --once          # 发下一篇未发的草稿
  python growth/content_publisher.py --dry           # 只预览不发
  python growth/content_publisher.py --file xxx.md   # 指定发某篇
"""
import os, sys, json, argparse, glob, urllib.request, urllib.error

BASE  = os.path.dirname(os.path.abspath(__file__))
CFG   = os.path.join(BASE, "config.json")
CONTENT = os.path.join(BASE, "content")
PUBLISHED = os.path.join(CONTENT, "published.json")

def _cfg():
    return json.load(open(CFG, encoding="utf-8")).get("channels", {}).get("devto", {})

def _published_set():
    if os.path.exists(PUBLISHED):
        try:
            return set(json.load(open(PUBLISHED, encoding="utf-8")))
        except Exception:
            return set()
    return set()

def _mark_published(name):
    s = _published_set()
    s.add(name)
    json.dump(sorted(s), open(PUBLISHED, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def _next_draft():
    """返回 (路径, 名字) 下一篇未发的草稿；没有则 (None,None)。"""
    done = _published_set()
    files = sorted(glob.glob(os.path.join(CONTENT, "*.md")))
    for f in files:
        name = os.path.basename(f)
        if name == "published.json":
            continue
        if name in done:
            continue
        return f, name
    return None, None

def _parse_frontmatter(text):
    meta = {"title": "Untitled", "tags": [], "published": True}
    if not text.startswith("---"):
        return meta, text
    end = text.find("\n---", 3)
    if end < 0:
        return meta, text
    fm = text[3:end].strip()
    body = text[end+4:].lstrip("\n")
    for line in fm.splitlines():
        if line.lower().startswith("title:"):
            meta["title"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("tags:"):
            meta["tags"] = [t.strip() for t in line.split(":", 1)[1].split(",") if t.strip()]
        elif line.lower().startswith("published:"):
            meta["published"] = line.split(":", 1)[1].strip().lower() in ("true", "1", "yes")
    return meta, body

def _post(key, meta, body):
    payload = json.dumps({"article": {
        "title": meta.get("title"),
        "body_markdown": body,
        "tags": meta.get("tags", [])[:4],
        "published": meta.get("published", True),
    }}).encode("utf-8")
    req = urllib.request.Request("https://dev.to/api/articles", data=payload,
                                 headers={"api-key": key, "Content-Type": "application/json",
                                          "User-Agent": "Mozilla/5.0 (SantaClaraAegis content engine)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
            return True, d.get("url") or d.get("id") or "ok"
    except urllib.error.HTTPError as e:
        return False, "HTTP %s: %s" % (e.code, e.read().decode("utf-8")[:240])
    except Exception as ex:
        return False, "失败: %s" % ex

def run(dry=False, draft=None):
    c = _cfg()
    key = c.get("key", "")
    if not c.get("enabled") or not key or key.startswith("PASTE"):
        print("[content_publisher] 未启用或 key 未填（在 config.json 的 channels.devto 填 key 并 enabled=true）。")
        return
    if draft and os.path.exists(draft):
        path, name = draft, os.path.basename(draft)
    else:
        path, name = _next_draft()
    if not path:
        print("[content_publisher] 没有待发新草稿（content/ 下的 .md 都已发过，或队列为空）。放新草稿即可提频。")
        return
    meta, body = _parse_frontmatter(open(path, encoding="utf-8").read())
    if dry:
        print("[content_publisher] DRY file=%s title=%s tags=%s published=%s len=%d"
              % (name, meta.get("title"), meta.get("tags"), meta.get("published"), len(body)))
        return
    ok, res = _post(key, meta, body)
    if ok:
        _mark_published(name)
        print("[content_publisher] 已发布 -> %s  (草稿 %s)" % (res, name))
    else:
        print("[content_publisher] %s" % res)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--file", default=None, help="指定草稿路径（不指定则发下一篇未发的）")
    args = ap.parse_args()
    run(dry=args.dry, draft=args.file)
