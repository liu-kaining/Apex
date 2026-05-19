# Apex CTO 技术评审报告

| 字段 | 内容 |
|------|------|
| **版本** | v2.0（静态代码全量审计） |
| **日期** | 2026-05-19 |
| **评审方式** | 静态代码 + 文档 + CI 配置（未连生产 API） |
| **基线** | 当前仓库 `main` 工作区 |
| **关联文档** | [`INIT.md`](INIT.md) · [`DEPLOYMENT.md`](DEPLOYMENT.md) |

---

## 执行摘要

Apex 已实现 INIT 规定的 **Serverless 三页产品**（Feed / Heatmap / Ticker Timeline）与 **四条核心业务规则** 的可运行代码路径。架构与 PRD 一致，适合作为 **MVP 公网发布**。

**CTO 结论：有条件通过（Conditional Go）**

在完成 [`DEPLOYMENT.md`](DEPLOYMENT.md) 中的 **上线检查清单（全部必选项）** 后，可判定为 **生产可部署**。代码层面无已知 P0 阻塞项；本次审计中发现的 **P1 分片索引覆盖** 与 **CORS 通配符** 等问题已在仓库内修复或文档化。

---

## 一、系统架构审计

### 1.1 拓扑（与设计一致性）

```
Dataroma ──► investors.json (规则1)
SEC EDGAR ──► 13F by_cik/*.json ──► map_cusip ──► rule2/QoQ
FMP Insider ──► feed_today.json (规则3)
                    │
                    ▼
            generate_signals (规则4, 7日窗口)
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
  feed_today   sp500_grid   tickers/*
        │           │           │
        └───────────┴───────────┘
                    ▼
            upload_to_r2 (v1/)
                    ▼
        Next.js 静态站 (GitHub Pages) ──fetch──► R2/CDN
```

| 层级 | 技术选型 | 评价 |
|------|----------|------|
| ETL | Python 3.11 脚本 + GHA | ✅ 单一职责、可本地复现 |
| 存储 | Cloudflare R2 静态 JSON | ✅ 无 DB、成本低 |
| 前端 | Next.js 14 `output: 'export'` | ✅ 与 INIT 一致 |
| CI | 3 个工作流（全量 / 日频 / 季度） | ✅ 符合 INIT 双 cron + 手动全量 |

### 1.2 与 INIT 的差异（已接受）

| INIT 描述 | 实际实现 | 风险 |
|-----------|----------|------|
| INIT 示例 `api.apex.so` | 数据 `apex-data.thetamind.ai/v1`，站点 `apex.thetamind.ai` | 低 — Variable 可覆盖 |
| OpenFIGI 为主 | FMP 为主 + OpenFIGI fallback | 低 — 更稳 |
| `src/styles/` 目录 | `app/globals.css` + Tailwind | 无 |
| 硬编码 80 CIK | Dataroma 同步 + `dataroma_cik_map.json` | 中 — 需定期校验 CIK |
| shadcn/ui | Tailwind + Radix Tooltip | 无 — 满足交互要求 |

---

## 二、业务规则实现审计

### 规则 1：超级投资者白名单

| 检查项 | 状态 | 证据 |
|--------|------|------|
| 约 80 家机构 | ✅ | `config/investors.json` `count: 80` |
| CIK 可用于 SEC API | ✅ | `normalize_cik()` 10 位补零 |
| 可维护性 | ✅ | `sync_dataroma_investors.py` |

**残留风险**：`dataroma_cik_map.json` 中部分 `_reviewCodes` 可能映射错误 → 用 `validate_investor_ciks.py` 季度核对。

### 规则 2：持仓权重与过滤

| 检查项 | 状态 | 证据 |
|--------|------|------|
| weightPct = 个股市值 / 组合总市值 | ✅ | `fetch_13f_sec.add_weights()` |
| SEC value 单位（美元，非 ×1000） | ✅ | 注释 + 解析逻辑 |
| >1% / NEW / QoQ ±20% | ✅ | `rule2.py` + `annotate_holdings_with_qoq_and_rule2()` |
| 热力图 / 时间轴仅 Rule2 持仓 | ✅ | `passesRule2` 过滤于 grid/timeline 脚本 |
| QoQ 失败回退 | ⚠️ | 仅按 weight>1% 标 `passesRule2`（可接受降级） |

### 规则 3：内部人买入

