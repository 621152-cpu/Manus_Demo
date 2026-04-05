"""
Verifier 智能体
============================================================
在 Planner → Executor → Reasoner 之后的最后一关。

输入：
  - 用户原始问题
  - Executor 搜索结果的完整文本（用于事实核查）
  - Reasoner 生成的草稿回答

输出：
  - 经过校验和润色的最终回答（异步流式生成）

模型：deepseek-chat（快速，专注于内容编辑）
提示词：prompts/verifier.py
"""

from typing import AsyncGenerator
from openai import AsyncOpenAI

from prompts.verifier import VERIFIER_SYSTEM_PROMPT

VERIFIER_MODEL = "deepseek-chat"


async def run_verifier(
    client: AsyncOpenAI,
    user_question: str,
    search_context: str,
    draft_reply: str,
) -> AsyncGenerator[str, None]:
    """
    流式生成 Verifier 优化后的最终回答。

    Args:
        client:         AsyncOpenAI 客户端（指向 DeepSeek API）
        user_question:  用户原始问题
        search_context: Executor 搜索到的所有内容文本（用于事实核查）
        draft_reply:    Reasoner 生成的草稿回答

    Yields:
        str — 流式文字块，每块为最终回答的一部分
    """
    user_prompt = _build_verifier_prompt(user_question, search_context, draft_reply)

    stream = await client.chat.completions.create(
        model    = VERIFIER_MODEL,
        messages = [
            {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        stream     = True,
        max_tokens = 4096,
        temperature = 0.3,   # 低温：保守编辑，不要随意发挥
    )

    async for chunk in stream:
        text = chunk.choices[0].delta.content or ""
        if text:
            yield text


def _build_verifier_prompt(
    user_question: str,
    search_context: str,
    draft_reply: str,
) -> str:
    """
    组装传给 Verifier 的用户消息，包含：
    - 用户原始问题（明确校验目标）
    - 搜索结果（事实核查依据）
    - 草稿回答（待校验内容）
    """
    search_section = (
        f"【搜索参考资料】\n{search_context}"
        if search_context.strip()
        else "【说明】本次任务未使用搜索工具，仅依赖模型知识。"
    )

    return f"""\
【用户原始问题】
{user_question}

{search_section}

【Reasoner 生成的草稿回答（待校验）】
{draft_reply}

请对上述草稿进行校验和优化，输出最终答案。\
"""
