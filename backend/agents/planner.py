"""
Planner 智能体
============================================================
职责：接收用户消息 → 调用 deepseek-chat（JSON 模式）→ 返回结构化任务计划

提示词位置：backend/prompts/planner.py
工具列表位置：backend/tools/registry.py
"""

import json
import logging

from openai import AsyncOpenAI

from prompts.planner import PLANNER_SYSTEM_PROMPT, PLANNER_FEW_SHOT
from tools.registry import TOOLS

logger = logging.getLogger(__name__)

# Planner 使用 deepseek-chat（快速、支持 JSON 模式）
# Executor 使用 deepseek-reasoner（深度推理）
PLANNER_MODEL = "deepseek-chat"


async def run_planner(client: AsyncOpenAI, user_message: str) -> dict:
    """
    运行 Planner 智能体，将用户请求拆解为有序子任务计划。

    Args:
        client:       AsyncOpenAI 实例（已配置 DeepSeek base_url）
        user_message: 用户原始输入

    Returns:
        {
            "goal":       str,
            "complexity": str,
            "subtasks": [
                {
                    "id":          int,
                    "title":       str,
                    "description": str,
                    "tool":        str,   # "web_search" | "none"
                    "tool_query":  str,
                    "depends_on":  list[int],
                }
            ],
            "raw": str   # 模型原始输出（调试用）
        }
    """
    # 构建 few-shot messages（system + 示例 + 用户）
    messages = (
        [{"role": "system", "content": PLANNER_SYSTEM_PROMPT}]
        + PLANNER_FEW_SHOT
        + [{"role": "user", "content": user_message}]
    )

    try:
        response = await client.chat.completions.create(
            model=PLANNER_MODEL,
            messages=messages,
            response_format={"type": "json_object"},  # 强制 JSON 输出
            temperature=0.3,   # 规划任务需要稳定输出，降低随机性
            max_tokens=2048,
        )
        raw = response.choices[0].message.content or "{}"
        plan = json.loads(raw)

    except json.JSONDecodeError as e:
        logger.warning(f"Planner JSON 解析失败: {e}，raw={raw!r}")
        plan = _fallback_plan(user_message)
        raw  = ""
    except Exception as e:
        logger.error(f"Planner 调用失败: {e}")
        plan = _fallback_plan(user_message)
        raw  = ""

    plan["raw"] = raw
    return plan


def plan_to_steps(plan: dict) -> list[dict]:
    """
    将 Planner 的子任务列表转换为前端 steps 格式，以便直接渲染在 UI 中。

    前端 step 格式：{ id, text, status }
    status: "completed" | "running" | "pending"
    """
    subtasks = plan.get("subtasks", [])
    steps = []
    for t in subtasks:
        tool_tag = " 🔍" if t.get("tool") == "web_search" else ""
        steps.append({
            "id":     t.get("id", len(steps) + 1),
            "text":   f"{t.get('title', '子任务')}{tool_tag}",
            "status": "pending",
        })
    return steps


def _fallback_plan(user_message: str) -> dict:
    """Planner 出错时的降级计划"""
    return {
        "goal":       user_message[:60],
        "complexity": "simple",
        "subtasks": [
            {
                "id":          1,
                "title":       "分析请求",
                "description": "理解并分析用户的核心需求",
                "tool":        "none",
                "tool_query":  "",
                "depends_on":  [],
            },
            {
                "id":          2,
                "title":       "生成回复",
                "description": "根据分析结果生成最终回复",
                "tool":        "none",
                "tool_query":  "",
                "depends_on":  [1],
            },
        ],
    }
