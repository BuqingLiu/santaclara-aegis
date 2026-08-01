# Lemon Squeezy 配置指南（海外合规代收 · 彻底避开 PayPal 风险）

> 用途：海外客户用信用卡直接付款（USD），Lemon Squeezy 作为 Merchant of Record 替我们处理
> 税务与合规，资金安全到账。这样就不依赖家人 PayPal（有封号+冻结风险）。
> 站点 `index.html` 已预留 `lemon` 字段，注册后把 5 条产品链接粘进去即生效。

## 为什么用 Lemon Squeezy（而不是 PayPal）
- PayPal 本人账户被永久封（PP-L-283471408239，180 天冻结），家人账户违反 ToS 有连带封号风险。
- Lemon Squeezy 是正规的 MoR（代售商），客户刷信用卡付款，合规、稳定、无关联封号风险。
- 客户体验更好：一张链接即可付款，无需登录 PayPal。

## 注册与建店（约 5 分钟）
1. 打开 https://www.lemonsqueezy.com/ 注册账号（用你自己的邮箱，例如 liuxiaochu 或 Buqing Liu 品牌邮箱）。
2. 进入 Dashboard → **New store**，商店名填 `SantaClara Aegis`，货币选 **USD**。
3. 商店开通后进入 **Store → Products → New product**，按下面 5 条逐一创建。

## 要创建的 5 条产品（与站点 SKU 一一对应）
| # | 产品名（Product name） | 价格 (USD) | 对应 index.html 字段 | 说明 |
|---|------------------------|-----------|----------------------|------|
| 1 | SantaClara Aegis · Trial-1 (4 scenarios) | $55 | `trial` 的 lemon | 体验包，破冰用 |
| 2 | SantaClara Aegis · Core-4 | $278 | `core4` 的 lemon | 核心 4 场景 |
| 3 | SantaClara Aegis · Full-23 Library | $694 | `full23` 的 lemon | 全库 23 场景 |
| 4 | SantaClara Aegis · Custom Deposit (50%) | $556 | `custom` 的 lemon | 定制定金（¥8,000 的 50%） |
| 5 | SantaClara Aegis · Pro Subscription (monthly) | $694 / 月 | `pro` 的 lemon | 海外月付订阅 |

> 价格按近似汇率（¥7.2≈$1）设 USD；可在 Lemon 后台随时调。产品类型：
> - 1–4 为 **One-time**（一次性买断/定金）。
> - 5 为 **Subscription**（月付，开 "Subscription" 开关）。

## 拿到链接并粘进站点
1. 每个产品建好后，复制它的 **Checkout / Buy link**（产品页或 "Share" 按钮里的链接，
   形如 `https://store.santaclara-aegis.lemonsqueezy.com/checkout/...` 或 `.../buy/...`）。
2. 打开 `index.html`，搜索 `← Lemon`，会看到 5 处标记：
   - `trial` 行：`lemon:""  /* ← Lemon Trial-1 链接 */`
   - `core4` 行：`lemon:""  /* ← Lemon Core-4 链接 */`
   - `full23` 行：`lemon:""  /* ← Lemon Full-23 链接 */`
   - `custom` 行：`lemon:""  /* ← Lemon Custom 定金链接 */`
   - `pro` 行：`lemon:""  /* ← Lemon Pro 月付链接 */`
3. 把每处 `lemon:""` 改成 `lemon:"你复制的链接"`（保留引号）。**只改引号里的内容，别删 `/* ← ... */` 注释也没关系。**
4. 保存。无需改其他代码——`openPay()` 会自动 `paypal || stripe || lemon` 优先级跳转。

## 验证
- 本地用浏览器打开 `index.html`，点任一方案的「立即订阅」：
  - 若配了 lemon → 新标签页打开 Lemon 付款页（正确）。
  - 若仍为空 → 弹窗显示微信/支付宝二维码 + PayPal 备用（兜底，不漏客户）。
- 推到 GitHub Pages 后，海外客户即可信用卡直付。

## 备注
- Lemon Squeezy 会抽成（约 5% + $0.50/笔），已计入定价余量。
- 资金结算到你在 Lemon 绑定的银行账户（需 KYC，按平台指引完成）。
- 不使用 Stripe（需自己处理税务/compliance），Lemon 作为 MoR 更省心。
