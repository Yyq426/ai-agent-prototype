import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types


# ============================================
# 1. 创建服务器实例
# ============================================
app = Server("weather-note-server")


# ============================================
# 2. 定义工具处理函数 (业务逻辑)
# ============================================

async def handle_get_weather(city: str) -> str:
    """
    模拟获取天气数据
    真实场景可替换为调用 OpenWeatherMap 等 API
    """
    import random

    weather_data = {
        "city": city,
        "temperature": round(random.uniform(10, 30), 1),
        "condition": random.choice(["晴天", "多云", "小雨", "阴天", "雾"]),
        "humidity": random.randint(40, 80),
        "timestamp": datetime.now().isoformat(),
        "note": "⚠️ 模拟数据，仅供演示"
    }

    return json.dumps(weather_data, ensure_ascii=False, indent=2)


async def handle_save_note(content: str, tags: Optional[List[str]] = None) -> str:
    """
    将笔记保存到本地 Markdown 文件
    """
    # 确保笔记目录存在
    notes_dir = Path.cwd() / "notes"
    notes_dir.mkdir(exist_ok=True)

    # 按日期生成文件名
    date_str = datetime.now().strftime("%Y-%m-%d")
    file_path = notes_dir / f"notes-{date_str}.md"

    # 格式化笔记内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tags_str = ", ".join(tags) if tags else "无"

    note_entry = f"""
## 📝 笔记 - {timestamp}
{content}

🏷️ 标签: {tags_str}
---
"""

    # 追加写入文件
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(note_entry)

    return f"✅ 笔记已成功保存到 {file_path}"


# ============================================
# 3. 注册工具列表处理器
# ============================================

@app.list_tools() # @app.list_tools() 装饰的函数，其任务是返回一个包含工具元数据的列表。这个列表就是你的服务器向外界公布的“能力清单”。
# 一个典型的实现会返回一个 Tool 对象的列表，每个 Tool 对象都详细描述了工具的功能和调用方式。
async def list_tools() -> list[types.Tool]:
    """
    列出所有可用工具及其参数定义
    """
    return [
        types.Tool(
            name="get_weather",
            description="获取指定城市的当前天气信息（模拟数据）", # 给 AI 模型看的指令。一个清晰、准确的描述能帮助 AI 在合适的场景下正确地选择和使用你的工具，它直接影响着 AI 调用工具的准确性
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海、重庆"
                    }
                },
                "required": ["city"]
            }
        ),
        types.Tool(
            name="save_note",
            description="将重要信息保存到本地笔记文件中",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "笔记的正文内容"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "笔记标签列表，如 ['工作', '重要']"
                    }
                },
                "required": ["content"]
            }
        )
    ]


# ============================================
# 4. 注册工具调用处理器
# ============================================

@app.call_tool() # @app.call_tool() 装饰的函数，是 MCP 服务器处理具体工具调用的入口函数。当 AI 模型（通过客户端）决定调用某个工具时，服务器就会触发这个函数，并根据请求中的工具名称和参数，执行对应的业务逻辑。
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    处理工具调用请求
    """
    if name == "get_weather":
        # 参数验证
        city = arguments.get("city")
        if not city:
            raise ValueError("缺少必要参数: city")

        # 调用业务逻辑
        result = await handle_get_weather(city)

        return [types.TextContent(
            type="text",
            text=result
        )]

    elif name == "save_note":
        # 参数验证
        content = arguments.get("content")
        if not content:
            raise ValueError("缺少必要参数: content")

        tags = arguments.get("tags", [])
        if not isinstance(tags, list):
            tags = [tags] if tags else []

        # 调用业务逻辑
        result = await handle_save_note(content, tags)

        return [types.TextContent(
            type="text",
            text=result
        )]

    else:
        raise ValueError(f"未知工具: {name}")


# ============================================
# 5. 启动服务器 (入口函数)
# ============================================

async def main():
    """
    使用 stdio 传输启动服务器
    """
    # 初始化服务器
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="weather-note-server",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())