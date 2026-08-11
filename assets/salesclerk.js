/* SantaClara Aegis — 24/7 Automated Sales Clerk (no backend, runs forever)
 * Bilingual (中文 / EN). Answers common buyer questions and drives to PayPal / WeChat.
 * Zero human in the loop: a visitor can read, get convinced, and pay without talking to anyone.
 */
(function () {
  "use strict";

  var LINKS = {
    custom: "https://www.paypal.com/paypalme/LiuXiaochu2/556", // 50% deposit ¥8,000 (~$556)
    single: "https://www.paypal.com/paypalme/LiuXiaochu2/14",  // Single-1 ¥99 (~$14) — lowest entry
    trial: "https://www.paypal.com/paypalme/LiuXiaochu2/55",    // Trial ¥399 (~$55)
    sample: "samples/sample-scenario.html",
    proposal: "proposal-custom.html",
    tg: "https://t.me/santaclaraaegis_bot"
  };

  // Knowledge base: keywords (lowercase) -> bilingual answer + optional CTA type
  var KB = [
    {
      k: ["是什么", "介绍", "what is", "about", "产品", "product"],
      zh: "SantaClara Aegis 是一套「自动驾驶安全关键场景」订阅库：23 类边缘场景，每类都附带真实遥测 CSV + 可复现 CARLA 仿真脚本 + 合规标注。它的工作就是帮您向监管/客户证明：您的 ADAS/AV 系统能处理那些最刁钻的边界情况（对应 EU NCAP 2026/2030、ISO 21448 SOTIF、UN-R157 安全签字）。",
      en: "SantaClara Aegis is a subscription library of safety-critical AV scenarios — 23 edge-case classes, each with real telemetry CSV + a reproducible CARLA script + compliance tags. Its job: help you prove to regulators/customers that your ADAS/AV stack handles the hardest edge cases (maps to EU NCAP 2026/2030, ISO 21448 SOTIF, UN-R157 sign-off).",
      cta: "custom"
    },
    {
      k: ["场景", "有哪些", "scenario", "scenarios", "类别", "class"],
      zh: "23 类含：强行加塞、遮挡行人、鬼探头、传感器失效、极端天气、路口冲突、违章车辆、施工区、隧道明暗、夜间逆行、公交靠站、两轮车穿插、自动泊车边界、高速汇入、紧急制动规避等。每类都来自真实路采 + 仿真复现。",
      en: "23 classes: aggressive cut-in, occluded pedestrian, jaywalker 'ghost', sensor failure, extreme weather, intersection conflict, reckless vehicle, work zone, tunnel glare, night wrong-way, bus stop, two-wheeler weave, parking edge, highway merge, emergency-brake avoidance, and more — each from real road data + simulation replay.",
      cta: "sample"
    },
    {
      k: ["合规", "法规", "标准", "compliance", "regulation", "ncap", "sotif", "un-r157", "标准"],
      zh: "每个场景都预标注了合规意图：直接对应 EU NCAP 2026 / 2030、ISO 21448 SOTIF、UN-R157、加州 DMV。交付物里的 annotation JSON 让审计/签字人员能一键溯源「这个场景在验证哪条法规」。",
      en: "Every scenario ships with pre-mapped compliance intent: EU NCAP 2026/2030, ISO 21448 SOTIF, UN-R157, CA DMV. The annotation JSON lets your safety/audit team trace 'which regulation does this scenario validate' in one click.",
      cta: "proposal"
    },
    {
      k: ["交付", "交付物", "包含", "deliver", "deliverable", "include", "csv", "数据"],
      zh: "交付四件套：① 遥测 CSV（车辆轨迹/信号/事件）② 可复现 CARLA 仿真脚本（一键重跑）③ 合规标注 JSON ④ 场景报告（含风险等级与边界条件）。拍下后 2 小时内发货，支持微信 / PayPal。",
      en: "Four deliverables: (1) telemetry CSV (trajectories/signals/events), (2) reproducible CARLA script (one-click rerun), (3) compliance annotation JSON, (4) scenario report (risk tier + boundary conditions). Delivered within 2h of payment via WeChat / PayPal.",
      cta: "custom"
    },
    {
      k: ["价格", "多少钱", "报价", "定价", "price", "pricing", "cost", "how much", "收费"],
      zh: "买断：单场景 ¥99 / Trial ¥399 / Core-4 ¥1,999 / Full-23 ¥4,999 / 定制 ¥8,000 起。订阅：Pilot ¥999/月、Pro ¥4,999/月、Enterprise ¥19,999/月。全部支持 7 天无理由退款。对标价的市场（Applied Intuition / Foretellix 企业授权 $30K–500K/年）便宜 10–100 倍。",
      en: "One-time: Single ¥99 / Trial ¥399 / Core-4 ¥1,999 / Full-23 ¥4,999 / Custom from ¥8,000. Subscription: Pilot ¥999/mo, Pro ¥4,999/mo, Enterprise ¥19,999/mo. All with 7-day no-question refund. 10–100x cheaper than market (Applied Intuition / Foretellix enterprise $30K–500K/yr).",
      cta: "single"
    },
    {
      k: ["试用", "体验", "免费", "样例", "trial", "free", "sample", "demo", "试"],
      zh: "三个零风险入口：① 免费样例场景（点下方「免费样例」看真实遥测+报告）② 单场景包 ¥99 先花一杯咖啡钱验真 1 类场景 ③ Trial ¥399 一次性买断 1 类跑通再决定。企业客户还可申请 2 周免费试点转付费。",
      en: "Three zero-risk entries: (1) a free sample scenario (hit 'Free sample' below for real telemetry + report), (2) Single-1 pack at ¥99 to verify one class for the price of a coffee, (3) Trial ¥399 one-time for 1 class to validate before scaling. Enterprise buyers can also request a 2-week free pilot.",
      cta: "single"
    },
    {
      k: ["单场景", "¥99", "便宜", "cheap", "entry", "入门", "最低", "small", "single", "先验真"],
      zh: "想用最低成本先验真？单场景包 ¥99（≈ $14）：任选 1 类安全场景的完整数据（逐帧遥测 CSV + 真值 JSONL + 雷达回波 + 合规报告样例），7 天无理由退款。先花一杯咖啡钱，确认数据是真的、标注是对的，再决定要不要上 Core-4 / Full-23 / 定制。这 ¥99 后续升级全套可全额抵扣。",
      en: "Lowest-cost way to verify: the Single-1 pack at ¥99 (~$14) gives one full scenario class (frame telemetry CSV + ground-truth JSONL + radar + compliance report sample), with 7-day refund. Spend a coffee, confirm the data is real and the tags are right, then decide on Core-4 / Full-23 / Custom. The ¥99 counts fully toward any upgrade.",
      cta: "single"
    },
    {
      k: ["怎么买", "购买", "付款", "支付", "buy", "purchase", "pay", "payment", "下单"],
      zh: "点「立即购买」→ 跳转 PayPal（美元实时到账）/ 或微信收款码扫码。支持 7 天无理由退款，拍下后 2 小时内自动发货。整个流程不需要和任何人说话。单场景 ¥99 也能直接付，先验真再放大。",
      en: "Click 'Buy Now' -> PayPal (USD, instant) / or WeChat QR. 7-day no-question refund; files auto-deliver within 2h of payment. No human needed in the loop. Even the ¥99 single pack pays directly — verify first, scale later.",
      cta: "custom"
    },
    {
      k: ["信任", "靠谱", "为什么", "案例", "trust", "why", "credibility", "who uses"],
      zh: "我们给的是「真跑出来的数据」，不是 PPT：免费样例可验真、7 天无理由退款兜底、转介绍分成 15%、已服务 OEM / Tier-1 / 认证机构级别的精准买家。您先拿样例或 ¥99 单场景自己跑一遍再决定。",
      en: "We sell real run data, not slides: verify via the free sample or the ¥99 single pack, 7-day refund as downside protection, 15% referral commission, already serving OEM / Tier-1 / certification-grade buyers. Run it yourself first.",
      cta: "sample"
    },
    {
      k: ["企业", "定制", "private", "enterprise", "custom", "bespoke", "consult"],
      zh: "企业定制 ¥8,000 起：5 天交付、直接对接工程师、按您的车型/ODD/法规定制场景。先付 50% 定金（$556）启动，尾款交付前结清。🎁 创始会员前 3 位加赠 2 周免费试点。看完整方案点「企业定制方案」。",
      en: "Custom engagement from ¥8,000: 5-day turnaround, direct engineer contact, scenarios tailored to your vehicle/ODD/regulation. 50% deposit ($556) to start. 🎁 First 3 founding buyers also get a free 2-week pilot. See the full plan via 'Enterprise plan'.",
      cta: "proposal"
    },
    {
      k: ["推荐", "佣金", "返利", "referral", "commission", "affiliate", "赚钱", "earn", "介绍"],
      zh: "推荐同行/朋友购买任意套餐，您拿成交额 15% 佣金，成交当天 PayPal 直发。把落地页或 Telegram 机器人转发给做 ADAS/AV 安全的朋友即可，其余我们自动跟进成交。点「Telegram 秒出定制方案」把机器人发给他们。",
      en: "Refer a peer who buys any plan and earn 15% commission, paid same-day via PayPal. Just forward our landing page or Telegram bot to anyone in ADAS/AV safety — we auto-close the rest. Hit 'Telegram instant plan' to send them the bot.",
      cta: "tg"
    }
  ];

  var GREET = {
    zh: "👋 我是 SantaClara Aegis 的 AI 销售顾问，7×24 在线。下面挑个您关心的问题，或直接问我都行。",
    en: "👋 I'm the SantaClara Aegis AI sales assistant, online 24/7. Pick a topic or just ask."
  };
  var FALLBACK = {
    zh: "这个问题我建议直接对接真人工程师（同一天回复）。留个邮箱，我们把定制方案发您：",
    en: "For this one, let's loop in a real engineer (same-day reply). Drop your email and we'll send a tailored plan:"
  };
  var MAILTO = "8069dg@163.com";

  var lang = "zh";
  var panelOpen = false;

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function ctaButtons(type) {
    var wrap = el("div", "sc-cta");
    if (type === "single" || type == null) {
      wrap.appendChild(btn("💰 " + (lang === "zh" ? "先花 ¥99 验真 1 类" : "Verify 1 class $14"), LINKS.single));
    }
    if (type === "custom" || type == null) {
      wrap.appendChild(btn("💳 " + (lang === "zh" ? "立即购买 Custom 定金 $556" : "Buy Custom deposit $556"), LINKS.custom));
    }
    if (type === "trial" || type == null) {
      wrap.appendChild(btn("🧪 " + (lang === "zh" ? "试一试 Trial $55" : "Try Trial $55"), LINKS.trial));
    }
    if (type === "sample" || type == null) {
      wrap.appendChild(btn("🔬 " + (lang === "zh" ? "免费样例" : "Free sample"), LINKS.sample));
    }
    if (type === "proposal" || type == null) {
      wrap.appendChild(btn("📄 " + (lang === "zh" ? "企业定制方案" : "Enterprise plan"), LINKS.proposal));
    }
    wrap.appendChild(btn("🤖 " + (lang === "zh" ? "Telegram 秒出定制方案" : "Telegram instant plan"), LINKS.tg));
    return wrap;
  }

  function btn(label, href) {
    var b = el("a", "sc-btn", label);
    b.href = href;
    b.target = "_blank";
    b.rel = "noopener";
    return b;
  }

  function answerNode(item) {
    var box = el("div", "sc-msg sc-bot");
    box.appendChild(el("div", "sc-text", lang === "zh" ? item.zh : item.en));
    box.appendChild(ctaButtons(item.cta));
    return box;
  }

  function injectCSS() {
    var css = [
      ".sc-fab{position:fixed;right:20px;bottom:20px;z-index:2147483000;width:60px;height:60px;border-radius:50%;",
      "border:none;cursor:pointer;background:linear-gradient(135deg,#0a84ff,#00c2a8);color:#fff;font-size:26px;",
      "box-shadow:0 8px 24px rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center}",
      ".sc-panel{position:fixed;right:20px;bottom:92px;z-index:2147483000;width:370px;max-width:calc(100vw - 40px);",
      "height:520px;max-height:calc(100vh - 120px);background:#0f1420;color:#e8edf5;border-radius:16px;",
      "box-shadow:0 16px 48px rgba(0,0,0,.5);display:flex;flex-direction:column;overflow:hidden;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}",
      ".sc-head{background:linear-gradient(135deg,#0a84ff,#00c2a8);padding:14px 16px;display:flex;align-items:center;justify-content:space-between}",
      ".sc-head .sc-title{font-weight:700;font-size:15px}",
      ".sc-head .sc-lang{display:flex;gap:6px}",
      ".sc-head .sc-lang button{background:rgba(255,255,255,.18);border:none;color:#fff;font-size:12px;padding:4px 8px;border-radius:8px;cursor:pointer}",
      ".sc-head .sc-lang button.on{background:#fff;color:#0a84ff;font-weight:700}",
      ".sc-body{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px}",
      ".sc-msg{max-width:88%;padding:10px 12px;border-radius:12px;font-size:13.5px;line-height:1.55}",
      ".sc-bot{background:#1c2536;align-self:flex-start;border-bottom-left-radius:4px}",
      ".sc-user{background:#0a84ff;align-self:flex-end;border-bottom-right-radius:4px;color:#fff}",
      ".sc-text{white-space:pre-wrap}",
      ".sc-chips{display:flex;flex-wrap:wrap;gap:6px}",
      ".sc-chip{background:#1c2536;border:1px solid #2c3a52;color:#cfe0ff;border-radius:999px;padding:6px 10px;font-size:12.5px;cursor:pointer}",
      ".sc-chip:hover{border-color:#0a84ff}",
      ".sc-cta{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}",
      ".sc-btn{background:#00c2a8;color:#04201b;text-decoration:none;font-weight:700;font-size:12.5px;padding:7px 10px;border-radius:9px}",
      ".sc-btn:hover{filter:brightness(1.08)}",
      ".sc-input{display:flex;gap:8px;padding:10px;border-top:1px solid #1c2536;background:#0b0f18}",
      ".sc-input input{flex:1;background:#1c2536;border:1px solid #2c3a52;color:#e8edf5;border-radius:9px;padding:9px 11px;font-size:13px;outline:none}",
      ".sc-input button{background:#0a84ff;border:none;color:#fff;border-radius:9px;padding:0 14px;font-weight:700;cursor:pointer}",
      ".sc-foot{padding:6px 12px;font-size:11px;color:#7e8aa0;text-align:center;border-top:1px solid #1c2536}",
      ".sc-banner{background:linear-gradient(135deg,#0a84ff,#00c2a8);color:#fff;font-size:13.5px;padding:9px 16px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:center;font-weight:600;z-index:2147483001;position:relative}",
      ".sc-banner b{font-weight:800}",
      ".sc-banner-btn{background:#fff;color:#04201b;border-radius:999px;padding:5px 13px;font-size:12.5px;font-weight:800;text-decoration:none;margin-left:2px}",
      "@media(max-width:480px){.sc-panel{right:8px;bottom:84px;width:calc(100vw - 16px)}}",
      "@media(max-width:480px){.sc-banner{font-size:12.5px;padding:8px 12px}}"
    ].join("");
    var s = el("style");
    s.textContent = css;
    document.head.appendChild(s);
  }

  function addFoundingBanner() {
    var banner = el("div", "sc-banner");
    banner.innerHTML = (lang === "zh"
      ? "🚀 <b>创始会员仅 20 席 · 8/31 关闭</b> · 前 3 位订 Custom ¥8,000 送 <b>2 周免费试点 + 15% 转介绍权</b>。推荐同行，您赚 15% 佣金。"
      : "🚀 <b>Founding cohort · 20 seats · closes 8/31</b> · First 3 Custom ¥8,000 buyers get a <b>free 2-week pilot + 15% referral rights</b>. Refer a peer, earn 15%.");
    var b1 = btn(lang === "zh" ? "立即锁定 ¥8,000" : "Lock ¥8,000 now", LINKS.custom);
    b1.className = "sc-banner-btn";
    var b2 = btn(lang === "zh" ? "推荐赚佣金" : "Refer & earn 15%", LINKS.tg);
    b2.className = "sc-banner-btn";
    banner.appendChild(b1);
    banner.appendChild(b2);
    document.body.insertBefore(banner, document.body.firstChild);
  }

  function build() {
    injectCSS();
    addFoundingBanner();
    var fab = el("button", "sc-fab", "💬");
    fab.setAttribute("aria-label", "AI sales assistant");
    var panel = el("div", "sc-panel");
    panel.style.display = "none";

    var head = el("div", "sc-head");
    var title = el("div", "sc-title", "SantaClara Aegis · AI 销售顾问");
    title.textContent = "SantaClara Aegis · AI 销售顾问";
    var langBox = el("div", "sc-lang");
    var bZh = el("button", "on", "中文");
    var bEn = el("button", "", "EN");
    langBox.appendChild(bZh); langBox.appendChild(bEn);
    head.appendChild(title); head.appendChild(langBox);

    var body = el("div", "sc-body");
    var inputRow = el("div", "sc-input");
    var input = el("input");
    input.type = "text";
    input.placeholder = "问点什么…";
    var send = el("button", "", "发送");
    inputRow.appendChild(input); inputRow.appendChild(send);
    var foot = el("div", "sc-foot", "7 天无理由退款 · 真人工程师同日支持 · 推荐同行赚 15% 佣金");

    panel.appendChild(head); panel.appendChild(body); panel.appendChild(inputRow); panel.appendChild(foot);
    document.body.appendChild(fab); document.body.appendChild(panel);

    function setLang(l) {
      lang = l;
      bZh.className = l === "zh" ? "on" : "";
      bEn.className = l === "en" ? "on" : "";
      input.placeholder = l === "zh" ? "问点什么…" : "Ask anything…";
      renderHome();
    }
    bZh.onclick = function () { setLang("zh"); };
    bEn.onclick = function () { setLang("en"); };

    function push(node) { body.appendChild(node); body.scrollTop = body.scrollHeight; }

    function renderHome() {
      body.innerHTML = "";
      push(el("div", "sc-msg sc-bot", GREET[lang]));
      var chips = el("div", "sc-chips");
      var topics = lang === "zh"
        ? ["这是什么？", "场景有哪些？", "合规怎么对应？", "交付物是什么？", "价格多少？", "¥99 先验真？", "能先试用吗？", "怎么买？", "企业定制？", "推荐赚佣金？"]
        : ["What is this?", "Which scenarios?", "Compliance?", "Deliverables?", "Pricing?", "Verify for $14?", "Free trial?", "How to buy?", "Enterprise?", "Referral & 15%?"];
      topics.forEach(function (t, i) {
        var c = el("div", "sc-chip", t);
        c.onclick = function () { ask(KB[i].k[0], true); };
        chips.appendChild(c);
      });
      push(chips);
    }

    function match(text) {
      var q = (text || "").toLowerCase();
      for (var i = 0; i < KB.length; i++) {
        var keys = KB[i].k;
        for (var j = 0; j < keys.length; j++) {
          if (q.indexOf(keys[j].toLowerCase()) >= 0) return KB[i];
        }
      }
      return null;
    }

    function ask(text, fromChip) {
      if (!fromChip) {
        var u = el("div", "sc-msg sc-user", text);
        push(u);
      }
      var hit = match(text);
      if (hit) {
        push(answerNode(hit));
      } else {
        var fb = el("div", "sc-msg sc-bot", FALLBACK[lang]);
        var m = el("a", "sc-btn", lang === "zh" ? "✉ 留邮箱对接工程师" : "✉ Leave email");
        m.href = "mailto:" + MAILTO + "?subject=" + encodeURIComponent("SantaClara Aegis 定制咨询") + "&body=" + encodeURIComponent("您好，我想了解企业定制方案，我的邮箱是：");
        m.target = "_blank";
        fb.appendChild(m);
        push(fb);
      }
    }

    fab.onclick = function () {
      panelOpen = !panelOpen;
      panel.style.display = panelOpen ? "flex" : "none";
      fab.textContent = panelOpen ? "✕" : "💬";
      if (panelOpen) renderHome();
    };
    function submit() {
      var v = input.value.trim();
      if (!v) return;
      input.value = "";
      ask(v, false);
    }
    send.onclick = submit;
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") submit(); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", build);
  } else {
    build();
  }
})();
