# 部署与推广手册 · 把 SantaClara Aegis 推出去、卖出去

目标：**让客户搜得到、点得开、付得了**。本仓库已具备
① GitHub Pages 在线销售页 → ② 双币定价与自动收款按钮 → ③ 留资表单兜底。
本手册负责「让人进来」与「让人下单」。

---

## 一、站点已经在线（GitHub Pages）

仓库已启用 GitHub Pages，`index.html` 自动成为可访问网站：

- **线上站点**：https://buqingliu.github.io/santaclara-aegis/
- 每次 `git push` 到 `main`，站点几分钟内部署更新，无需额外操作。

> 若想用自有域名（如 `www.santaclara-aegis.com`）：
> 在仓库 **Settings → Pages → Custom domain** 填域名，并按提示加 DNS 记录即可。

---

## 二、提升「可发现性」（让客户搜得到）

1. **GitHub 仓库元数据**
   - Topics（已设置）：`autonomous-driving, self-driving, adas, carla, simulation,
     safety, scenario, av, autonomous-vehicles, compliance, dmv, dataset`
   - Description（已设置）含关键词，利于站内与谷歌检索。
2. **SEO**：`index.html` 已含 `title / description / og:` 分享卡片，分享到社交平台有图有摘要。
3. **README 即门面**：GitHub 首页直接展示专业 README + 双币定价 + 购买指引。

## 三、把仓库推出去的渠道清单（按优先级）

### A. 开发者 / 技术圈（最容易转化 ADAS 算法团队）
- **Product Hunt** — 发布 "SantaClara Aegis"，打 Autonomous Vehicles / Developer Tools 标签。
- **Hacker News** — 发一条 "Show HN: CARLA-based AV safety scenario subscription" + 链接。
- **稀土掘金 / 思否 / CSDN** — 写中文技术文：《用 CARLA 做 DMV 合规仿真，23 类场景一键跑》。
- **知乎** — 回答「自动驾驶如何做合规验证 / 仿真数据从哪来」并附产品。
- **GitHub Topics / Awesome lists** — 提交到 autonomous-driving / CARLA 相关清单。

### B. 行业 / 商务圈（高客单价）
- **LinkedIn** — 英文帖：面向 AV/ADAS 公司安全负责人，附站点与合规卖点。
- **微信公众号 / 视频号** — 发布「自动驾驶合规仿真」科普 + 案例。
- **X（Twitter）** — 面向国际 AV 社区，附 demo 片段。
- **自动驾驶垂直社群**：Apollo / Autoware 社区、行业微信群 / Slack。

### C. 直接获客（不漏客户）
- 在 **CA DMV AV 许可持有者名单**（公开）中，定向 LinkedIn 触达安全 / 合规负责人。
- 参加 **Automotive World / CES / 上海车展 / 世界人工智能大会** 等，带合规报告样本。

## 四、可直接复制的推广文案

### 推文 / 动态（中文，LinkedIn/微信通用）
> 做自动驾驶合规验证，自建仿真栈要 $300K+ 和 3 个月。我们用 CARLA 把这件事做成
> **订阅制**：23 类安全场景、逐帧标签数据、DMV 风格合规报告，笔记本就能跑。
> 现已上线在线订阅（微信 / PayPal 自动收款）→ https://buqingliu.github.io/santaclara-aegis/

### Tweet / X（英文）
> Show HN-style: SantaClara Aegis turns your driving domain into reproducible,
> labeled AV safety-simulation evidence on CARLA — 23 scenario classes, DMV-style
> compliance reports, subscription API. Live & auto-billing → https://buqingliu.github.io/santaclara-aegis/

### Product Hunt 文案
- **Tagline**: CARLA-based AV safety simulation & scenario-data subscription
- **First comment**: "We turn a client's ODD into reproducible, labeled safety
  evidence — 23 scenario classes, 20 Hz telemetry, DMV-style reports. Subscribe,
  pay by WeChat/PayPal, get data via API."

### 冷启动邮件（给 AV 公司安全负责人）
> 主题：合规场景证据，可否用订阅方式快速补齐？
> 正文：贵司在准备 CA DMV / 监管材料时，是否需要可复现的 23 类安全关键场景证据与
> 逐帧标签数据？我们提供 CARLA 仿真订阅（含 DMV 风格报告），可先在贵司驾驶域跑一套样本。
> 站点与样本报告：https://buqingliu.github.io/santaclara-aegis/ ；或回邮预约演示。

## 五、转化闭环（确保「卖出且收款」）

1. 访客从任意渠道进入站点 → 看场景/合规/定价。
2. 想买 → 点「立即订阅」→ 微信 / PayPal 收银台 → **自动收款、即时开通**。
3. 犹豫 / 企业需求 → 留资表单或「联系销售」→ 邮件进 Formspree → 销售跟进。
4. 站点持续迭代：新增场景、客户案例、demo 视频，保持转化力。

## 六、待补充的高价值内容（让页面更高级）

- [ ] **客户案例 / Logo 墙**（脱敏后可放"某 L4 初创用 Aegis 通过 DMV 材料"）
- [ ] **30 秒 demo 视频 / GIF**（把 CARLA 仿真录屏嵌进 Hero 或 gallery）
- [ ] **互动沙盒**：在线填 ODD → 返回可跑场景清单（进阶）
- [ ] **英文版销售页**（面向海外；当前为中文为主 + 英文标签）
- [ ] **定价页 A/B**：测试年付折扣力度对转化影响

---

> 本手册给出「推 + 收」的完整路径。实际成交取决于流量与跟进；本仓库已把
> **门面、定价、收款、留资**四件套备齐，剩下的就是持续投放与响应线索。