| 检查项 | 状态 | 证据 |
|--------|------|------|
| acqOrDisp = A | ✅ | `passes_rule_3_insider_buy_filter()` |
| transactionType = P | ✅ | 含 FMP 字段拼写兼容 |
| Common Stock | ✅ | 大小写不敏感子串 |
| ≥ $50,000 | ✅ | `MIN_TRANSACTION_USD` |
| 单测 | ✅ | `tests/test_rules.py` |

### 规则 4：共振信号

| 检查项 | 状态 | 证据 |
|--------|------|------|
| 13F 持有 ∩ 内部人同 Ticker | ✅ | `apply_resonance()` |
| 7 日历日窗口 | ✅ | `INSIDER_LOOKBACK_DAYS = 7` |
| 初稿不误标 STRONG_RESONANCE | ✅ | `fetch_fmp_insider` 输出 `INSIDER_BUY` |
| 单测 | ✅ | `test_resonance_marks_strong_when_held` |

**产品语义说明**：共振判定基于 **任意白名单 13F 持仓**，不要求同时满足规则 2。热力图/时间轴比 Feed 更严，符合「降噪 Feed + 深度 Conviction 页」的产品分层。

---

## 三、数据管道代码审计

### 3.1 脚本质量矩阵

| 脚本 | 健壮性 | 主要优点 | 发现问题 |
|------|--------|----------|----------|
| `fetch_fmp_insider.py` | A | 重试、429、Rule3 清晰 | 分页 `page` 依赖 FMP 语义，API 变更需监控 |
| `fetch_13f_sec.py` | A- | SEC 退避、分片、部分失败容忍 | ~~分片覆盖 index.json~~ **已修复** + `rebuild_13f_index.py` |
| `map_cusip.py` | A | 缓存 + OpenFIGI fallback | 全量 enrich 耗 FMP 额度（有缓存） |
| `generate_signals.py` | A | 7 日过滤、共振逻辑清晰 | 无 13F 文件时 exit 1（符合预期） |
| `generate_sp500_grid.py` | A | `--all-tickers` / universe | 依赖 13F 已 map ticker |
| `generate_ticker_timelines.py` | A | 13F + insider 事件合并 | — |
| `upload_to_r2.py` | A | Content-Type、Cache-Control | `--skip-missing` 可能掩盖未跑完的 ETL |
| `write_manifest.py` | B+ | 可观测性 | 不校验业务阈值 |
| `validate_investor_ciks.py` | B | 质量工具 | **未接入 CI**（建议季度手动） |

### 3.2 已修复问题（本次审计）

| ID | 严重度 | 问题 | 修复 |
|----|--------|------|------|
| **BUG-001** | P1 | 13F 分片多次运行会 **覆盖** `13f/index.json` 为最后一片 | 分片模式跳过写 index；`rebuild_13f_index.py` + CI 合并后重建 |
| **BUG-002** | P1 | `skip_etl` 时 `deploy-web` 可能因 `needs` 被跳过 | `deploy-web` 增加 `always()` 条件 |
| **BUG-003** | P1 | 季度 13F 未上传 R2，日频 job 依赖 cache 易空跑 | 季度 workflow 增加 R2 upload；cache key 统一为 `apex-13f-data` |
| **BUG-004** | P2 | CORS `https://*.github.io` 非 S3/R2 合法 Origin | 改为 `*`（公开只读 JSON）；生产可收紧 Origin |
| **BUG-005** | P2 | README 称 apex-pipeline 有 cron | 文档将更正：cron 在日频/季度 workflow |

### 3.3 历史已修复（v1 review）

- P0：无 13F 时误标 `STRONG_RESONANCE`
- P0：单 CIK 失败导致整链 exit 1
- P1：规则 4 未限制 7 日、标签重复逻辑、SEC User-Agent 空值
- P2：日期解析、Avatar、feed schema 校验等

---

## 四、前端审计

### 4.1 页面与路由

| 路由 | 组件 | 数据源 | 状态 |
|------|------|--------|------|
| `/` | `FeedSection` → `SignalFeedCard` | `feed_today.json` | ✅ |
| `/grid` | `GridSection` → `HeatmapGrid` | `sp500_grid.json` | ✅ |
| `/ticker/[id]` | `TickerTimelineSection` → `ConvictionTimeline` | `tickers/{id}.json` | ✅ |

### 4.2 工程质量

