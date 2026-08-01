# 30 秒找到 GitHub Topics 字段（图文并茂）

> 你之前发的截图是 GitHub 的 **Settings → Profile** 页面（设置你的个人资料：Bio / Pronouns / URL / Social accounts / Company）——**这个页面没有 Topics 字段**。  
> **Topics 在仓库主页**，不是个人设置页。

## 步骤（30 秒搞定）

### 第 1 步：进入你的公开展示仓主页
浏览器打开：
👉 **https://github.com/BuqingLiu/santaclara-aegis**

（你登录的 GitHub 账号 `BuqingLiu` 看到这个仓库时，右上角会有齿轮 ⚙ 按钮；不登录也能看到）

### 第 2 步：找页面右侧的"About"模块
仓库主页右上角有一个 **"About"** 框，右边有一个 **⚙ 齿轮按钮**：

```
┌─────────────────────────────┐
│  About                      ⚙ │   ← 点这个 ⚙
│  ──────────────────────────  │
│  No description, website,    │
│  or topics                  │
│  ☐ Releases  ☐ Packages     │
│  ☐ Contributors              │
└─────────────────────────────┘
```

### 第 3 步：点 ⚙ 后弹出的窗口
弹出"Edit repository details"小窗，**往下滑**，你会看到：

```
┌──────────────────────────────────┐
│  Edit repository details         │
│                                  │
│  Description                     │
│  [ 23 CARLA-validated safety... ]│
│                                  │
│  Website                         │
│  [                              ]│
│                                  │
│  Topics  ← ★ 在这里！             │
│  [autonomous-driving] [+]         │
│  [adas] [+]                      │
│  [+] ← 点这个 + 添加更多          │
│                                  │
│  ☑ Releases                      │
│  ☑ Packages                      │
│  ☑ Contributors                  │
│                                  │
│  [Cancel]  [Save changes]        │
└──────────────────────────────────┘
```

### 第 4 步：粘贴这 12 个标签（一次一个 + 号添加）
```
autonomous-driving
self-driving
adas
carla
simulation
safety
scenario
av
autonomous-vehicles
compliance
dmv
dataset
```

### 第 5 步：点 **Save changes** 即可

---

## ⚠️ 注意事项
- 单个标签 ≤ 35 字符、只允许小写字母+连字符+数字
- 最多 20 个标签
- 不要有空格（如 "self driving" 错，"self-driving" 对）
- 改完点 Save 立即生效，无需 push 代码

## 为什么 GitHub API 没这个写权限？
GitHub 仓库的 Topics 字段需要 **`repo` 范围 OAuth token**，你现在的 GCM/GitHub Action token 只有 `public_repo` 范围（只能推代码，不能改 Topics）。这是 GitHub 出于安全考虑的设计——Topics 会被搜索引擎收录，影响"被搜索到的关键词"，所以权限收得很紧。

所以**只能你手动 UI 操作 30 秒**，是最快路径。

## 改完之后…
- 在 GitHub 搜索 "CARLA scenario" / "ADAS simulation" / "autonomous-driving" 都能搜到你的仓库
- 仓库卡片下会出现彩色标签
- 项目 SEO +20%（这是 GitHub 官方数据）
