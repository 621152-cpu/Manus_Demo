"""
联网搜索工具 — 多 Provider 支持
============================================================
调用优先级（按 .env 中 Key 是否配置决定）：
  1. Tavily       TAVILY_API_KEY    → 最佳，返回完整页面 content
  2. Serper       SERPER_API_KEY    → Google 搜索结果 snippet
  3. 百度千帆     QIANFAN_API_KEY   → 百度搜索，适合中文内容

API 规范参考：
  Tavily  : https://docs.tavily.com/sdk/python/reference
            AsyncTavilyClient.search() → results[].content（AI提取的最相关内容）
  Serper  : POST https://google.serper.dev/search
            Header: X-API-KEY | Body: {"q": query, "num": N}
            Response: organic[].snippet / answerBox / knowledgeGraph
  千帆    : POST https://qianfan.baidubce.com/v2/ai_search/web_search
            Header: Authorization: Bearer <key>
            Body: {"messages": [{"role":"user","content":query}], "search_source":"baidu_search_v2"}
            Response: search_results[].title / .url / .content
"""

import os
import asyncio
import httpx
from dataclasses import dataclass, field
from typing import Any


# ── 数据结构 ──────────────────────────────────────────────────

@dataclass
class SearchItem:
    """单条搜索结果"""
    title:   str
    url:     str
    content: str   # 从页面提取的相关内容（最重要的字段）
    score:   float = 1.0


@dataclass
class SearchResult:
    """搜索工具的完整返回"""
    provider: str             # "tavily" | "serper" | "baidu_qianfan" | "none"
    query:    str
    results:  list[SearchItem] = field(default_factory=list)
    answer:   str = ""        # AI 生成的摘要（Tavily/Baidu有，Serper可能有）
    error:    str = ""        # 出错时的描述


# ── 主入口：自动选择 Provider ─────────────────────────────────

async def web_search(query: str, max_results: int = 5) -> SearchResult:
    """
    联网搜索主入口。
    按优先级依次尝试：Tavily → Serper → 百度千帆
    任意一个成功即返回。
    """
    providers = [
        ("Tavily",       os.getenv("TAVILY_API_KEY",   ""), _search_tavily),
        ("Serper",       os.getenv("SERPER_API_KEY",   ""), _search_serper),
        ("百度千帆",     os.getenv("QIANFAN_API_KEY",  ""), _search_baidu),
    ]

    for name, key, fn in providers:
        if _key_valid(key):
            print(f"     🔌 使用搜索引擎：{name}")
            try:
                result = await fn(query, max_results, key)
                if result.results:
                    return result
                print(f"     ⚠️  {name} 返回空结果，尝试下一个 Provider")
            except Exception as e:
                print(f"     ❌  {name} 调用失败：{e}")

    return SearchResult(
        provider="none",
        query=query,
        error="所有搜索 Provider 均不可用，请在 .env 中配置至少一个 API Key",
    )


# ── Provider 1：Tavily ────────────────────────────────────────
# SDK: AsyncTavilyClient  /  search_depth="advanced" 返回最全 content

async def _search_tavily(query: str, max_results: int, api_key: str) -> SearchResult:
    """
    Tavily 搜索
    - search_depth="advanced": 使用 AI 提取每个页面最相关的多段内容（chunks）
    - include_answer=True: 返回 Tavily 基于所有结果生成的摘要
    - chunks_per_source=3: 每个来源最多 3 段 content（每段≤500字符）
    """
    from tavily import AsyncTavilyClient

    client = AsyncTavilyClient(api_key=api_key)
    raw = await client.search(
        query        = query,
        search_depth = "advanced",
        max_results  = max_results,
        include_answer      = True,
        chunks_per_source   = 3,    # 获取更多内容片段
        include_raw_content = False,
    )

    items = []
    for r in raw.get("results", []):
        items.append(SearchItem(
            title   = r.get("title",   ""),
            url     = r.get("url",     ""),
            content = r.get("content", ""),  # AI 提取的最相关内容（可含多 chunk）
            score   = round(r.get("score", 0.0), 3),
        ))

    return SearchResult(
        provider = "tavily",
        query    = query,
        results  = items,
        answer   = raw.get("answer", ""),
    )


