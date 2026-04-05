"""
ManusAI Backend — Planner → Executor → Reasoner 完整 Agent 管线
----------------------------------------------------------------
启动方式：
    cd backend
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

主要端点：
    POST /api/chat/stream  — SSE 实时流式端点（主力）
    POST /api/chat         — 普通 JSON 端点（兼容旧版）
    GET  /api/health       — 健康检查

SSE 事件序列（前端监听）：
    planning   → 正在规划（显示"规划中..."）
    plan       → Planner 完成，附带子任务列表
    step_start → 某步骤开始执行（变为 running 状态）
    step_done  → 某步骤执行完毕（变为 completed 打勾）
    reply      → 最终回答的流式文字块
    done       → 全部完成
    error      → 出现错误
"""

import asyncio
import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI, AuthenticationError, APIConnectionError
from pydantic import BaseModel

from agents.planner  import run_planner, plan_to_steps
from agents.executor import run_executor, build_llm_context
from agents.verifier import run_verifier
from tools.registry  import TOOLS

# ── 环境变量 ──────────────────────────────────────────────────
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "sk-your-api-key-here":
    print("=" * 60)
    print("⚠️  请先在 backend/.env 中填入 DEEPSEEK_API_KEY！")
    print("=" * 60)
    sys.exit(1)

deepseek = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

# ── FastAPI ───────────────────────────────────────────────────
app = FastAPI(title="ManusAI Backend", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Executor 系统提示词 ───────────────────────────────────────
EXECUTOR_SYSTEM_PROMPT = (
    "你是 Manus，一个能够自主完成复杂任务的 AI 助手。"
    "你已经看到 Planner 制定的任务计划，以及各步骤的工具执行结果，"
    "请根据这些信息给出专业、详尽的中文回答。"
    "直接回答用户的问题，不要重复描述执行过程。"
)


# ── 数据模型 ──────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    task_id: int = 1


# ── SSE 辅助 ──────────────────────────────────────────────────
def sse(event: str, data: dict) -> str:
    """格式化一条 SSE 消息"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ══════════════════════════════════════════════════════════════
#  主力端点：SSE 流式接口
# ══════════════════════════════════════════════════════════════
@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    完整 Agent 管线，通过 SSE 实时推送每个阶段的进度：
      1. Planner  → 生成子任务 Todo 清单
      2. Executor → 逐步执行工具，实时打勾
      3. Reasoner → 流式输出最终回答
    """
    queue: asyncio.Queue = asyncio.Queue()

    # ── 后台生产者：运行 Agent 管线，把事件放入队列 ──────────
    async def pipeline():
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            # ── 阶段 1：Planner ───────────────────────────────
            _log_banner(f"用户消息 [{ts}]")
            print(f"  task_id : {req.task_id}")
            print(f"  message : {req.message}\n")

            await queue.put(sse("planning", {}))

            print("🗂️   [Planner] 正在规划任务...\n")
            plan  = await run_planner(deepseek, req.message)
            steps = plan_to_steps(plan)

            _log_plan(plan)

            await queue.put(sse("plan", {
                "goal":  plan.get("goal", ""),
                "steps": steps,
            }))

            # ── 阶段 2：Executor ──────────────────────────────
            async def send_event(event: str, data: dict):
                await queue.put(sse(event, data))

            results = await run_executor(plan, send_event)

            # ── 阶段 3：Reasoner — 缓冲草稿，不直接流式到前端 ───
            _log_banner("[Reasoner] 调用 deepseek-reasoner 生成草稿回答")

            # 把 Planner 计划 + 所有搜索 content 打包成完整上下文
            user_content = build_llm_context(req.message, plan, results)

            # ★ 打印完整 Reasoner 输入上下文（用户要求验证 executor 结果是否传入）
            _log_reasoner_input(user_content)

            stream = await deepseek.chat.completions.create(
                model="deepseek-reasoner",
                messages=[
                    {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_content},
                ],
                stream=True,
                max_tokens=8192,
            )

            reasoning_buf = []
            draft_buf     = []

            async for chunk in stream:
                delta = chunk.choices[0].delta
                r_chunk = getattr(delta, "reasoning_content", None) or ""
                if r_chunk:
                    reasoning_buf.append(r_chunk)
                c_chunk = delta.content or ""
                if c_chunk:
                    draft_buf.append(c_chunk)
                    # 草稿不推送给前端，交给 Verifier 处理

            draft_reply = "".join(draft_buf)

            # ── 阶段 4：Verifier — 校验草稿，流式输出最终回答 ──
            _log_banner("[Verifier] 校验草稿，生成最终优化回答")

            # 提取搜索上下文（传给 Verifier 做事实核查）
            search_ctx = "\n\n".join(
                r["content_for_llm"] for r in results if r.get("content_for_llm")
            )

            verify_buf = []
            async for text in run_verifier(deepseek, req.message, search_ctx, draft_reply):
                verify_buf.append(text)
                await queue.put(sse("reply", {"text": text}))

            verifier_output = "".join(verify_buf)

            # ★ 打印 Verifier 最终输出（用户要求）
            _log_verifier_output(verifier_output)

            await queue.put(sse("done", {}))

        except AuthenticationError:
            print("❌  API Key 无效")
            await queue.put(sse("error", {"message": "DeepSeek API Key 无效，请检查 .env"}))
        except APIConnectionError as e:
            print(f"❌  网络连接失败：{e}")
            await queue.put(sse("error", {"message": "无法连接 DeepSeek API，请检查网络"}))
        except Exception as e:
            print(f"❌  管线异常：{e}")
            await queue.put(sse("error", {"message": str(e)}))
        finally:
            await queue.put(None)   # 哨兵：告知消费者结束

    # ── 前台消费者：从队列读取事件并流式返回给前端 ──────────
    async def generate():
        asyncio.create_task(pipeline())
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )


