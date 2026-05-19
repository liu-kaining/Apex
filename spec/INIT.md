# Apex: 核心产品与工程架构基准文档 (v1.0)

## 一、 产品需求文档 (PRD)

### 1. 产品定位

Apex 是一个 Serverless 架构的极简投研 SaaS 平台。它通过自动化融合“超级投资者 13F 报表”与“高管内部交易 Form 4”，提取市场中的**极高确定性共振信号（Resonance Signals）**，为高净值个人和机构提供“降噪版”的操作内参。

### 2. 核心业务逻辑（Cursor 代码实现规则）

* **规则 1：超级投资者白名单 (Superinvestor Pool)**
* 系统需硬编码维护一份包含 80 个顶级机构的 CIK 码列表（如 `0001067983` 对应 Berkshire Hathaway）。


* **规则 2：持仓权重计算 (Conviction Weight)**
* 个股权重 = `某只股票当季期末市值 / 该机构当季美股总市值`。
* *过滤条件*：只关注权重 > 1% 或本季度新建仓/增持幅度 > 20% 的记录。


* **规则 3：高管内部买入过滤 (Insider Buy Filter)**
* 在 FMP 接口返回的数据中，必须严格满足：`acqOrDisp == 'A'` (Acquire) 且 `transactionType == 'P'` (Purchase) 且 `securityName` 包含 'Common Stock'。
* 排除金额过小（< $50,000）的噪音交易。


* **规则 4：共振信号生成 (The Apex Signal)**
* 触发条件：某只股票在最新 13F 中被至少 1 位（或多位）白名单大佬持有，且在过去 7 天内，发生过至少 1 笔满足上述条件的高管买入。



---

## 二、 技术架构白皮书 (Technical Architecture Spec)

### 1. 基础设施拓扑 (Serverless Stack)

* **Compute (ETL Pipelines)**: GitHub Actions (Python 3.11 用于数据获取与清洗，Pandas 处理矩阵)。
* **Storage (Database & API)**: Cloudflare R2 (完全作为静态 JSON 托管，对外暴露只读的自定义域名，如 `api.apex.so/v1/...`)。
* **Frontend (Web App)**: Next.js 14 (App Router, Static Export `output: 'export'`), 托管于 GitHub Pages。

### 2. 目录结构规范 (Monorepo Layout)

请 Cursor 严格按照此目录结构生成代码：

```text
/apex-monorepo
├── .github/workflows/
│   ├── pipeline-13f-quarterly.yml   # 触发器: cron '0 0 16 2,5,8,11 *'
│   └── pipeline-insider-daily.yml   # 触发器: cron '0 22 * * 1-5' (美东盘后)
├── data-pipelines/                  # Python ETL 脚本
│   ├── requirements.txt
│   ├── config/investors.json        # 80个大佬的 CIK 列表
│   ├── scripts/fetch_13f_sec.py     # 请求 SEC EDGAR API
│   ├── scripts/map_cusip.py         # OpenFIGI CUSIP -> Ticker 转换
│   └── scripts/fetch_fmp_insider.py # 请求 FMP Premium API 并生成信号
├── web-app/                         # Next.js 前端
│   ├── src/
│   │   ├── app/                     # App Router 页面 (/, /grid, /ticker/[id])
│   │   ├── components/              # React 组件 (FeedCard, HeatMap, Timeline)
│   │   ├── lib/                     # 封装 Fetch 请求 (获取 R2 上的 JSON)
│   │   └── styles/                  # Tailwind 全局配置
│   ├── package.json
│   └── tailwind.config.ts

```

### 3. 数据层契约 (Cloudflare R2 JSON Schemas)

ETL 脚本最终必须生成以下格式的 JSON 文件上传至 R2，前端直接 fetch 这些文件，**无需任何复杂的动态参数请求**。

**文件 1: `feed_today.json` (核心共振信号流)**

```json
{
  "lastUpdated": "2026-05-19T20:00:00Z",
  "signals": [
    {
      "id": "MSFT-20260519",
      "ticker": "MSFT",
      "companyName": "Microsoft Corp.",
      "signalType": "STRONG_RESONANCE",
      "superinvestorCount": 5,
      "insiderActions": {
        "recentBuyers": ["Nadella Satya"],
        "totalAmountUsd": 2500000,
        "date": "2026-05-18"
      },
      "tags": ["Tech", "52-Week Low", "Cluster Buy"]
    }
  ]
}

```

**文件 2: `sp500_grid.json` (共识热力图)**

```json
{
  "lastUpdated": "2026-05-15T00:00:00Z",
  "grid": [
    {
      "ticker": "AAPL",
      "heldBy": ["0001067983", "0001166559"],
      "totalWeight": 15.4,
      "qOqChange": "INCREASED"
    }
  ]
}

```

---

## 三、 UI/UX 与页面交互规范 (Design System & Components)

### 1. 设计系统 (Design Tokens - Tailwind 配置)

告诉 Cursor 使用 `shadcn/ui` 或纯 Tailwind 实现，风格必须对标 Linear/Vercel。

* **Base Theme**: 纯深色模式 (`bg-black` 或 `bg-zinc-950`)。
* **Typography**: `font-sans` 使用 Inter 或 Geist。数字强制开启 `tabular-nums`。
* **Colors**:
* Background: `#0A0A0A`
* Card Surface: `bg-white/5` (带 `backdrop-blur-md` 和极细的 `border-white/10` 边框)。
* Accent/Signal (买入/利好): 荧光绿 `#00FF66` (在文字或图标上作点缀，切勿大面积使用)。
* Consensus (大佬持有): 电光紫 `#8B5CF6`。
* Text: `text-zinc-100` (主标), `text-zinc-400` (副文)。



### 2. 核心组件开发需求 (Frontend Component Specs)

#### A. 首页信息流卡片 (`<SignalFeedCard />`)

* **结构**：
* **Header**: Ticker (粗体) + 公司全称 (灰色小字) + 右侧 `Badge` (如 "2 Hrs Ago")。
* **Body**: 采用两行极简的 `DataRow` 结构。
* Row 1: 图标(紫) + "Superinvestors" + 右对齐的具体人数及头部大佬头像（Avatar Group）。
* Row 2: 图标(绿) + "Insider Buy" + 右对齐的买入者职务 (e.g., CEO) 及高亮金额 (e.g., `<span class="text-green-400">$1.5M</span>`)。


* **Hover State**: `hover:border-zinc-700 hover:bg-zinc-900 transition-all duration-200`。



#### B. 大佬共识矩阵 (`<HeatmapGrid />`)

* **结构**：类似于 GitHub Contribution Graph。
* **交互**：每个格子是一个 `<div class="w-4 h-4 rounded-sm">`。颜色透明度（Opacity）映射其持仓权重。
* **Tooltip**：必须集成 `Radix UI Tooltip`。当鼠标 Hover 或移动端长按时，浮现黑色背景的弹窗，显示：“Berkshire Hathaway: 5.2% of portfolio”。

#### C. 个股行动时间轴 (`<ConvictionTimeline />`)

* **结构**：垂直线段贯穿左侧 (`border-l border-zinc-800`)。
* **节点设计**：
* `<TimelineItem>` 包含一个状态点（相对于左侧线条绝对定位）。
* 右侧内容区：日期 (text-xs) + 动作描述。
* 根据数据类型区分图标：大佬调仓使用 🏛️ (Bank icon)，高管买入使用 💼 (Briefcase icon)。
