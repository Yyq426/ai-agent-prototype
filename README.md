# AI Agent Prototype

个人 AI Agent 学习实践项目，从零实现 Agent 的几个核心机制。

## 项目概述

本仓库是一组小型 AI Agent 原型实现，覆盖 Agent 的核心能力链路：

- **工具调用循环**：LLM 输出工具调用 → 执行 → 结果回灌 → 再次推理
- **任务规划**：将复杂任务分解为可执行步骤
- **持久记忆**：跨多次调用保持上下文
- **多智能体协作**：Agent 身份、生命周期管理、消息通道
- **MCP 工具协议**：基于官方 SDK 实现工具服务器

## 文件说明

| 文件 | 说明 | 核心能力 |
| --- | --- | --- |
| `tiny_agent.py` | 最小 Agent 实现（~50 行核心） | LLM + 工具定义 + 执行循环 |
| `agent_plus.py` | 在 tiny_agent 基础上扩展 | 任务规划（plan）+ 持久记忆（memory） |
| `agent_teams.py` | 多智能体团队协作 | Agent 身份/记忆、Team 生命周期、消息通道（send/broadcast/inbox） |
| `agent-claudecode.py` | 类 Claude Code 结构的 Agent | 记忆 + Rules + Skills + MCP 工具动态加载 |
| `mcp_server.py` | MCP 工具服务器（stdio） | 注册 get_weather / save_note 工具 |

## 运行前提

```bash
pip install openai httpx mcp
```

通过环境变量配置 LLM 服务：

```bash
export DEEPSEEK_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.deepseek.com"   # 可选，默认指向 DeepSeek
export MODEL="deepseek-v4-flash"                    # 可选
```

> 代码中的 API Key 均从环境变量读取，无任何硬编码。

## 快速开始

```bash
# 最小 Agent：查看当前目录文件
python tiny_agent.py "帮我看看当前目录下有什么文件"

# 带规划与记忆的 Agent
python agent_plus.py

# 多智能体团队协作
python agent_teams.py "固定 3 人发布评审团队演示：登录接口发布前评审"

# 类 Claude Code 结构的 Agent
python agent-claudecode.py --plan "你的任务"
```

## 说明

本项目为个人学习实践原型，用于演示 Agent 核心机制，并非生产级系统。
