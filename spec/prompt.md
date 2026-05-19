*拿到上述文本后，在 Cursor 的 Composer（Cmd+I 或 Cmd+L）中，使用以下结构化指令让它帮你生成代码：*

> "你现在是顶级全栈工程师与 UI 设计师。请仔细阅读 Context 中的《Apex 核心产品与工程架构基准文档》。
> **第一步（后端/数据流）：**
> 请在根目录初始化 Python 环境，并按照要求编写 `data-pipelines/scripts/fetch_fmp_insider.py` 脚本。使用 `requests` 库拉取 FMP Premium 的 `/v4/insider-trading` 接口。请严格实现文档中的【规则 3】（内部买入过滤），并将清洗后的数据最终输出为 `feed_today.json` 的结构。写出代码，注重错误处理与 API 限流处理。
> **第二步（前端/UI）：**
> 请帮我初始化 `web-app` (Next.js 14)。安装 Tailwind 和 `lucide-react`。然后直接帮我编写首页的主组件 `app/page.tsx` 和 `<SignalFeedCard />` 组件。请严格遵循文档中的 Design Tokens（黑色主题、白/灰文字、绿色/紫色点缀、毛玻璃卡片质感）。数据直接 mock 文档中 `feed_today.json` 的结构即可。"
