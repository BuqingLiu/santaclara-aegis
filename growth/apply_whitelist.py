# -*- coding: utf-8 -*-
"""Inject DOMAIN_ALLOW (real verified deep-mine domains) into focus_scope.py
so harvested rows for these real companies are classified as KEEP (sendable)."""
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))
VER = os.path.join(BASE, "_mine_all_verified_0812.txt")
FS  = os.path.join(BASE, "focus_scope.py")

# collect verified domains
doms = []
seen = set()
with open(VER, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or "|" not in line:
            continue
        d = line.split("|", 1)[0].strip().lower()
        if d and d not in seen:
            seen.add(d)
            doms.append(d)
print("verified domains to whitelist:", len(doms))

src = open(FS, encoding="utf-8").read()

# 1) inject DOMAIN_ALLOW tuple right after PR_DOMAINS block
allow_block = "DOMAIN_ALLOW = (\n" + "\n".join('    "%s",' % d for d in doms) + "\n)\n"
marker = "def junk(email):"
if marker in src:
    src = src.replace(marker, allow_block + "\n" + marker, 1)

# 2) modify fit_of: add domain-allow check before final not_focus_fit
old = '    for grp, tag in ((KEEP_AV, "av"), (KEEP_VV, "vv"), (KEEP_LAB, "lab")):\n        for k in grp:\n            if k in name:\n                return True, "", tag\n    return False, "not_focus_fit", ""'
new = '''    for grp, tag in ((KEEP_AV, "av"), (KEEP_VV, "vv"), (KEEP_LAB, "lab")):
        for k in grp:
            if k in name:
                return True, "", tag
    # 域名白名单（深扒真实公司，已 DNS 核验）：命中即留
    dom = (row.get("email") or "").split("@")[-1].strip().lower()
    if dom in DOMAIN_ALLOW:
        seg = (row.get("segment") or "").lower()
        if "connector" in seg:
            tag = "connector"
        elif "lab" in seg:
            tag = "lab"
        elif "vv" in seg or seg == "vv":
            tag = "vv"
        else:
            tag = "av"
        return True, "", tag
    return False, "not_focus_fit", ""'''
if old in src:
    src = src.replace(old, new, 1)
else:
    print("WARN: fit_of pattern not found, manual review needed")

open(FS, "w", encoding="utf-8").write(src)
print("focus_scope.py updated with DOMAIN_ALLOW (%d domains) + fit_of domain check" % len(doms))
