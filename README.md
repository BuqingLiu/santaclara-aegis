<p align="center">
  <img src="assets/logo.svg" width="72" alt="SantaClara Aegis logo"/>
</p>

<h1 align="center">SantaClara Aegis</h1>

<p align="center">
  <b>自动驾驶安全仿真与场景数据订阅平台</b> &nbsp;·&nbsp;
  Autonomous-driving safety simulation &amp; scenario-data subscription platform
</p>

<p align="center">
  <a href="https://carla.org"><img src="https://img.shields.io/badge/CARLA-0.9.14%20--%200.9.16-blue" alt="CARLA"/></a>
  <a href="docs/scenario-catalog.md"><img src="https://img.shields.io/badge/Scenarios-23%20classes-red" alt="Scenarios"/></a>
  <a href="docs/compliance.md"><img src="https://img.shields.io/badge/Compliance-CA%20DMV%20%7C%20NHTSA-yellow" alt="Compliance"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT%20(open%20layer)-lightgrey" alt="License"/></a>
</p>

---

SantaClara Aegis turns a client's driving domain (ODD) into **reproducible,
labeled safety-simulation evidence** — built on CARLA. We deliver compliant
scenario evidence, per-frame labeled datasets, and audit-ready reports for
AV / ADAS teams, so they can satisfy regulators, train algorithms, and validate
behavior without building a sim stack from scratch.

> 本仓库是**对外开放的参考层**（场景定义、CARLA 客户端、传感装置、地图工具与样本数据）。
> 运行整套仿真的专有核心引擎 `elite/` 仅向订阅客户交付。详见[销售页](index.html)。

## Why teams subscribe

| Pain | SantaClara Aegis |
|---|---|
| CA DMV 许可审查需要场景证据 | 23 类安全关键场景，自动执行、自动评分 |
| 自建仿真栈要 $300K+ 与 3 个月 | 交付即可运行，远程或本地部署 |
| 缺少带标签的训练/验证数据 | 20 Hz 遥测 + 真值事件 + 摄像头帧 + 评分 KPI |
| 缺少可审计报告 | 一条命令产出 DMV 风格合规报告（PDF/MD） |
| 硬件受限 | 笔记本即可运行（低画质、限定参与者、20 Hz 定步长） |

## What's in this repository (open reference layer)

- **`docs/`** — architecture, the **23**-class scenario catalog, data schema,
  API contract, methodology, and compliance mapping.
- **`scenarios/`** — 23 scenario definitions following a stable contract.
- **`simulation/`** — CARLA client, sensor rig, world utilities.
- **`config/` `maps/` `tools/` `data/` `reports/`** — profiles, real-corridor
  (OSM→OpenDRIVE) tooling, utilities, and the compliance report template.
- **`samples/`** — sample manifest, telemetry, and summary.
- **`elite/`** — ⚠ **documentation only**; the proprietary engine is
  subscriber-only (see [`elite/README.md`](elite/README.md)).

## Pricing（人民币 / 美元同屏）

Three subscription tiers (dual currency) plus custom enterprise.
See the **[sales page →](index.html)** (also live at **https://buqingliu.github.io/santaclara-aegis/**)
for the full breakdown, FAQ, demo request, and one-click payment.

| Tier | Best for | 价格（月付） | Price (monthly) |
|---|---|---|---|
| **Pilot** | 评估 / 单场景验证 | **¥999 / 月** | **$139 / mo** |
| **Professional** | 持续场景数据 + API | **¥4,999 / 月** | **$699 / mo** |
| **Enterprise** | 定制场景 / 私有部署 | 定制（年框可议） | Custom |

年付享 2 个月免费。

## 如何购买 · 自动收款

平台支持**在线订阅、自动收款**，客户点击即付、即时开通：

- **💳 信用卡（国际）** — 通过 Stripe Payment Link 收银台，支持 Visa / Mastercard / AmEx 等。
- **💚 微信支付 / 🔵 支付宝** — 国内客户扫码即付。
- **🏦 对公转账 / 合同** — 企业版与定制场景。

> 支付由 Stripe / 微信支付 / 支付宝等持牌机构处理，我们不接触你的卡号与密码。
> 收款链接在 `index.html` 顶部 `PAY` 配置中填写（详见 **[docs/payment-setup.md](docs/payment-setup.md)**）。
> 未配置时，按钮自动引导留资，确保**不漏掉任何客户**。

**立即订阅 / 预约演示：** 打开 [销售页](index.html) → 选择方案 → 点击「立即订阅」完成支付；或邮件 **contact@santaclara-aegis.example**。

## Quick links

- 📖 [Documentation hub](docs/index.md)
- 🧪 [Scenario catalog](docs/scenario-catalog.md)
- 🔌 [API reference](docs/api-reference.md)
- ✅ [Compliance mapping](docs/compliance.md)
- 🚀 [Getting started](docs/getting-started.md)
- 💼 [Sales page](index.html)

---

<p align="center">
  SantaClara Aegis — compliant scenario evidence for autonomous driving.<br/>
  Proprietary engine delivered under commercial subscription. Open reference
  layer published under MIT.
</p>
