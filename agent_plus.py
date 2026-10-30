import os
import json
import subprocess
import sys
from datetime import datetime
from typing import Any
from openai import OpenAI

# 安全起见，API Key 请勿泄露，一定不要在代码中硬编码，上传到 GitHub 仓库前请务必请删除。
# 请在机器中通过环境变量设置环境变量中设置 API Key，如：
# export DEEPSEEK_API_KEY="your-key"
api_key = os.getenv("DEEPSEEK_API_KEY")

if api_key:
    print("成功获取API Key!")
else:
    print("未找到API Key，请检查环境变量设置。")

# ==================== 1. LLM 客户端 ====================

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", "sk-xxx"),
    base_url=os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com"),
)
MODEL = os.environ.get("MODEL", "deepseek-v4-flash")
MEMORY_FILE = "agent_memory.md"

tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Execute a bash command on the system",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The bash command to execute"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["path", "content"]
            }
        }
    }
]

def execute_bash(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {str(e)}"

def read_file(path):
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"

def write_file(path, content):
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error: {str(e)}"

available_functions = {
    "execute_bash": execute_bash,
    "read_file": read_file,
    "write_file": write_file
}

def parse_tool_arguments(raw_arguments: str) -> dict[str, Any]:
    if not raw_arguments:
        return {}
    try:
        parsed = json.loads(raw_arguments)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError as error:
        return {"_argument_error": f"Invalid JSON arguments: {error}"}

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return ""
    try:
        with open(MEMORY_FILE, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            return '\n'.join(lines[-50:]) if len(lines) > 50 else content
    except:
        return ""

def save_memory(task, result):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n## {timestamp}\n**Task:** {task}\n**Result:** {result}\n"
    try:
        with open(MEMORY_FILE, 'a') as f:
            f.write(entry)
    except:
        pass

def create_plan(task):
    print("[Planning] Breaking down task...")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Break down the task into 3-5 simple, actionable steps. Return as JSON array of strings."},
            {"role": "user", "content": f"Task: {task}"}
        ],
        response_format={"type": "json_object"}
    )
    try:
        plan_data = json.loads(response.choices[0].message.content)
        if isinstance(plan_data, dict):
            steps = plan_data.get("steps", [task])
        elif isinstance(plan_data, list):
            steps = plan_data
        else:
            steps = [task]
        print(f"[Plan] {len(steps)} steps created")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step}")
        return steps
    except:
        return [task]

def run_agent_step(task, messages, max_iterations=5):
    messages.append({"role": "user", "content": task})
    actions = []
    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools
        )
        message = response.choices[0].message
        messages.append(message)
        if not message.tool_calls:
            return message.content, actions, messages
        for tool_call in message.tool_calls:
            function_payload = getattr(tool_call, "function", None)
            if function_payload is None:
                continue
            function_name = str(getattr(function_payload, "name", ""))
            raw_arguments = str(getattr(function_payload, "arguments", ""))
            function_args = parse_tool_arguments(raw_arguments)
            print(f"[Tool] {function_name}({function_args})")
            function_impl = available_functions.get(function_name)
            if function_impl is None:
                function_response = f"Error: Unknown tool '{function_name}'"
            elif "_argument_error" in function_args:
                function_response = f"Error: {function_args['_argument_error']}"
            else:
                function_response = function_impl(**function_args)
                actions.append({"tool": function_name, "args": function_args})
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": function_response})
    print(f"messages after running agent step: {messages}")
    return "Max iterations reached", actions, messages

def run_agent_plus(task, use_plan_=False):
    memory = load_memory()
    system_prompt = "You are a helpful assistant that can interact with the system. Be concise."
    if memory:
        system_prompt += f"\n\nPrevious context:\n{memory}"  # why put in system prompt?
    messages = [{"role": "system", "content": system_prompt}]
    if use_plan_:
        steps = create_plan(task)
    else:
        steps = [task]
    all_results = []
    for i, step in enumerate(steps, 1):
        if len(steps) > 1:
            print(f"\n[Step {i}/{len(steps)}] {step}")
        result, actions, messages = run_agent_step(step, messages)
        all_results.append(result)
        print(f"\n{result}")
    final_result = "\n".join(all_results)
    save_memory(task, final_result)
    return final_result

if __name__ == "__main__":
    # if "--plan" in sys.argv:
    #     use_plan = True
    # else:
    #     use_plan = False
    # if use_plan:
    #     sys.argv.remove("--plan")
    # if len(sys.argv) < 2:
    #     print("Usage: python agent-plus.py [--plan] 'your task here'")
    #     print("  --plan: Enable task planning and decomposition")
    #     sys.exit(1)
    # task_input = " ".join(sys.argv[1:])
    ## for test purpose
    task_input = "Write a Python script to calculate the factorial of a number."
    print(f"[Task] {task_input}")
    use_plan = True
    # run_agent_plus(task_input, use_plan=use_plan)
    run_agent_plus(task_input, use_plan_=use_plan)