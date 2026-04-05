/* ============================================================
   ManusAI Clone — Vue 3 App (CDN, Options API)
   ============================================================ */

// ── Rich mock file contents ───────────────────────────────────
const FILE_DB = {
  'market_analysis.md': {
    type: 'markdown', size: '8.4 KB',
    content: `# AI Agent 市场竞品分析报告

## 执行摘要

本报告对当前 AI Agent 市场的主要竞争对手进行了全面深入的分析。通过收集公开市场数据、用户反馈及行业报告，对 Manus 的主要竞争对手的产品特性、市场定位和发展趋势进行了系统性评估。

---

## 主要竞争对手分析

### 1. AutoGPT
- **公司性质**：开源项目，GitHub Stars 160,000+
- **核心定位**：自主 AI 代理框架，支持多步骤任务执行
- **优势**：开源社区活跃，高度可定制，技术领先
- **劣势**：使用门槛高，需要较强技术背景，稳定性待提升
- **月活用户**：约 50 万（开发者为主）

### 2. Microsoft Copilot
- **公司性质**：微软旗下产品
- **月活用户**：5,000 万+
- **核心定位**：企业级 AI 工作助手，深度集成 Microsoft 365
- **优势**：企业信赖度高，生态整合完善，安全合规
- **劣势**：创新速度较慢，定制化能力有限，价格较高
- **市场份额**：B2B 市场约 35%

### 3. Anthropic Claude
- **公司估值**：180 亿美元
- **核心定位**：安全可靠的 AI 助手，强调 AI 安全
- **优势**：长上下文窗口（200K tokens），推理能力强
- **劣势**：Agent 能力相对基础，API 价格偏高
- **月活增长**：QoQ 增长 45%

### 4. Google Gemini
- **公司性质**：Google DeepMind
- **核心定位**：多模态 AI，深度集成 Google 生态
- **优势**：多模态能力强，Google 搜索加持
- **劣势**：Agent 独立执行能力较弱，隐私顾虑

### 5. Devin (Cognition AI)
- **公司估值**：20 亿美元
- **核心定位**：首个自主软件工程师 AI Agent
- **优势**：代码生成与调试一体化，端到端开发能力
- **劣势**：场景垂直，仅限软件开发

---

## 市场规模预测

| 年份 | 全球 AI Agent 市场规模 | YoY 增长 |
|------|----------------------|---------|
| 2024 | $52 亿              | —       |
| 2025 | $156 亿             | +200%   |
| 2026 | $387 亿             | +148%   |
| 2027 | $836 亿             | +116%   |

---

## Manus 核心差异化

1. **真正的自主任务执行** — 相比竞争对手，Manus 能完成从研究到结构化输出的完整任务链
2. **多工具无缝协作** — 支持浏览器、代码执行、文件操作等多种工具的协调调用
3. **任务透明度** — 实时展示执行步骤，让用户了解 AI 的工作过程
4. **产出质量** — 生成可直接使用的文件、报告、代码

---

## 战略建议

1. **强化多步骤任务成功率** — 从当前 78% 提升至 90%+，这是最核心的护城河
2. **建立开发者生态** — 开放 API，吸引第三方集成
3. **优先攻占 B 端市场** — 企业客户 ARPU 更高，留存率更好
4. **加强数据安全合规** — 特别针对欧美企业客户
`
  },
  'competitors.csv': {
    type: 'csv', size: '1.2 KB',
    content: `公司,类型,月活用户,估值(亿美元),核心能力,市场定位
AutoGPT,开源框架,50万,N/A,自主代理/开源生态,开发者市场
Microsoft Copilot,企业产品,5000万,N/A,Office集成/企业协作,B2B企业市场
Anthropic Claude,API+产品,800万,180,长上下文/安全AI,通用助手市场
Google Gemini,多模态AI,1亿+,N/A,多模态/搜索整合,消费者市场
Devin (Cognition),代码Agent,10万,20,自主编程/调试,开发者市场
Manus,任务Agent,30万,8,自主任务执行/多工具,通用任务市场`
  },
  'scraper.py': {
    type: 'python', size: '3.8 KB',
    content: `#!/usr/bin/env python3
"""
Web 数据采集脚本
异步并发采集，结果存储为 CSV
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataScraper:
    """异步数据采集器（支持并发控制）"""

    def __init__(self, base_url: str, max_concurrent: int = 5):
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.session = None

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; DataBot/1.0)'},
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def fetch_page(self, url: str) -> dict | None:
        """采集单个页面数据"""
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    return self.parse_page(html, url)
                logger.warning(f"HTTP {resp.status}: {url}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def parse_page(self, html: str, url: str) -> dict:
        """解析页面内容，提取结构化数据"""
        soup = BeautifulSoup(html, 'html.parser')
        return {
            'url': url,
            'title': soup.find('title').text.strip() if soup.find('title') else '',
            'description': self._get_meta(soup, 'description'),
            'price': self._extract_price(soup),
            'timestamp': datetime.now().isoformat(),
        }

    def _get_meta(self, soup, name: str) -> str:
        tag = soup.find('meta', attrs={'name': name})
        return tag.get('content', '') if tag else ''

    def _extract_price(self, soup) -> str:
        price_el = soup.find(class_=['price', 'product-price', 'offer-price'])
        return price_el.text.strip() if price_el else ''

    async def scrape_all(self, urls: list[str]) -> list[dict]:
        """并发采集多个 URL"""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def fetch_with_limit(url):
            async with semaphore:
                return await self.fetch_page(url)

        tasks = [fetch_with_limit(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if r and not isinstance(r, Exception)]

    def save_results(self, results: list[dict], output_dir: str = 'output') -> str:
        """保存采集结果为 CSV"""
        Path(output_dir).mkdir(exist_ok=True)
        df = pd.DataFrame(results)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = f"{output_dir}/results_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"已保存 {len(results)} 条记录至 {csv_path}")
        return csv_path


async def main():
    urls = [
        'https://example.com/products/1',
        'https://example.com/products/2',
        # 继续添加目标 URL...
    ]

    async with DataScraper('https://example.com', max_concurrent=10) as scraper:
        logger.info(f"开始采集 {len(urls)} 个页面...")
        results = await scraper.scrape_all(urls)

        if results:
            csv_path = scraper.save_results(results)
            logger.info(f"采集完成！{len(results)}/{len(urls)} 页面成功")
        else:
            logger.error("未获取到任何数据")


if __name__ == '__main__':
    asyncio.run(main())
`
  },
  'business_plan.md': {
    type: 'markdown', size: '5.6 KB',
    content: `# 商业计划书
**NextGen SaaS 数据管理平台** | Pre-A 轮融资 ¥3,000 万

---

## 市场机会

- **TAM（总目标市场）**：¥2,000 亿
- **SAM（可服务市场）**：¥500 亿
- **SOM（初期目标）**：¥50 亿

### 核心痛点

1. 企业数据孤岛严重，跨部门协作效率低下
2. 现有方案定制化成本高，实施周期长（6–18 个月）
3. 中小企业缺乏技术团队，难以独立推进数字化

---

## 产品方案

### 核心功能

- **智能数据中台** — 统一数据接入，实时处理与分析
- **低代码配置** — 业务人员可自主配置工作流，无需编码
- **AI 决策辅助** — 基于业务数据提供智能建议

### 技术架构

\`\`\`
用户层 → API 网关 → 微服务集群 → 数据层
                        ↓
              AI 引擎 (LLM + RAG + Vector DB)
\`\`\`

---

## 商业模式

| 方案   | 年费       | 目标客户       | 核心功能           |
|--------|------------|----------------|--------------------|
| 基础版 | ¥9,800     | 10–50 人团队   | 核心功能           |
| 专业版 | ¥49,800    | 50–500 人企业  | 全功能 + 优先支持  |
| 企业版 | 定制报价   | 500 人以上     | 私有化部署 + SLA   |

---

## 财务预测

| 年份  | 年收入     | 客户数 | 净利润率 |
|-------|------------|--------|---------|
| 2024  | ¥800 万    | 100    | -45%    |
| 2025  | ¥3,600 万  | 350    | -8%     |
| 2026  | ¥1.2 亿    | 900    | +22%    |

**盈亏平衡点**：2025 年 Q2（客户数达 220 家）

---

## 团队介绍

- **CEO** 张三 — 前阿里巴巴产品总监，10 年互联网经验
- **CTO** 李四 — 前字节跳动架构师，深度学习专家
- **CMO** 王五 — 前腾讯增长负责人，用户增长专家

---

## 融资用途

| 用途     | 金额     | 占比 |
|----------|----------|------|
| 产品研发 | ¥1,500 万 | 50%  |
| 市场营销 | ¥600 万   | 20%  |
| 团队扩张 | ¥600 万   | 20%  |
| 运营储备 | ¥300 万   | 10%  |
`
  }
}

