*拿到上述文本后，在 Cursor 的 Composer（Cmd+I 或 Cmd+L）中，使用以下结构化指令让它帮你生成代码：*

> "你现在是顶级全栈工程师与 UI 设计师。请仔细阅读 Context 中的《Apex 核心产品与工程架构基准文档》。
> **第一步（后端/数据流）：**
> 请在根目录初始化 Python 环境，并按照要求编写 `data-pipelines/scripts/fetch_fmp_insider.py` 脚本。使用 `requests` 库拉取 FMP Premium 的 `/v4/insider-trading` 接口。请严格实现文档中的【规则 3】（内部买入过滤），并将清洗后的数据最终输出为 `feed_today.json` 的结构。写出代码，注重错误处理与 API 限流处理。
> **第二步（前端/UI）：**
> 请帮我初始化 `web-app` (Next.js 14)。安装 Tailwind 和 `lucide-react`。然后直接帮我编写首页的主组件 `app/page.tsx` 和 `<SignalFeedCard />` 组件。请严格遵循文档中的 Design Tokens（黑色主题、白/灰文字、绿色/紫色点缀、毛玻璃卡片质感）。数据直接 mock 文档中 `feed_today.json` 的结构即可。"




> **角色与上下文：**
> 继续作为顶级全栈工程师，执行《Apex 核心架构文档》的第二阶段：补全 13F 数据管道与共振算法。
> **任务 1：编写 13F SEC 获取脚本 (`data-pipelines/scripts/fetch_13f_sec.py`)**
> * **目标：** 读取 `config/investors.json` 中的 CIK 列表。使用 `requests` 调用 SEC EDGAR 官方 API (`https://data.sec.gov/submissions/CIK{cik}.json`)。请求头必须包含 User-Agent (例如 `Apex_Data_Bot/1.0 (contact@apex.so)`) 以避免被 SEC 封禁。
> * **逻辑：** 找到最新的一份 `form == "13F-HR"`，提取 `accessionNumber`，并拼接出对应的 XML 文件 URL 下载。
> * **XML 解析：** 使用 `xml.etree.ElementTree` 或 `BeautifulSoup` 解析 SEC 的 13F XML，提取 `nameOfIssuer`, `cusip`, `value` 和 `sshPrnamt` (股数)。将结果按机构存储为结构化的 JSON。
> 
> 
> **任务 2：CUSIP 转 Ticker (`data-pipelines/scripts/map_cusip.py`)**
> * 因为用户已经有 FMP Premium API，请编写一个函数，优先使用 FMP 的 API (`/api/v3/cusip/{cusip}`) 将 13F XML 里的 CUSIP 转换为标准 Ticker。做好缓存（存到本地 JSON 字典）以防重复消耗 API 额度。
> 
> 
> **任务 3：生成共振信号 (`data-pipelines/scripts/generate_signals.py`)**
> * 读取昨天生成的 `feed_today.json`（内部买入数据）和清洗好的 13F 持仓数据。
> * **执行 JOIN 逻辑：** 如果内部买入的 Ticker 同样出现在任何一个大佬的 13F 持仓中，则触发“共振”。
> * 更新 `feed_today.json` 中的 `superinvestorCount` 为实际持有该股票的大佬数量，并将 `signalType` 标记为 `STRONG_RESONANCE`。
> 
> 

---

### 第二步指令：打通 Cloudflare R2 存储层

等第一步代码跑通并生成了带有真实 `superinvestorCount` 的 JSON 后，将以下指令发给 Cursor：

> **角色与上下文：**
> 现在我们需要将生成的数据湖文件上云。我们将使用 Cloudflare R2（兼容 AWS S3 API）作为 Serverless 的数据层。
> **任务：编写 R2 上传脚本 (`data-pipelines/scripts/upload_to_r2.py`)**
> * 请在 `requirements.txt` 中添加 `boto3`。
> * 编写上传脚本，读取 `.env` 中的 `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`。
> * 初始化 boto3 的 s3 client（注意 endpoint_url 的格式为 `https://{ACCOUNT_ID}.r2.cloudflarestorage.com`）。
> * 将 `output/` 目录下的 `feed_today.json` 和 `sp500_grid.json` 上传至 R2。
> * **关键配置：** 上传时，必须设置 `ContentType='application/json'`，并且为了前端跨域读取，建议设置基础的 Cache-Control 头信息。
> 
> 

---

### 第三步指令：GitHub Actions 自动化与前端真实接口对接

前两步的代码确认无误后，发送最后一段指令：

> **角色与上下文：**
> 收尾阶段：我们要实现全自动的 Serverless CI/CD，并让 Next.js 前端消费真实的公网数据。
> **任务 1：编写 GitHub Actions 工作流 (`.github/workflows/apex-pipeline.yml`)**
> * 配置两个触发器：`schedule` (cron 定时任务，每天美东盘后执行) 和 `workflow_dispatch` (允许手动触发)。
> * **Job 1 (Data ETL)：** >   - setup Python 3.11。
> * 安装 `requirements.txt`。
> * 注入 Github Secrets (FMP_API_KEY, R2 相关的凭证)。
> * 顺序执行：fetch_fmp, fetch_13f, generate_signals, upload_to_r2。
> 
> 
> * **Job 2 (Build & Deploy Web App)：** >   - 依赖 Job 1 完成。
> * setup Node.js 20。
> * cd 到 `web-app`，执行 `npm ci` 和 `npm run build`。
> * 使用 `actions/upload-pages-artifact` 和 `actions/deploy-pages` 将 `out/` 目录部署到 GitHub Pages。
> 
> 
> 
> 
> **任务 2：改造 Next.js 前端组件**
> * 修改 `web-app/src/app/page.tsx` 和相关数据抓取逻辑。
> * 移除之前写的 mock-feed 引入。
> * 改为在客户端 (使用 SWR 或 React `useEffect`) 或构建时，通过 `fetch()` 请求 Cloudflare R2 绑定的自定义公开域名（例如：`https://data.apex.so/feed_today.json`）来动态渲染 `<SignalFeedCard />` 组件。请写出健壮的 fetch 逻辑（包含 loading 和 error 状态）。
>