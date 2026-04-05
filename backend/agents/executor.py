"""
Executor 智能体
============================================================
职责：
  接收 Planner 的子任务列表
  → 逐一分析每个子任务需要调用的工具及参数
  → 执行工具调用，收集完整的 SearchResult
  → 将所有搜索内容（content）打包传给 LLM 生成最终回答

工具列表  ：backend/tools/registry.py
搜索实现  ：backend/tools/search.py（Tavily / Serper / 百度千帆）
"""

import logging
from typing import Callable, Awaitable

from tools.registry import TOOLS, get_tool
from tools.search   import web_search, SearchResult, format_search_result_for_llm

logger = logging.getLogger(__name__)

EventSender = Callable[[str, dict], Awaitable[None]]


# ══════════════════════════════════════════════════════════════
async def run_executor(plan: dict, send_event: EventSender) -> list[dict]:
    """
    执行 Planner 制定的子任务计划。

    每个子任务：
      1. [分析] 打印 Executor 对工具和参数的决策
      2. [执行] 调用工具，获取 SearchResult（含完整 content）
      3. [日志] 打印工具执行结果（title + 完整 content）
      4. [通知] 向前端推送 step_start / step_done

    Returns:
        list[dict]，每条包含：
          step_id, title, tool, tool_input, search_result, content_for_llm
    """
    subtasks = plan.get("subtasks", [])
    results  = []

    _box("Executor 开始", f"共 {len(subtasks)} 个子任务待执行")

    for subtask in subtasks:
        step_id     = subtask.get("id", 0)
        title       = subtask.get("title", "子任务")
        description = subtask.get("description", "")
        tool_name   = subtask.get("tool", "none")
        tool_query  = subtask.get("tool_query", "")

        # ── ① Executor 分析：决策工具和参数 ─────────────────
        print(f"\n  ┌─ Executor 子任务 [{step_id}] ─────────────────────────")
        print(f"  │  标题：{title}")
        print(f"  │  描述：{description}")
        _log_tool_decision(tool_name, tool_query)

        # 通知前端步骤开始
        await send_event("step_start", {"step_id": step_id})

        # ── ② 工具执行 ───────────────────────────────────────
        search_result: SearchResult | None = None
        content_for_llm = ""
        tool_success    = True

        if tool_name == "web_search":
            search_result, tool_success = await _exec_web_search(
                query=tool_query, step_title=title
            )
            if search_result:
                content_for_llm = format_search_result_for_llm(title, search_result)

        elif tool_name == "none":
            print(f"  │  → 无需工具，依靠模型自身知识完成")

        else:
            registered = [t["name"] for t in TOOLS]
            print(f"  │  ⚠️  未知工具 '{tool_name}'（已注册：{registered}），跳过")

        # ── ③ 日志：打印工具执行结果 ─────────────────────────
        _log_search_result(search_result, tool_success)

        print(f"  └─ 步骤 [{step_id}] {'✅ 完成' if tool_success else '⚠️ 部分完成'}")

        results.append({
            "step_id":        step_id,
            "title":          title,
            "tool":           tool_name,
            "tool_input":     {"query": tool_query} if tool_query else {},
            "search_result":  search_result,
            "content_for_llm": content_for_llm,
            "success":        tool_success,
        })

        # 通知前端步骤完成 → 打勾
        await send_event("step_done", {"step_id": step_id})

    _box("Executor 完成", f"{len(results)} 个子任务全部执行完毕")
    return results


# ── 工具执行函数 ──────────────────────────────────────────────

async def _exec_web_search(query: str, step_title: str) -> tuple[SearchResult | None, bool]:
    """调用联网搜索，返回 (SearchResult | None, 是否成功)"""
    if not query:
        print(f"  │  ⚠️  tool_query 为空，跳过搜索")
        return None, False

    print(f"  │  🔍 发起搜索：query='{query}'")
    try:
        result = await web_search(query, max_results=5)
        if result.error:
            print(f"  │  ❌  搜索返回错误：{result.error}")
            return result, False
        return result, True
    except Exception as e:
        print(f"  │  ❌  搜索异常：{e}")
        from tools.search import SearchResult
        return SearchResult(provider="none", query=query, error=str(e)), False


# ── 日志函数 ──────────────────────────────────────────────────

def _log_tool_decision(tool_name: str, tool_query: str) -> None:
    """打印 Executor 的工具决策分析"""
    info = get_tool(tool_name)
    if tool_name == "none":
        print(f"  │  → [Executor分析] 工具决策：无需工具")
    elif info:
        print(f"  │  → [Executor分析] 工具决策：{tool_name}")
        print(f"  │                   描述：{info['description']}")
        if tool_query:
            print(f"  │                   入参：query = \"{tool_query}\"")
    else:
        print(f"  │  → [Executor分析] 工具：{tool_name}（未注册）")


def _log_search_result(result: SearchResult | None, success: bool) -> None:
    """打印工具调用结果摘要（完整 content 由 main.py 在 Reasoner 输入时统一打印）"""
    if result is None:
        return

    if result.error:
        print(f"  │  ❌  [工具结果] 搜索失败：{result.error}")
        return

    print(f"  │  📥 [工具结果] Provider={result.provider}  共 {len(result.results)} 条结果")
    for i, item in enumerate(result.results, 1):
        title_preview = item.title[:50] + "…" if len(item.title) > 50 else item.title
        print(f"  │       [{i}] {title_preview}  ({item.url[:60]})")
    if result.answer:
        answer_preview = result.answer[:120].replace("\n", " ")
        suffix = "…" if len(result.answer) > 120 else ""
        print(f"  │       AI摘要：{answer_preview}{suffix}")


def _box(title: str, msg: str) -> None:
    bar = "═" * 55
    print(f"\n  {bar}")
    print(f"  ▶  {title}：{msg}")
    print(f"  {bar}")


# ── 格式化函数（供 main.py 使用）────────────────────────────

def build_llm_context(user_question: str, plan: dict, results: list[dict]) -> str:
    """
    将 Planner 计划 + Executor 所有搜索结果拼成 LLM 上下文。
    这个字符串直接作为 user 消息传给 deepseek-reasoner。
    """
    parts = [
        f"# 用户问题\n{user_question}",
        f"\n# 任务计划（由 Planner 生成）",
    ]

    for t in plan.get("subtasks", []):
        tool_note = f"（搜索词：{t['tool_query']}）" if t.get("tool") == "web_search" else ""
        parts.append(f"  {t['id']}. {t['title']}：{t.get('description','')}{tool_note}")

    search_sections = [r["content_for_llm"] for r in results if r["content_for_llm"]]

    if search_sections:
        parts.append("\n# 搜索工具执行结果（请仔细阅读以下内容来回答用户问题）\n")
        parts.extend(search_sections)
    else:
        parts.append("\n# 说明\n本次任务无需搜索工具，请依靠你的知识直接回答。")

    parts.append("\n# 你的任务\n请根据上方的搜索结果，用专业、清晰的中文回答用户的问题。")

    return "\n".join(parts)
