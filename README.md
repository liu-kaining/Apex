# Apex

Apex 是一个 Serverless 架构的极简投研 SaaS 平台。它通过自动化融合「超级投资者 13F 报表」与「高管内部交易 Form 4」，提取市场中的极高确定性共振信号（Resonance Signals），为高净值个人和机构提供「降噪版」的操作内参。

## 文档

| 文档 | 说明 |
|------|------|
| [`spec/INIT.md`](spec/INIT.md) | 产品需求与架构基准（PRD） |
| [`spec/CTO_REVIEW.md`](spec/CTO_REVIEW.md) | CTO 技术评审（静态审计 v2） |
| [`spec/DEPLOYMENT.md`](spec/DEPLOYMENT.md) | **上线部署手册（生产必读）** |

## 快速开始（本地开发）

### Python 数据管道

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填入 FMP_API_KEY、R2、SEC_USER_AGENT

python data-pipelines/scripts/fetch_fmp_insider.py
python data-pipelines/scripts/sync_dataroma_investors.py
python data-pipelines/scripts/fetch_13f_sec.py --limit 5
python data-pipelines/scripts/rebuild_13f_index.py
python data-pipelines/scripts/map_cusip.py --enrich-13f-dir data-pipelines/output/13f/by_cik
python data-pipelines/scripts/generate_signals.py
python data-pipelines/scripts/generate_sp500_grid.py --all-tickers
python data-pipelines/scripts/generate_ticker_timelines.py
python data-pipelines/scripts/write_manifest.py
python data-pipelines/scripts/upload_to_r2.py
```

### Next.js 前端

```bash
cd web-app
npm install
npm run dev    # http://localhost:3000
npm run build  # 静态导出
```

### 测试

```bash
pytest data-pipelines/tests/ -q
```

## CI/CD（GitHub Actions）

| 工作流 | 触发 | 作用 |
|--------|------|------|
| [`apex-pipeline.yml`](.github/workflows/apex-pipeline.yml) | **手动** | 全量 ETL → R2 → 部署 GitHub Pages |
| [`pipeline-insider-daily.yml`](.github/workflows/pipeline-insider-daily.yml) | 美东工作日 22:00 | 日频 insider + 共振 + 上传 R2 |
| [`pipeline-13f-quarterly.yml`](.github/workflows/pipeline-13f-quarterly.yml) | 季末 + 手动 | 80 家 13F 分片 + grid + 上传 R2 |

**首次上线**请按 [`spec/DEPLOYMENT.md`](spec/DEPLOYMENT.md) 执行，不要仅依赖日频 cron。

**Secrets**：`FMP_API_KEY`、`SEC_USER_AGENT`、R2 四件套。  
**Variables**（可选）：`NEXT_PUBLIC_DATA_API_URL`（默认 `https://apex-data.thetamind.ai/v1`）。前端站点：`https://apex.thetamind.ai`。  
**Pages**：Settings → Pages → Source 选 **GitHub Actions**。
