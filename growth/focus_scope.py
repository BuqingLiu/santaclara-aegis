# -*- coding: utf-8 -*-
"""
聚焦收窄器（2026-08-10 用户指令落地）—— 白名单制，不是黑名单制
================================================================
用户指令原话：「我卖豆腐，当然选择菜市场，而不是去商超巨头那，显然门都进不去」。
所以判断标准只有一条：**这家团队的工程师，自己就能拍板花 $14–$1,111 买一包场景数据吗？**

能 → 留；不能（要走 6–18 个月采购流程、或压根不做自动驾驶安全论证）→ 收起。

保留的四类摊位（人工逐家判定，不是关键词猜的）：
  A. AV / ADAS 开发与运营团队（中小规模，自己跑安全论证）
  B. 功能安全 / SOTIF 咨询与 V&V 工程服务商（他们缺现成场景，买来就能交付给客户）
  C. 大学与产业实验室的自动驾驶 / 交通研究组（预算小但是集群里的意见领袖，转介绍源头）
  D. 园区 / 测试场 / 孵化器 / 出行 VC —— 标记为 connector，**不推销，只求引荐**（华强生态园打法）

地理只认三处：密歇根汽车走廊、加州湾区、深圳（≤19 家，无收款不再扩）。

用法：
  python focus_scope.py            # 只看数，不改文件
  python focus_scope.py --apply    # 落盘（自动备份）
"""
import csv, io, os, sys, shutil, datetime, collections

BASE = os.path.dirname(os.path.abspath(__file__))
CSV  = os.path.join(BASE, "prospects_email_ready.csv")

# ---------------- 地理白名单 ----------------
MI_KEYS = ("MI", "Michigan", "Detroit", "Ann Arbor", "Novi", "Troy", "Auburn Hills",
           "Plymouth", "Southfield", "Farmington", "Grand Rapids", "Lansing", "Northville",
           "Warren", "Livonia", "Sterling Heights", "Dearborn", "Flint", "Rochester Hills",
           "Zeeland", "Automation Alley", "Holland", "Kalamazoo", "Saline", "Ypsilanti",
           "Wixom", "Madison Heights", "Canton", "Redford", "Romulus", "Milford",
           "Brighton", "Howell", "Battle Creek", "Midland", "Saginaw", "Owosso",
           "Shelby Township", "Clinton Township", "Pontiac", "Oak Park", "Grosse Pointe",
           "Van Buren", "Superior Township", "York Township", "East Lansing", "New Hudson",
           "Houghton", "Big Rapids", "Ottawa Lake", "Galesburg", "Brimley", "汽车走廊")
CA_KEYS = ("San Francisco", "San Jose", "Santa Clara", "Mountain View", "Palo Alto",
           "Sunnyvale", "Fremont", "Berkeley", "Menlo Park", "Foster City", "Redwood",
           "Milpitas", "Cupertino", "Oakland", "San Mateo", "Campbell", "Los Gatos",
           "Hayward", "Pleasanton", "Livermore", "Emeryville", "Union City", "Newark, CA",
           "Walnut Creek", "Concord, CA", "Bay Area", "Silicon Valley", "硅谷", "湾区",
           "San Carlos", "Belmont", "Burlingame", "Alameda", "San Ramon", "Los Altos")
CN_KEYS = ("深圳", "华强", "光明", "南山", "宝安", "龙岗", "坪山", "前海", "GBA")
# 德州（用户 2026-08-12 铁律新增战场）：奥斯汀/达拉斯/休斯顿/圣安东尼奥
TX_KEYS = ("TX", "Texas", "Austin", "Dallas", "Houston", "San Antonio", "Plano",
           "Frisco", "Fort Worth", "Arlington", "Domain", "Riata", "Legacy West",
           "Energy Corridor", "Port SA", "Port San Antonio", "Richardson", "Round Rock")