# ── Provider 2：Serper（Google） ──────────────────────────────
# POST https://google.serper.dev/search
# Header: X-API-KEY  Body: {"q":..., "num":..., "gl":"cn", "hl":"zh-cn"}

async def _search_serper(query: str, max_results: int, api_key: str) -> SearchResult:
    """
    Serper Google 搜索
    Response 字段:
      organic[].title / .link / .snippet  → 搜索结果
      answerBox.answer / .snippet          → 直接答案框（如有）
      knowledgeGraph.description           → 知识图谱描述（如有）
    """
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY":    api_key,
                "Content-Type": "application/json",
            },
            json={
                "q":   query,
                "num": max_results,
                "gl":  "cn",
                "hl":  "zh-cn",
            },
        )
        resp.raise_for_status()
        raw = resp.json()

    # 提取 answerBox / knowledgeGraph 作为摘要
    answer = ""
    if box := raw.get("answerBox"):
        answer = box.get("answer") or box.get("snippet", "")
    elif kg := raw.get("knowledgeGraph"):
        answer = kg.get("description", "")

    items = []
    for r in raw.get("organic", [])[:max_results]:
        items.append(SearchItem(
            title   = r.get("title",   ""),
            url     = r.get("link",    ""),
            content = r.get("snippet", ""),   # Serper 只有 snippet（较短）
            score   = max(0.0, 1.0 - (r.get("position", 1) - 1) * 0.08),
        ))

    return SearchResult(
        provider = "serper",
        query    = query,
        results  = items,
        answer   = answer,
    )


# ── Provider 3：百度千帆 ──────────────────────────────────────
# POST https://qianfan.baidubce.com/v2/ai_search/web_search
# Header: Authorization: Bearer <key>

async def _search_baidu(query: str, max_results: int, api_key: str) -> SearchResult:
    """
    百度千帆网页搜索
    Response 字段（参考文档 /v2/ai_search/web_search）:
      search_results[].title / .url / .content / .abstract
    注意：messages 仅支持单轮，且 content 限 72 字符
    """
    short_query = query[:72]  # API 限制

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://qianfan.baidubce.com/v2/ai_search/web_search",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "messages":      [{"role": "user", "content": short_query}],
                "search_source": "baidu_search_v2",
                "resource_type_filter": ["web"],
            },
        )
        resp.raise_for_status()
        raw = resp.json()

    items = []
    for r in raw.get("search_results", [])[:max_results]:
        content = r.get("content") or r.get("abstract") or r.get("snippet", "")
        items.append(SearchItem(
            title   = r.get("title", ""),
            url     = r.get("url",   ""),
            content = content,
            score   = 0.85,
        ))

    return SearchResult(
        provider = "baidu_qianfan",
        query    = query,
        results  = items,
        answer   = raw.get("answer", ""),
    )


# ── 工具函数 ──────────────────────────────────────────────────

def _key_valid(key: str) -> bool:
    """检查 API Key 是否有效（非空、非占位符）"""
    return bool(key) and not key.startswith("your-") and not key.startswith("tvly-your") and not key.startswith("sk-your")


def format_search_result_for_llm(step_title: str, result: SearchResult) -> str:
    """
    将搜索结果格式化为 LLM 可阅读的结构化文本。
    这是最终传给 deepseek-reasoner 的内容，要包含完整 content。
    """
    if result.error:
        return f"[{step_title}] 搜索失败：{result.error}"

    lines = [f"【{step_title}】搜索词：{result.query}  来源：{result.provider}"]

    for i, item in enumerate(result.results, 1):
        lines.append(f"\n  来源{i}：{item.title}")
        lines.append(f"  网址：{item.url}")
        lines.append(f"  内容：{item.content}")    # 完整 content，不截断

    if result.answer:
        lines.append(f"\n  AI摘要：{result.answer}")

    return "\n".join(lines)
