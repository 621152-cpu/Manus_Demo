"""
工具注册表 — Manus 可用工具的唯一维护入口
============================================================
新增工具时，在 TOOLS 列表中追加一条记录，并在对应文件中实现逻辑。

已注册工具：
  1. web_search  — 联网搜索（Tavily / Serper / 百度千帆，按 .env 配置自动选择 Provider）
"""

from typing import Any

# ── 工具描述列表（供 Planner 读取、决策） ─────────────────────
TOOLS: list[dict[str, Any]] = [
    {
        "name": "web_search",
        "description": (
            "使用 Tavily 搜索引擎检索互联网获取最新信息。"
            "适用于：实时数据、新闻资讯、事实核查、市场动态、技术文档等场景。"
        ),
        "parameters": {
            "query":       "搜索关键词或完整问题 (str, 必填)",
            "max_results": "返回结果数量，默认 5 (int, 可选)",
        },
        "when_to_use": "任务需要获取互联网实时信息时",
        "module":      "tools.search",
        "function":    "web_search",
    },
    # ── 未来可在此追加更多工具，例如：─────────────────────────
    # {
    #     "name": "code_executor",
    #     "description": "在沙箱中执行 Python 代码并返回结果",
    #     ...
    # },
    # {
    #     "name": "file_writer",
    #     "description": "将内容写入文件并返回下载链接",
    #     ...
    # },
]

# ── OpenAI Function Calling 格式（供模型直接调用） ────────────
TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "使用 Tavily 搜索引擎检索互联网最新信息。"
                "适用于需要实时数据、最新资讯、事实核查的场景。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或完整问题",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "返回搜索结果数量，默认为 5",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
]

# ── 快捷查询 ──────────────────────────────────────────────────
TOOL_NAMES: list[str] = [t["name"] for t in TOOLS]


def get_tool(name: str) -> dict[str, Any] | None:
    """按名称查询工具描述"""
    return next((t for t in TOOLS if t["name"] == name), None)