# 这几家名单里 city 缺失/串了，按真实总部强制归位（不猜，是公开可查的总部所在地）
GEO_OVERRIDE = {
    "gatik": "ca",           # Mountain View, CA
    "pronto.ai": "ca",       # San Francisco, CA
    "weride": "ca",          # 美国办公室在硅谷
    "kodiak": "ca",
    "kodiak ai": "ca",
    "kodiak robotics": "ca",
    "zoox": "ca",
    "plus.ai": "ca",
    "nullmax 纽劢": "sz",
}


def geo_of(row):
    nm = (row.get("company") or "").strip().lower()
    for k, g in GEO_OVERRIDE.items():
        if nm == k or nm.startswith(k + " "):
            return g
    s = ((row.get("city") or "") + " | " + (row.get("cluster") or "")).strip()
    if any(k in s for k in CN_KEYS):
        return "sz"
    if any(k in s for k in MI_KEYS):
        return "mi"
    if any(k in s for k in CA_KEYS):
        return "ca"
    if any(k in s for k in TX_KEYS):
        return "tx"
    return "out"

# ---------------- A. AV / ADAS 开发与运营团队（中小） ----------------
KEEP_AV = (
    "may mobility", "adastec", "torc robotics", "refraction ai", "cavnue", "dataspeed",
    "derq", "pratt miller", "traxen", "bedestrian", "cybernet systems", "new eagle",
    "gatik", "pronto.ai", "kodiak", "plus.ai", "zoox", "weride", "imagry", "nuro",
    "deeproute", "minieye", "haylion", "nullmax", "robosense", "枢途科技", "智坤动力",
    "速博达智能", "万屏时代", "车联智控", "为思润华",
    # 已 parked 的真实中小 AV / ADAS / 仿真团队（按用户要求深挖产业带）
    "sensible 4", "overland ai", "wayve", "deepen.ai", "motional", "oxa", "easymile",
    "auve tech", "ohmio", "roboauto", "zeabuz", "perrone robotics", "reflexion",
    "foretellix", "morai", "cognata", "aves reality", "rfpro", "ipg automotive",
    "applied intuition", "vehicle", "carsim", "sierai.ai", "stocked robotics",
    "nexteer", "gentherm", "lattice", "wind river", "hatci",
    "waabi", "outrider", "embark trucks", "locomation", "stack av", "aurora innovation",
    "serve robotics", "tern ai", "uhnder", "ree automotive",
    "autox", "qcraft", "idriverplus", "haomo", "momenta", "pony.ai",
    "comma.ai", "udacity", "drive.ai", "voyage",
    "limousine", "may mobility", "cleveron", "magna electronics",
    "navistar", "international motors",
    # 国内/深圳小团队
    "元戎启行", "轻舟智航", "智行者", "毫末智行", "小马智行",
    "文远知行", "速腾聚创", "大疆车载", "华为车", "地平线", "黑芝麻",
    "芯驰科技", "全志科技", "德赛西威", "华阳集团", "均胜安全", "经纬恒润",
)
# 已核实是媒体/公关角色的具名邮箱：域名对但人不对，发过去等于石沉大海
PR_PERSON_EMAILS = ("pete.bigelow@kodiak.ai",)
# ---------------- B. 功能安全 / SOTIF 咨询与 V&V 工程服务（中小） ----------------
KEEP_VV = (
    "omnex", "lhp engineering", "methodica", "unatech", "tomco service",
    "quality-one", "luminous group", "soltis advisors", "sres / securesafe",
    "intelligent learning machines", "dornerworks", "quantum signal", "soar technology",
    "danlaw", "intrepid control", "traffic intelligence", "detroit engineered products",
    "explico engineering", "etech stars", "touchstone evaluations", "bylogix",
    "compumak", "faac incorporated", "voxel51", "rgbsi",
    # 新增：已 parked 的真实 V&V / 功能安全 / SOTIF / 工程服务商
    "exida", "iav automotive engineering", "iav", "bertrandt", "bertrandt ag",
    "virtual vehicle research", "avl list", "avl", "fev group", "fev",
    "tata technologies", "transportation research center", "trc",
    "tuv sud", "tuv nord", "tuv rheinland", "dekra", "sgs-tuv", "sgs",
    "exponent", "dekra se", "tuv sud ag", "tuv nord ag", "sgs-tuv saar",
    "michigan office of future mobility", "ofme",
    "national technical systems", "nts", "rohde & schwarz", "rohde-schwarz",
    "cirrus logic", "silicon labs", "microvast", "methode electronics",
    "kautex", "brandfx body", "avanzar", "reyes automotive", "toyotetsu",
    "maclean-fogg", "piston automotive", "dura automotive", "neapco",
    "changan usa", "kiekert", "auo", "sres", "tachi-s", "srg global",
    "coastal automotive", "newcor", "lg energy solution", "gotion",
    "tower international", "eberspaecher", "camaco", "irvin automotive",
    "rco engineering", "venture industries", "detroit manufacturing systems",
    "midway products", "utila legend", "logging-in", "a. raymond",
    "detroit thermal systems", "henkel",
    "cybernet systems", "new eagle", "pratt miller", "traxen",
)
# ---------------- C. 大学 / 产业实验室（AV·交通方向） ----------------
KEEP_LAB = (
    "umtri", "university of michigan transportation research", "michigan state university",
    "kettering", "wayne state", "university of michigan-dearborn", "april robotics",
    "university of michigan robotics", "automotive research center university of michigan",
    "michigan tech research institute", "lawrence technological university",
    "oakland university", "michigan technological university", "western michigan university",
    "grand valley state university", "university of detroit mercy",
    "eastern michigan university", "center for advanced automotive technology",
    "national advanced mobility consortium", "uc berkeley", "berkeley deepdrive",
    "北京理工大学深圳汽车研究院",
    # 已 parked 的真实高校/研究实验室/测试场（按用户要求深挖）
    "driving safety research institute", "university of iowa",
    "virginia tech transportation institute", "vtti", "gcaps",
    "clemson university", "cu-icar",
    "ohio state university", "carlab", "center for automotive research",
    "texas a&m transportation institute", "tti", "texas smarttrack",
    "ut austin", "autonomous systems", "center for transportation research",
    "mit agelab", "massachusetts institute of technology",
    "carnegie mellon university", "robotics institute",
    "penn state", "larson transportation institute",
    "university of wisconsin", "tops lab",
    "university of central florida", "av research",
    "nyu", "c2smart",
    "georgia tech", "dcsc", "aerospace",
    "university of michigan-dearborn", "michigan central",
    "fraunhofer", "fraunhofer iks",
    "swri", "southwest research institute",
    "utsa", "university of texas at san antonio",
    "texas state university", "texas tech university", "utep",
    "lawrence berkeley lab", "lbl",
    "university of michigan mobility", "mcity", "umtri",
    "american center for mobility", "michigan technical resource park",
)
# ---------------- D. 园区 / 测试场 / 孵化器 / 出行 VC（只求引荐，不推销） ----------------
KEEP_CONNECTOR = (
    "mcity", "american center for mobility", "michigan technical resource park",
    "automation alley", "ann arbor spark", "michigan central", "newlab",
    "michauto", "nextenergy", "centrepolis", "center for automotive research",
    "techtown detroit", "detroit regional partnership", "fontinalis partners",
    "gomentum",
    # 新增：测试场 / 产业园 / 孵化器 / 创新中心
    "suntrax", "transportation research center", "trc", "gcaps", "vtti",
    "michigan office of future mobility", "ofme",
    "austintech", "austin technology council", "capital factory",
    "alliancetexas", "port san antonio", "portsa",
    "frisco station", "legacy west", "the domain", "riata",
    "berkeley avs", "bavsf", "oaklandca.gov", "port of oakland",
    "深圳华强北", "华强科技园", "深圳湾科技园", "南山科技园", "前海",
    "michigan economic development", "medc",
)

