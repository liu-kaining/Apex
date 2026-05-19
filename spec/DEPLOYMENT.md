# Apex 上线部署手册

| 字段 | 内容 |
|------|------|
| **版本** | 1.0 |
| **日期** | 2026-05-19 |
| **读者** | 发布负责人 / DevOps |
| **前置** | 已阅读 [`INIT.md`](INIT.md)、[`CTO_REVIEW.md`](CTO_REVIEW.md) |

本文档是 **生产环境首次上线与日常运维** 的操作说明。按顺序执行 **第一节 → 第五节**；全部 **P0 检查项** 打勾后，即达到 CTO 定义的「可对外发布」状态。

---

## 一、架构与数据流（必读）

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ GitHub Actions  │────►│ Cloudflare R2    │◄────│ 用户浏览器       │
│ (Python ETL)    │     │ v1/*.json        │     │ GitHub Pages    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                         ▲
        │                         │ HTTPS GET + CORS
        └─ 不部署 DB ─────────────┘
```

**对外 URL 约定**

| 资源 | 默认路径 |
|------|----------|
| 站点（GitHub Pages） | `https://apex.thetamind.ai` |
| API 根（R2 自定义域） | `https://apex-data.thetamind.ai/v1`（Bucket 内对象前缀 `v1/`） |
| Feed | `{API}/feed_today.json` |
| 热力图 | `{API}/sp500_grid.json` |
| 个股时间轴 | `{API}/tickers/{TICKER}.json` |
| 索引 | `{API}/tickers/index.json` |
| 运维清单 | `{API}/manifest.json` |

---

## 二、上线前准备（一次性）

### 2.1 账号与权限

| # | 任务 | P0 |
|---|------|-----|
| 1 | GitHub 仓库 **Admin** 权限 | ✅ |
| 2 | [Cloudflare](https://dash.cloudflare.com) 账号 + **R2** 已开通 | ✅ |
| 3 | [FMP Premium](https://site.financialmodelingprep.com) API Key | ✅ |
| 4 | 域名：`apex.thetamind.ai`（前端）+ `apex-data.thetamind.ai`（R2） | ✅ |

### 2.2 域名（生产）

| 用途 | 域名 | 示例 URL |
|------|------|----------|
| 前端（GitHub Pages） | `apex.thetamind.ai` | `https://apex.thetamind.ai/grid` |
| 静态 JSON（R2 自定义域） | `apex-data.thetamind.ai` | `https://apex-data.thetamind.ai/v1/feed_today.json` |

**DNS / Cloudflare**

1. **`apex.thetamind.ai`** → GitHub Pages（Settings → Pages → Custom domain）。
2. **`apex-data.thetamind.ai`** → R2 Bucket → Settings → Custom Domains（指向同一 Bucket，对象 Key 仍为 `v1/feed_today.json` 等）。

前端通过 **跨域 fetch** 访问数据域；须在 R2 配置 CORS，允许 Origin `https://apex.thetamind.ai`（见 2.4）。

### 2.3 Cloudflare R2 配置

1. **创建 Bucket**（例如 `apex-data`）。
2. **创建 R2 API Token**  
   - **上传对象**：Object Read & Write 即可（`upload_to_r2.py`）  
   - **脚本自动配 CORS**（`apply_r2_cors.py`）：需要 **Admin Read & Write**；若只有 Object 权限会 `AccessDenied`，请在 Dashboard 手动配 CORS（见 2.4）
3. 记录：
   - Account ID → `R2_ACCOUNT_ID`
   - Access Key ID → `R2_ACCESS_KEY_ID`
   - Secret Access Key → `R2_SECRET_ACCESS_KEY`
   - Bucket 名称 → `R2_BUCKET_NAME`
4. **自定义域名**  
   - R2 → Bucket → Settings → Custom Domains → **`apex-data.thetamind.ai`**  
   - DNS：按 Cloudflare 提示为 `apex-data` 添加 CNAME  
5. **公开读**（二选一）  
   - **A**：Bucket 开启 Public Access（最简单）  
   - **B**：Cloudflare Worker / 规则反代（更安全，自行实现）

### 2.4 应用 CORS（浏览器 fetch 必需）

前端在 GitHub Pages 域名下 **跨域** 请求 R2，必须配置 CORS。

```bash
# 在仓库根目录，.env 已填入 R2 四件套
pip install -r requirements.txt
python data-pipelines/scripts/apply_r2_cors.py
```

默认策略见 [`infrastructure/r2-cors.json`](../infrastructure/r2-cors.json)（允许前端 Origin `https://apex.thetamind.ai` 与本地 `http://localhost:3000`）。

> 若临时用 `*.github.io` 预览，需在 CORS 中追加完整 Origin（不支持 `https://*.github.io` 通配）。

### 2.5 GitHub 仓库 Secrets

路径：**Settings → Secrets and variables → Actions → New repository secret**

| Secret | 必填 | 说明 |
|--------|------|------|
| `FMP_API_KEY` | ✅ | FMP Premium |
| `SEC_USER_AGENT` | ✅ | 格式：`AppName/1.0 (email@domain.com)`，[SEC 要求](https://www.sec.gov/os/webmaster-faq#developers) |
| `R2_ACCOUNT_ID` | ✅ | Cloudflare Account ID |
| `R2_ACCESS_KEY_ID` | ✅ | R2 API Token |
| `R2_SECRET_ACCESS_KEY` | ✅ | R2 API Token |
| `R2_BUCKET_NAME` | ✅ | Bucket 名 |

### 2.6 GitHub 仓库 Variables（可选）

路径：**Settings → Secrets and variables → Actions → Variables**

| Variable | 默认 | 说明 |
|----------|------|------|
| `NEXT_PUBLIC_DATA_API_URL` | `https://apex-data.thetamind.ai/v1` | 前端 build 时注入；**不要**末尾斜杠 |

可选 Secret：`R2_KEY_PREFIX`（默认 `v1/`，一般无需改）。

### 2.7 启用 GitHub Pages

1. **Settings → Pages**
2. **Source** 选择 **GitHub Actions**（不是 Deploy from branch）
3. 首次部署成功后记下 URL（如 `https://<user>.github.io/<repo>/`）

**子路径站点注意**：若 URL 含仓库名子路径，需在 `web-app/next.config.mjs` 增加：

```js
const nextConfig = {
  output: "export",
  basePath: "/<repo-name>",   // 仅 project site 需要
  images: { unoptimized: true },
};
```

使用 **用户站**（`username.github.io`）或 **自定义根域名** 时通常 **不需要** `basePath`。

---

## 三、首次上线执行顺序（P0）

按 **严格顺序** 执行一次；预计耗时 **1–3 小时**（13F 全量受 SEC 限流影响）。

### Step 1：全量数据管道

1. 打开 **Actions → Apex Pipeline (Full) → Run workflow**
2. 参数：
   - `skip_etl`: **false**
   - `skip_deploy`: **false**
3. 等待 **data-etl** 完成，确认日志：
   - `pytest` 通过
   - `fetch_13f_sec` 四个分片 + `rebuild_13f_index.py`
   - `upload_to_r2` 无致命错误

### Step 2：验证 R2 对象

在 R2 控制台或 `curl` 检查（将域名换成你的）：

```bash
curl -sI "https://apex-data.thetamind.ai/v1/feed_today.json"
curl -sI "https://apex-data.thetamind.ai/v1/sp500_grid.json"
curl -sI "https://apex-data.thetamind.ai/v1/tickers/index.json"
curl -sI "https://apex-data.thetamind.ai/v1/manifest.json"
```

期望：`HTTP/2 200`，`content-type: application/json`。

### Step 3：验证前端部署

1. **deploy-web** job 绿勾
2. 打开 Pages URL
3. 检查：
   - 首页 Feed 有卡片或「无信号」空态（非红错）
   - `/grid` 热力图有格子
   - `/ticker/AAPL` 时间轴可打开

若 Feed 报 **CORS / Network**，回到 **2.3** 重跑 `apply_r2_cors.py`。

### Step 4：首次上线检查清单（P0）

复制到 Issue / 飞书，逐项打勾：

```
[ ] R2 四件套 Secret 已配置
[ ] FMP_API_KEY、SEC_USER_AGENT 已配置
[ ] apply_r2_cors.py 已执行
[ ] https://apex-data.thetamind.ai/v1/feed_today.json 返回 200
[ ] https://apex.thetamind.ai 首页 / Grid / Ticker 可访问（且 Feed 无 CORS 报错）
[ ] GitHub Pages Source = GitHub Actions
[ ] 全量 Apex Pipeline 成功
[ ] 浏览器三页（/、/grid、/ticker/AAPL）正常
[ ] manifest.json 中 thirteenFPortfoliosOnDisk ≥ 50（建议 ≥ 70）
```

全部完成后 → **CTO 生产发布签字：可上线**。

---

## 四、日常运维

### 4.1 定时任务（已配置，无需改 cron）

| Workflow | 美东时间 | 作用 |
|----------|----------|------|
| **Apex Insider Daily** | 周一至五 22:00 | insider → 共振 → timelines/grid → **上传 R2** |
| **Apex 13F Quarterly** | 2/5/8/11 月 16 日 00:00 | 80 家 13F 分片拉取 → CUSIP → grid → **上传 R2** + cache |

**重要**：日频 job **依赖** 季度 job 写入的 `apex-13f-data` cache。  
**首次上线必须先跑全量 pipeline**，再等季度；否则日频会 `::warning:: Few or no 13F files`。

### 4.2 手动操作场景

| 场景 | 操作 |
|------|------|
| 只更新数据、不部署前端 | Actions → **Apex Insider Daily** → Run workflow |
| 季度更新 13F | Actions → **Apex 13F Quarterly** → Run workflow |
| 全量重跑 + 部署前端 | **Apex Pipeline (Full)**，`skip_etl=false` |
| 只重新部署前端 | **Apex Pipeline (Full)**，`skip_etl=true`，`skip_deploy=false` |
| 同步 Dataroma 名单 | 全量 pipeline 内已含；或本地 `sync_dataroma_investors.py` |
| 校验 CIK | 本地 `python data-pipelines/scripts/validate_investor_ciks.py` |

### 4.3 本地调试（可选）

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填入密钥

python data-pipelines/scripts/fetch_fmp_insider.py
python data-pipelines/scripts/fetch_13f_sec.py --limit 3
python data-pipelines/scripts/map_cusip.py --enrich-13f-dir data-pipelines/output/13f/by_cik
python data-pipelines/scripts/generate_signals.py
python data-pipelines/scripts/generate_sp500_grid.py --all-tickers
python data-pipelines/scripts/generate_ticker_timelines.py
python data-pipelines/scripts/write_manifest.py
python data-pipelines/scripts/upload_to_r2.py   # 不加 --skip-missing 则缺文件会失败

cd web-app && npm ci && npm run dev
```

### 4.4 新增 Ticker 静态页

`/ticker/[id]` 在 **build 时** 根据 `tickers/index.json` 生成路径（最多 300 个）。

数据新增 ticker 后：

1. 跑 ETL 更新 `tickers/index.json` 并上传 R2  
2. 再跑 **Apex Pipeline** 且 **部署前端**（或本地 `npm run build` 后自行上传 `out/`）

---

## 五、故障排查

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| Feed 一直 Loading 后报错 | CORS 未配置 / 域名错误 | `apply_r2_cors.py`；检查 `NEXT_PUBLIC_DATA_API_URL` |
| Feed 空列表 | 7 日内无 Rule3 信号 | 正常；检查 `feed_today.json` 内容 |
| 无共振标签 | 13F 未拉取或 CUSIP 未映射 | 跑季度/全量 13F + `map_cusip` |
| Grid 报错 404 | `sp500_grid.json` 未上传 | 跑 `generate_sp500_grid` + upload |
| Ticker 页 404 | 该 ticker 不在 build 静态路径 | 重跑 deploy；或访问 fallback 列表内 ticker |
| GHA 13F 全失败 | `SEC_USER_AGENT` 缺失/被拒 | 检查 Secret 格式 |
| GHA map_cusip 慢/失败 | FMP 额度或 Key 无效 | 检查 Premium Key |
| 日频 warning 13F 文件少 | 未跑季度或未 restore cache | 先跑 **13F Quarterly** 或全量 pipeline |

---

## 六、安全与成本

| 项 | 建议 |
|----|------|
| R2 公开读 | 仅 JSON，无 PII；Acceptable for MVP |
| API Key | 仅 GHA Secrets；禁止提交 `.env` |
| FMP 调用 | 依赖 `cusip_ticker_cache.json`；避免频繁删 cache |
| SEC 礼貌爬取 | 保持 `SEC_REQUEST_DELAY_SEC`；勿并发提高 |

---

## 七、文档索引

| 文档 | 用途 |
|------|------|
| [`INIT.md`](INIT.md) | PRD + 架构基准 |
| [`CTO_REVIEW.md`](CTO_REVIEW.md) | 技术评审与 Go/No-Go |
| [`DEPLOYMENT.md`](DEPLOYMENT.md) | 本文 — 上线步骤 |
| [`../README.md`](../README.md) | 开发者快速开始 |

---

## 八、版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-05-19 | 首版：全量静态审计后发布 |

---

**发布负责人签字**

| 项目 | 姓名 | 日期 |
|------|------|------|
| 基础设施（R2/CORS/Secrets） | | |
| 首次全量 ETL | | |
| 前端 Pages 验证 | | |
| CTO 生产 Go | | |