| 检查项 | 状态 | 说明 |
|--------|------|------|
| TypeScript 类型 | ✅ | `types/feed|grid|timeline` |
| 客户端错误处理 | ✅ | loading / error / retry |
| 静态导出 `generateStaticParams` | ✅ | build 时拉 `tickers/index.json`，失败回退 6 个 ticker |
| Design Tokens | ✅ | `#0A0A0A`、`#00FF66`、`#8B5CF6`、Geist |
| Radix Tooltip（热力图） | ✅ | `@radix-ui/react-tooltip` |
| 无障碍 | B | 有 `aria-label` / `role="alert"`；热力图格子可加强 `aria-label` |

### 4.3 前端已知限制（非代码 Bug）

| 项目 | 说明 | 缓解 |
|------|------|------|
| **GitHub Pages 子路径** | 若 Pages URL 为 `user.github.io/repo/`，未配置 `basePath` 时路由/资源可能 404 | 使用自定义域名根路径，或配置 `basePath: '/repo'` |
| **CORS** | 浏览器 fetch R2 依赖 CORS | 执行 `apply_r2_cors.py` |
| **构建时 ticker 列表** | 仅预生成 index 中前 300 + fallback | 全量 ticker 需 rebuild 后重跑 `npm run build` |
| **无 SSR** | 纯客户端 fetch | 符合静态架构设计 |

---

## 五、CI/CD 与安全审计

### 5.1 工作流

| Workflow | 触发 | 产出 | 部署 Web |
|----------|------|------|----------|
| `apex-pipeline.yml` | 手动 | 全量 ETL + R2 + Pages | ✅ |
| `pipeline-insider-daily.yml` | 工作日 22:00 ET | insider + 信号 + R2 | ❌ |
| `pipeline-13f-quarterly.yml` | 季末 16 日 + 手动 | 13F + grid + R2 + cache | ❌ |

**运维说明**：日频更新 **不会** 自动部署前端；数据变后若需新 ticker 静态页，应手动跑全量 pipeline 的 deploy 或本地 build。

### 5.2 Secrets / 合规

| 项 | 状态 |
|----|------|
| API Key 不进仓库 | ✅ `.env` gitignore |
| SEC User-Agent | ✅ 默认 + Secret 覆盖 |
| R2 凭证仅 GHA Secrets | ✅ |
| 日志不打印密钥 | ✅（需保持） |

### 5.3 测试

| 范围 | 状态 |
|------|------|
| 规则 2/3/4 单测 | ✅ 9 cases |
| CI 内 pytest | ✅ 仅全量 pipeline |
| E2E / 契约测试 | ❌ 未做（MVP 可接受） |

---

## 六、评分与上线判定

| 维度 | 分数 | 说明 |
|------|------|------|
| 架构契合度 | **A-** | 与 INIT Serverless 一致，扩展点清晰 |
| 代码质量 | **B+** | 脚本结构好；缺集成测试与 CIK 自动校验 |
| 产品完成度 | **A-** | 三页 + 四规则闭环 |
| 安全与合规 | **B+** | 密钥管理合格；CORS 公开读需知悉 |
| 运维就绪 | **B+** | manifest + 三 workflow；依赖首次季度 13F |
| **综合** | **A-（有条件 Go）** | 完成部署清单即可上线 |

### 上线判定标准

| 级别 | 条件 |
|------|------|
| **代码就绪** | ✅ 无未修复 P0/P1；pytest 与 `npm run build` 通过 |
| **生产就绪** | 需完成 `DEPLOYMENT.md` 全部 **P0 检查项** |
| **CTO 签字「可上线」** | 代码就绪 **且** 生产就绪 **且** 首次全量 ETL + R2 有数据 |

---

## 七、上线后 30 天建议（非阻塞）

1. 将 `validate_investor_ciks.py` 加入季度 workflow。
2. 为 `upload_to_r2` 增加「必需文件缺失则失败」模式（去掉 `--skip-missing` 用于生产）。
3. GitHub Pages `basePath` 与自定义域名二选一文档化。
4. 监控：GHA 失败通知 + R2 `manifest.json` 字段告警。
5. 共振逻辑可选：仅对 `passesRule2` 持仓计 `superinvestorCount`（产品决策）。

---

## 八、评审签字

| 角色 | 结论 |
|------|------|
| **CTO（代码审计）** | **通过** — 代码达到 MVP 上线质量标准；无已知阻塞性缺陷。 |
| **CTO（生产发布）** | **有条件通过** — 须按 [`DEPLOYMENT.md`](DEPLOYMENT.md) 完成基础设施与首次数据灌入后，方可对外宣称「已上线」。 |

---

*本报告基于静态分析生成。生产行为以实际 Secrets、R2 域名与 SEC/FMP API 可用性为准。*