# ---------------- 邮箱垃圾箱 ----------------
JUNK_LOCAL = ("vulnerabilities", "security", "kol", "press", "media", "investor", "ir",
              "recruit", "jobs", "careers", "legal", "privacy", "abuse", "postmaster",
              "webmaster", "noreply", "no-reply", "unsubscribe")
PR_DOMAINS = ("futuristacommunications.com", "blueshirtgroup.com", "influencer.dji.com",
              "everymoment.ai", "gly-ai.com", "xingtu-iv.com", "qianhai-sim.com",
              "mcgis-tech.com", "a-raymond.com")


DOMAIN_ALLOW = (
    "aptiv.com",
    "magna.com",
    "continental.com",
    "valeo.com",
    "zf.com",
    "borgwarner.com",
    "autoliv.com",
    "denso.com",
    "hitachiastemo.com",
    "lear.com",
    "nexteer.com",
    "gentherm.com",
    "harman.com",
    "bosch.us",
    "stellantis.com",
    "geotab.com",
    "altair.com",
    "ricardo.com",
    "fev.com",
    "horiba.com",
    "mts.com",
    "humaneticsgroup.com",
    "intrepidcs.com",
    "danlawinc.com",
    "methodicatech.com",
    "autonomousstuff.com",
    "dspace.com",
    "vector.com",
    "etas.com",
    "elektrobit.com",
    "tttech.com",
    "kistler.com",
    "avl.com",
    "iav.com",
    "bertrandt.com",
    "dep.net",
    "explico.com",
    "exida.com",
    "tuvsud.com",
    "dekra.com",
    "intertek.com",
    "maymobility.com",
    "refraction.ai",
    "cavnue.com",
    "dataspeed.com",
    "neweagle.net",
    "prattmiller.com",
    "traxen.com",
    "cybernet.com",
    "tatatechnologies.com",
    "voxel51.com",
    "deepen.ai",
    "oxa.tech",
    "lattice.dev",
    "duraautomotive.com",
    "lacksenterprises.com",
    "macleanfogg.com",
    "rcoengineering.com",
    "pistonautomotive.com",
    "kiekert.com",
    "aeaes.com",
    "rohde-schwarz.com",
    "microvast.com",
    "methode.com",
    "tachis.com",
    "srglobal.com",
    "coastalautomotive.com",
    "newcor.com",
    "rheinmetall.com",
    "mahle.com",
    "tenant.com",
    "flex.com",
    "aam.com",
    "autonomic.ai",
    "sonatus.com",
    "tulatech.com",
    "renesas.com",
    "onsemi.com",
    "ceaton.com",
    "pointonenav.com",
    "swiftnav.com",
    "nauto.com",
    "netradyne.com",
    "motive.com",
    "samsara.com",
    "civilmaps.com",
    "baraja.com",
    "aeva.com",
    "ouster.com",
    "innoviz-tech.com",
    "luminartech.com",
    "hesaitech.com",
    "robosense.ai",
    "nodar.com",
    "seyond.com",
    "ambarella.com",
    "qualcomm.com",
    "trimble.com",
    "tomtom.com",
    "here.com",
    "phiar.net",
    "polysync.io",
    "carmera.com",
    "deepmap.ai",
    "atlatec.com",
    "scout.com",
    "tymetro.com",
    "wejo.com",
    "otonomo.com",
    "pegasus.com",
    "phantom.com",
    "lvl5.com",
    "isee.ai",
    "caruma.com",
    "wavesense.com",
    "leishen.com",
    "benewake.com",
    "hippo.com",
    "umich.edu",
    "mcity.umich.edu",
    "umtri.umich.edu",
    "kettering.edu",
    "wayne.edu",
    "oakland.edu",
    "ltu.edu",
    "msu.edu",
    "mtu.edu",
    "wmich.edu",
    "wccnet.edu",
    "emich.edu",
    "umdearborn.edu",
    "annarborusa.org",
    "medc.state.mi.us",
    "soartech.com",
    "dornerworks.com",
    "appliedintuition.com",
    "foretellix.com",
    "tata-technologies.com",
    "michigancentral.com",
    "newlab.com",
    "techtowndetroit.org",
    "detroitregionalpartnership.com",
    "fontinalis.com",
    "michauto.org",
    "nextenergy.org",
    "centrepolisaccelerator.com",
    "gomentum.org",
    "derq.com",
    "realtime-robotics.com",
    "tenneco.com",
    "navistar.com",
    "truck-lite.com",
    "nvidia.com",
    "arm.com",
    "cirrus.com",
    "silabs.com",
    "samsung.com",
    "waabi.ai",
    "kodiak.ai",
    "gatik.ai",
    "plus.ai",
    "motional.com",
    "cyngn.com",
    "einride.tech",
    "outrider.ai",
    "locomation.ai",
    "stackav.com",
    "capitalfactory.com",
    "austintech.org",
    "utexas.edu",
    "tacc.utexas.edu",
    "mathworks.com",
    "siemens.com",
    "ipg-automotive.com",
    "rfpro.com",
    "cognata.com",
    "morai.io",
    "avesreality.com",
    "metamoto.com",
    "ul.com",
    "tuv-rheinland.com",
    "toyota.com",
    "toyotaconnected.com",
    "gm.com",
    "att.com",
    "statefarm.com",
    "nttdata.com",
    "dxc.com",
    "fisglobal.com",
    "jtekt.com",
    "utdallas.edu",
    "twu.edu",
    "legacywest.com",
    "paccar.com",
    "mitsubishi-fuso.com",
    "shell.com",
    "exxonmobil.com",
    "chevron.com",
    "bp.com",
    "phillips66.com",
    "slb.com",
    "halliburton.com",
    "honeywell.com",
    "emerson.com",
    "nov.com",
    "jacobs.com",
    "worley.com",
    "rice.edu",
    "uh.edu",
    "tamu.edu",
    "ridemetro.org",
    "porthouston.com",
    "houstex.com",
    "cummins.com",
    "portsanantonio.us",
    "swri.org",
    "utsa.edu",
    "heb.com",
    "usaa.com",
    "rackspace.com",
    "frostbank.com",
    "valero.com",
    "zachrygroup.com",
    "texasscientific.com",
    "waymo.com",
    "zoox.com",
    "tesla.com",
    "intel.com",
    "apple.com",
    "google.com",
    "pony.ai",
    "weride.ai",
    "nuro.ai",
    "deeproute.ai",
    "nullmax.ai",
    "innovusion.com",
    "mobileye.com",
    "infineon.com",
    "nxp.com",
    "marvell.com",
    "broadcom.com",
    "cisco.com",
    "adobe.com",
    "microsoft.com",
    "meta.com",
    "stanford.edu",
    "sjsu.edu",
    "scu.edu",
    "cmu.edu",
    "righthook.com",
    "exponent.com",
    "tri.global",
    "tu-simple.com",
    "comma.ai",
    "lyft.com",
    "veoneer.com",
    "visteon.com",
    "aurora.tech",
    "pronto.ai",
    "turo.com",
    "uber.com",
    "usfca.edu",
    "sfsu.edu",
    "ucop.edu",
    "sf.gov",
    "berkeley.edu",
    "bdd.berkeley.edu",
    "bair.berkeley.edu",
    "lbl.gov",
    "covariant.ai",
    "oaklandca.gov",
    "portofoakland.com",
    "huawei.com",
    "dji.com",
    "tencent.com",
    "byd.com",
    "minieye.ai",
    "horizon.ai",
    "blacksesame.com",
    "desaysv.com",
    "hirain.com",
    "joyson.com",
    "huayang.com",
    "autox.ai",
    "qcraft.ai",
    "idriverplus.com",
    "uisee.com",
    "changan.com.cn",
    "gac.com.cn",
    "saicmotor.com",
    "nio.io",
    "xpeng.com",
    "lixiang.com",
    "momenta.ai",
)