# ══════════════════════════════════════════════════════════════
#  兼容端点：普通 JSON（非流式，保留向后兼容）
# ══════════════════════════════════════════════════════════════
@app.post("/api/chat")
async def chat(req: ChatRequest):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plan    = await run_planner(deepseek, req.message)
    steps   = plan_to_steps(plan)
    results = []

    async def _noop(e, d): pass
    results = await run_executor(plan, _noop)

    user_content = build_llm_context(req.message, plan, results)
    _log_reasoner_input(user_content)

    response = await deepseek.chat.completions.create(
        model="deepseek-reasoner",
        messages=[
            {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ],
        max_tokens=8192,
    )
    draft_reply = response.choices[0].message.content or ""

    search_ctx = "\n\n".join(
        r["content_for_llm"] for r in results if r.get("content_for_llm")
    )
    verify_buf = []
    async for text in run_verifier(deepseek, req.message, search_ctx, draft_reply):
        verify_buf.append(text)
    final_reply = "".join(verify_buf)
    _log_verifier_output(final_reply)

    return {
        "reply":       final_reply,
        "draft_reply": draft_reply,
        "steps":       steps,
        "plan":        plan,
        "task_id":     req.task_id,
        "received_at": ts,
    }


@app.get("/api/health")
async def health():
    return {
        "status":  "ok",
        "version": "0.5.0",
        "tools":   [t["name"] for t in TOOLS],
        "time":    datetime.now().isoformat(),
    }


# ── 日志辅助 ──────────────────────────────────────────────────
def _log_banner(msg: str) -> None:
    print(f"\n{'═'*55}")
    print(f"  {msg}")
    print(f"{'═'*55}")


def _log_plan(plan: dict) -> None:
    print(f"📋  [Planner] 任务规划完成")
    print(f"    目标     : {plan.get('goal', '—')}")
    print(f"    复杂度   : {plan.get('complexity', '—')}")
    for t in plan.get("subtasks", []):
        tool_tag = f" [{t.get('tool')}]" if t.get("tool") != "none" else ""
        print(f"      {t.get('id')}. {t.get('title')}{tool_tag}")
        if t.get("tool_query"):
            print(f"         搜索词: {t['tool_query']}")


def _log_reasoner_input(user_content: str) -> None:
    """
    ★ 打印传给 Reasoner 的完整上下文。
    用途：验证 Executor 的搜索结果是否被正确传入最终 LLM。
    """
    bar = "─" * 60
    print(f"\n{bar}")
    print(f"★  [Reasoner 输入上下文]  共 {len(user_content)} 字")
    print(f"{bar}")
    for line in user_content.splitlines():
        print(f"  {line}")
    print(f"{bar}\n")


def _log_verifier_output(text: str) -> None:
    """
    ★ 打印 Verifier 校验后的最终输出。
    用途：查看经过 Verifier 润色的最终答案。
    """
    bar = "═" * 60
    print(f"\n{bar}")
    print(f"★  [Verifier 最终输出]  共 {len(text)} 字")
    print(f"{bar}")
    for line in text.splitlines():
        print(f"  {line}")
    print(f"{bar}\n")


def _fmt_plan(plan: dict) -> str:
    lines = [f"目标：{plan.get('goal', '')}"]
    for t in plan.get("subtasks", []):
        note = f"（搜索：{t['tool_query']}）" if t.get("tool") == "web_search" else ""
        lines.append(f"{t['id']}. {t['title']}：{t.get('description', '')}{note}")
    return "\n".join(lines)
