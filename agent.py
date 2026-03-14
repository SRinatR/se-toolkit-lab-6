#!/usr/bin/env python3
import os
import sys
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(".env.agent.secret")

PROJECT_ROOT = Path(__file__).parent.resolve()

def read_file(file_path: str) -> str:
    safe_path = (PROJECT_ROOT / file_path).resolve()
    if not str(safe_path).startswith(str(PROJECT_ROOT)):
        raise ValueError("Path traversal detected!")
    if not safe_path.exists():
        return f"Error: File not found: {file_path}"
    return safe_path.read_text()

def list_files(dir_path: str) -> list:
    safe_path = (PROJECT_ROOT / dir_path).resolve()
    if not str(safe_path).startswith(str(PROJECT_ROOT)):
        raise ValueError("Path traversal detected!")
    if not safe_path.exists():
        return f"Error: Directory not found: {dir_path}"
    return [str(p.relative_to(PROJECT_ROOT)) for p in safe_path.iterdir()]

TOOLS = {
    "read_file": {"description": "Read content of a file", "parameters": {"path": "string"}},
    "list_files": {"description": "List files in a directory", "parameters": {"dir": "string"}}
}

def call_llm(messages: list) -> dict:
    response = httpx.post(
        os.getenv("LLM_API_BASE") + "/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('LLM_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={
            "model": os.getenv("LLM_MODEL"),
            "messages": messages,
            "temperature": 0.1
        },
        timeout=60.0
    )
    data = response.json()
    if "choices" in data and len(data["choices"]) > 0:
        content = data["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except:
            return {"answer": content}
    return {"answer": "API error"}

def execute_tool(tool_name: str, args: dict) -> str:
    if tool_name == "read_file":
        return read_file(args.get("path", ""))
    elif tool_name == "list_files":
        return json.dumps(list_files(args.get("dir", "")))
    return f"Unknown tool: {tool_name}"

def agent_loop(question: str, max_iterations: int = 10) -> dict:
    system_prompt = """You are a documentation agent. You can use tools to read files and list directories.
Available tools:
- read_file(path): Read content of a file
- list_files(dir): List files in a directory

Respond in JSON format:
{
  "answer": "your answer or empty if calling tool",
  "source": "file path if applicable",
  "tool_call": {"tool": "tool_name", "args": {"arg": "value"}} or null
}

If you can answer directly, set tool_call to null.
If you need to read a file, set tool_call with the tool name and args.
"""
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": question})
    tool_calls_log = []
    
    for i in range(max_iterations):
        response = call_llm(messages)
        
        if not response.get("tool_call"):
            return {
                "answer": response.get("answer", ""),
                "source": response.get("source", ""),
                "tool_calls": tool_calls_log
            }
        
        tool_result = execute_tool(response["tool_call"]["tool"], response["tool_call"]["args"])
        tool_calls_log.append({**response["tool_call"], "result": tool_result})
        messages.append({"role": "assistant", "content": f"Tool result: {tool_result}"})
    
    return {"answer": "Max iterations reached", "tool_calls": tool_calls_log}

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "What files are in the project?"
    result = agent_loop(prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))