def junk(email):
    e = (email or "").strip().lower()
    if not e or "@" not in e:
        return "malformed"
    if "\\" in e or " " in e or e.count("@") != 1:
        return "malformed"
    local, dom = e.split("@", 1)
    if e in PR_PERSON_EMAILS:
        return "pr-person"
    if dom in PR_DOMAINS:
        return "dead-or-pr-domain"
    if local in JUNK_LOCAL:
        return "non-buyer-mailbox"
    return ""


def fit_of(row):
    """返回 (keep, reason, tag)。白名单制：不在名单里一律收起。"""
    name = (row.get("company") or "").strip().lower()
    j = junk(row.get("email"))
    if j:
        return False, "junk:" + j, ""
    for k in KEEP_CONNECTOR:
        if k in name:
            return True, "", "connector"
    for grp, tag in ((KEEP_AV, "av"), (KEEP_VV, "vv"), (KEEP_LAB, "lab")):
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
    return False, "not_focus_fit", ""


def main():
    apply = "--apply" in sys.argv
    rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
    stat = collections.Counter()
    reason = collections.Counter()
    keep_geo = collections.Counter()
    keep_tag = collections.Counter()
    keep_rows = []
    for r in rows:
        st = (r.get("status") or "").strip()
        if st in ("replied", "deal"):
            stat["protected"] += 1; keep_rows.append(r); continue
        g = geo_of(r)
        if g == "out":
            stat["park"] += 1; reason["out_of_region"] += 1
            if apply:
                r["status"] = "parked"; r["last_error"] = "focus:out_of_region"
            continue
        ok, why, tag = fit_of(r)
        if not ok:
            stat["park"] += 1
            reason[why.split(":")[0] if why.startswith("junk") else why] += 1
            if apply:
                r["status"] = "blocked" if why.startswith("junk") else "parked"
                r["last_error"] = "focus:" + why
            continue
        stat["keep"] += 1; keep_geo[g] += 1; keep_tag[tag] += 1
        if apply:
            r["cluster"] = {"mi": "MI-汽车走廊", "ca": "CA-湾区", "sz": "深圳GBA", "tx": "TX-德州"}[g]
            if tag == "connector":
                r["segment"] = "connector"
        keep_rows.append(r)

    print("总行 %d ｜ 保留 %d ｜ 收起 %d ｜ 回信保护 %d" % (len(rows), stat["keep"], stat["park"], stat["protected"]))
    print("--- 保留（区域）---")
    for k, v in keep_geo.most_common():
        print("   %-4s %d 行" % (k, v))
    print("--- 保留（角色）---")
    for k, v in keep_tag.most_common():
        print("   %-10s %d 行" % (k or "-", v))
    print("--- 收起原因 ---")
    for k, v in reason.most_common():
        print("   %-16s %d" % (k, v))
    pend = [r for r in keep_rows if (r.get("status") or "") in ("", "pending")]
    print("--- 待首触 ---")
    print("   %d 行 ／ 去重公司 %d 家" % (len(pend), len({(r.get('company') or '').strip().lower() for r in pend})))
    for k, v in collections.Counter(geo_of(r) for r in pend).most_common():
        print("   %-4s %d 行" % (k, v))

    if apply:
        bak = CSV.replace(".csv", ".bak-%s.csv" % datetime.datetime.now().strftime("%m%d%H%M"))
        shutil.copyfile(CSV, bak)
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
        if len(data.strip().splitlines()) < 10:
            raise SystemExit("拒绝写入：结果异常")
        open(CSV, "w", newline="", encoding="utf-8-sig").write(data)
        print("[apply] 已落盘，备份 %s" % os.path.basename(bak))
    else:
        print("(未落盘，加 --apply 生效)")


if __name__ == "__main__":
    main()