// ── Minimal Markdown → HTML renderer ─────────────────────────
function renderMarkdown(md) {
  if (!md) return ''

  // 1. Extract code blocks
  const codeBlocks = []
  let html = md.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const esc = code.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    codeBlocks.push(`<pre><code>${esc}</code></pre>`)
    return `\x00CB${codeBlocks.length - 1}\x00`
  })

  // 2. Tables (header | separator | body)
  html = html.replace(/^(\|.+)\n\|[\s\-|: ]+\|\n((?:\|.+\n?)+)/gm, (_, hdr, body) => {
    const ths = hdr.split('|').slice(1,-1).map(c => `<th>${inl(c.trim())}</th>`).join('')
    const trs = body.trim().split('\n').map(row => {
      const tds = row.split('|').slice(1,-1).map(c => `<td>${inl(c.trim())}</td>`).join('')
      return `<tr>${tds}</tr>`
    }).join('')
    return `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`
  })

  // 3. Line-by-line processing
  const lines = html.split('\n')
  const out = []
  let listType = null

  function closeList() {
    if (listType) { out.push(listType === 'ul' ? '</ul>' : '</ol>'); listType = null }
  }

  for (const line of lines) {
    // Code block placeholder — pass straight through
    if (/\x00CB\d+\x00/.test(line)) { closeList(); out.push(line); continue }

    // Pre-rendered table HTML
    if (/^<table|^<\/table|^<thead|^<\/thead|^<tbody|^<\/tbody|^<tr|^<\/tr/.test(line.trim())) {
      closeList(); out.push(line); continue
    }

    // Headings
    const h3 = line.match(/^### (.+)/); if (h3) { closeList(); out.push(`<h3>${inl(h3[1])}</h3>`); continue }
    const h2 = line.match(/^## (.+)/);  if (h2) { closeList(); out.push(`<h2>${inl(h2[1])}</h2>`); continue }
    const h1 = line.match(/^# (.+)/);   if (h1) { closeList(); out.push(`<h1>${inl(h1[1])}</h1>`); continue }

    // HR
    if (line.trim() === '---') { closeList(); out.push('<hr>'); continue }

    // UL
    const ul = line.match(/^[-*] (.+)/)
    if (ul) {
      if (listType !== 'ul') { closeList(); out.push('<ul>'); listType = 'ul' }
      out.push(`<li>${inl(ul[1])}</li>`); continue
    }

    // OL
    const ol = line.match(/^\d+\. (.+)/)
    if (ol) {
      if (listType !== 'ol') { closeList(); out.push('<ol>'); listType = 'ol' }
      out.push(`<li>${inl(ol[1])}</li>`); continue
    }

    closeList()

    if (!line.trim()) { out.push(''); continue }
    out.push(`<p>${inl(line)}</p>`)
  }

  closeList()

  // 4. Restore code blocks
  let result = out.join('\n')
  codeBlocks.forEach((cb, i) => { result = result.replace(`\x00CB${i}\x00`, cb) })
  return result
}

// Inline markdown (bold, italic, code, escape HTML)
function inl(text) {
  if (!text) return ''
  return text
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,'<em>$1</em>')
    .replace(/`([^`]+)`/g,'<code>$1</code>')
}

// ── CSV → HTML table ──────────────────────────────────────────
function renderCSV(csv) {
  const rows = csv.trim().split('\n').map(r => r.split(','))
  const [header, ...body] = rows
  const ths = header.map(h => `<th>${h.trim()}</th>`).join('')
  const trs = body.map(row => '<tr>' + row.map(c => `<td>${c.trim()}</td>`).join('') + '</tr>').join('')
  return `<div class="csv-table-wrap"><table class="csv-table"><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table></div>`
}

// ── Python → escaped pre block ────────────────────────────────
function renderPython(code) {
  const esc = code.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
  return `<pre class="code-view"><code>${esc}</code></pre>`
}

// ── Backend config ────────────────────────────────────────────
const API_BASE = 'http://localhost:8000'

// ── Vue 3 App ─────────────────────────────────────────────────
const { createApp } = Vue

createApp({
  data() {
    return {
      inputText: '',
      isTyping: false,
      selectedFile: null,
      showToast: false,
      activeTaskId: 1,

      tasks: [
        { id: 1, title: 'AI竞品市场分析', status: 'completed', total: 8, done: 8, time: '2小时前' },
        { id: 2, title: 'Python爬虫脚本开发', status: 'running',   total: 7, done: 3, time: '进行中' },
        { id: 3, title: '季度商业计划书起草', status: 'pending',   total: 5, done: 0, time: '待处理' },
      ],

      taskMessages: {
        1: [
          {
            id: 101, role: 'user', time: '14:28',
            content: '帮我全面分析当前AI Agent市场的竞品情况，重点关注Manus的主要竞争对手，包括产品特点、市场定位和用户规模，并整理成报告文件。',
            steps: null, files: null
          },
          {
            id: 102, role: 'assistant', time: '14:29',
            content: '好的，我将对 AI Agent 市场进行全面竞品分析。我会搜索最新市场数据，逐一研究各主要竞争对手，最终生成结构化的分析报告和对比数据表。',
            typing: false,
            steps: [
              { id: 1, text: '搜索 AI Agent 市场最新公开数据', status: 'completed' },
              { id: 2, text: '分析 AutoGPT、Copilot、Claude 等主要竞品', status: 'completed' },
              { id: 3, text: '收集各产品用户规模与市场份额数据', status: 'completed' },
              { id: 4, text: '梳理竞品核心优势与劣势', status: 'completed' },
              { id: 5, text: '分析市场机会与差异化空间', status: 'completed' },
              { id: 6, text: '整理数据生成 CSV 竞品对比表', status: 'completed' },
              { id: 7, text: '撰写完整 Markdown 分析报告', status: 'completed' },
              { id: 8, text: '报告审核与优化', status: 'completed' },
            ],
            files: [
              { id: 'f1', name: 'market_analysis.md', contentKey: 'market_analysis.md' },
              { id: 'f2', name: 'competitors.csv',    contentKey: 'competitors.csv' },
            ]
          }
        ],
        2: [
          {
            id: 201, role: 'user', time: '15:42',
            content: '帮我写一个Python爬虫脚本，要求：异步请求、支持并发控制、数据存储为CSV格式，目标是电商平台的商品列表页。',
            steps: null, files: null
          },
          {
            id: 202, role: 'assistant', time: '15:43',
            content: '明白！我将开发一个高性能异步 Python 爬虫，使用 aiohttp 实现并发控制，BeautifulSoup 解析页面结构，pandas 导出 CSV 结果。',
            typing: false,
            steps: [
              { id: 1, text: '分析目标网站结构和数据格式', status: 'completed' },
              { id: 2, text: '设计异步爬虫架构（并发控制）', status: 'completed' },
              { id: 3, text: '实现核心请求与会话管理', status: 'completed' },
              { id: 4, text: '添加数据解析和清洗模块', status: 'running' },
              { id: 5, text: '实现 CSV 数据存储功能', status: 'pending' },
              { id: 6, text: '添加错误处理与重试机制', status: 'pending' },
              { id: 7, text: '代码测试与性能优化', status: 'pending' },
            ],
            files: [
              { id: 'f3', name: 'scraper.py', contentKey: 'scraper.py' },
            ]
          }
        ],
        3: [
          {
            id: 301, role: 'user', time: '16:05',
            content: '帮我起草一份完整的商业计划书，这是面向中小企业的SaaS数据管理平台，目标融资3000万人民币Pre-A轮。',
            steps: null, files: null
          },
          {
            id: 302, role: 'assistant', time: '16:05',
            content: '好的，我将为你起草一份专业的商业计划书，涵盖市场分析、产品规划、商业模式、财务预测和团队介绍等核心章节。现在开始收集行业数据。',
            typing: false,
            steps: [
              { id: 1, text: '研究目标行业和市场规模', status: 'pending' },
              { id: 2, text: '分析竞争格局和差异化定位', status: 'pending' },
              { id: 3, text: '规划产品路线图', status: 'pending' },
              { id: 4, text: '设计商业模式和定价方案', status: 'pending' },
              { id: 5, text: '撰写完整商业计划书', status: 'pending' },
            ],
            files: []
          }
        ]
      }
    }
  },

  computed: {
    activeTask() {
      return this.tasks.find(t => t.id === this.activeTaskId)
    },
    messages() {
      return this.taskMessages[this.activeTaskId] || []
    }
  },

  methods: {
    // ── Task sidebar ──────────────────────────────────────────
    setActiveTask(id) {
      this.activeTaskId = id
      this.$nextTick(() => this.scrollBottom())
    },

    createNewTask() {
      const id = Date.now()
      this.tasks.unshift({ id, title: '新建任务', status: 'pending', total: 0, done: 0, time: '刚刚' })
      this.taskMessages[id] = []
      this.activeTaskId = id
    },

    stepBadgeClass(task) {
      if (task.status === 'completed') return 'done'
      if (task.status === 'running')   return 'run'
      return ''
    },

    // ── Messaging ─────────────────────────────────────────────
    async sendMessage() {
      const content = this.inputText.trim()
      if (!content || this.isTyping) return

      this.inputText = ''
      this.resetTextareaHeight()

      const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

      if (!this.taskMessages[this.activeTaskId]) {
        this.taskMessages[this.activeTaskId] = []
      }

      // 立即显示用户消息
      this.taskMessages[this.activeTaskId].push({
        id: Date.now(), role: 'user', time, content, steps: null, files: null
      })
      await this.$nextTick()
      this.scrollBottom()

      // 显示"规划中..."气泡
      this.isTyping = true

      // 预建 AI 消息对象（plan 到达后才推入消息列表）
      const aiMsg = {
        id: Date.now() + 1, role: 'assistant', time,
        content: '', typing: true, steps: null, files: null
      }
      let aiMsgPushed = false

      // Vue 3 的响应式代理引用。
      // 直接修改 push 前的 aiMsg（原始对象）不会触发视图更新，
      // 必须通过 push 后从数组取回的 Proxy 来修改。
      let rMsg = aiMsg

      const pushAiMsg = async () => {
        if (!aiMsgPushed) {
          this.taskMessages[this.activeTaskId].push(aiMsg)
          aiMsgPushed = true
          // 从数组末尾取回 Vue 包装好的响应式 Proxy
          const msgs = this.taskMessages[this.activeTaskId]
          rMsg = msgs[msgs.length - 1]
          await this.$nextTick()
          this.scrollBottom()
        }
      }

      // ── SSE 流式请求 ──────────────────────────────────────
      try {
        const res = await fetch(`${API_BASE}/api/chat/stream`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ message: content, task_id: this.activeTaskId }),
        })

        if (!res.ok) throw new Error(`HTTP ${res.status}`)

        const reader  = res.body.getReader()
        const decoder = new TextDecoder()
        let   buffer  = ''

        // 读取 SSE 流
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // SSE 消息以 \n\n 分隔
          const messages = buffer.split('\n\n')
          buffer = messages.pop() ?? ''  // 最后一段可能不完整，保留到下次

          for (const raw of messages) {
            if (!raw.trim()) continue

            // 解析 SSE 的 event: / data: 行
            let eventName = 'message'
            let eventData = null
            for (const line of raw.split('\n')) {
              if (line.startsWith('event: '))      eventName = line.slice(7).trim()
              else if (line.startsWith('data: ')) {
                try { eventData = JSON.parse(line.slice(6)) } catch { eventData = {} }
              }
            }
            if (eventData === null) continue

            // ── 事件分发 ────────────────────────────────────
            switch (eventName) {

              case 'planning':
                // 保持"规划中..."气泡，不做额外操作
                break

              case 'plan':
                // Planner 完成 → 关闭规划气泡，显示带 Todo 列表的 AI 消息
                this.isTyping = false
                aiMsg.steps = eventData.steps || []  // push 前设置，随对象一起被 Vue 包装
                await pushAiMsg()                    // push 后 rMsg 指向响应式 Proxy
                break

              case 'step_start': {
                // 某步骤开始 → 通过 rMsg（响应式代理）修改，Vue 才能感知
                const s = rMsg.steps?.find(s => s.id === eventData.step_id)
                if (s) s.status = 'running'
                break
              }

              case 'step_done': {
                // 某步骤完成 → 打勾
                const s = rMsg.steps?.find(s => s.id === eventData.step_id)
                if (s) s.status = 'completed'
                break
              }

              case 'reply':
                // 最终回答的流式文字块 → 通过 rMsg 追加，触发响应式更新
                if (!aiMsgPushed) await pushAiMsg()
                rMsg.content += eventData.text || ''
                await this.$nextTick()
                this.scrollBottom()
                break

              case 'done':
                if (!aiMsgPushed) await pushAiMsg()
                rMsg.typing = false
                break

              case 'error':
                this.isTyping  = false
                if (!aiMsgPushed) await pushAiMsg()
                rMsg.typing   = false
                rMsg.content  = `⚠️ ${eventData.message || '未知错误'}`
                break
            }
          }
        }

      } catch (err) {
        console.error('[ManusAI] SSE 请求失败:', err)
        this.isTyping = false
        if (!aiMsgPushed) await pushAiMsg()
        rMsg.content = `⚠️ 无法连接后端（${err.message}）\n请确认已启动后端服务：\n  cd backend && uvicorn main:app --reload --port 8000`
        rMsg.typing  = false
      } finally {
        this.isTyping = false
      }
    },

    useSuggestion(text) {
      this.inputText = text
      this.$nextTick(() => this.$refs.textarea && this.$refs.textarea.focus())
    },

    // ── File panel ────────────────────────────────────────────
    openFile(file) {
      const db = FILE_DB[file.contentKey] || FILE_DB[file.name] || { type: 'text', size: '—', content: '文件内容暂不可用。' }
      this.selectedFile = { ...file, ...db }
    },

    closeFile() {
      this.selectedFile = null
    },

    renderFileContent(file) {
      if (!file) return ''
      if (file.type === 'markdown') return `<div class="md-content">${renderMarkdown(file.content)}</div>`
      if (file.type === 'csv')      return renderCSV(file.content)
      if (file.type === 'python')   return renderPython(file.content)
      const esc = (file.content || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      return `<pre class="code-view"><code>${esc}</code></pre>`
    },

    typeBadgeClass(file) {
      if (!file) return ''
      if (file.type === 'python') return 'py'
      if (file.type === 'csv')    return 'csv'
      return ''
    },

    async copyContent() {
      if (!this.selectedFile?.content) return
      try {
        await navigator.clipboard.writeText(this.selectedFile.content)
        this.showToast = true
        setTimeout(() => { this.showToast = false }, 2200)
      } catch (_) { /* clipboard not available */ }
    },

    // ── Textarea helpers ──────────────────────────────────────
    autoResize(e) {
      const el = e.target
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 200) + 'px'
    },

    resetTextareaHeight() {
      if (this.$refs.textarea) this.$refs.textarea.style.height = 'auto'
    },

    handleEnter(e) {
      if (e.shiftKey) return // allow Shift+Enter newline
      e.preventDefault()
      this.sendMessage()
    },

    // ── Misc ──────────────────────────────────────────────────
    scrollBottom() {
      const el = this.$refs.messages
      if (el) el.scrollTop = el.scrollHeight
    },

    sleep(ms) {
      return new Promise(r => setTimeout(r, ms))
    },

    formatMessage(content) {
      return (content || '').replace(/\n/g, '<br>')
    }
  },

  mounted() {
    this.$nextTick(() => this.scrollBottom())
  }
}).mount('#app')
