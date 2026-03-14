#!/usr/bin/env python3
import os
import sys
import json
import httpx
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(".env.agent.secret")

PROJECT_ROOT = Path(__file__).parent.resolve()

def read_file(file_path: str) -> str:
    safe_path = (PROJECT_ROOT / file_path).resolve()
    if not str(safe_path).startswith(str(PROJECT_ROOT)):
        return "Error: Path traversal detected!"
    if not safe_path.exists():
        return f"Error: File not found: {file_path}"
    try:
        return safe_path.read_text()[:5000]
    except Exception as e:
        return f"Error: {str(e)}"

def list_files(dir_path: str) -> str:
    safe_path = (PROJECT_ROOT / dir_path).resolve()
    if not str(safe_path).startswith(str(PROJECT_ROOT)):
        return "Error: Path traversal detected!"
    if not safe_path.exists():
        return f"Error: Directory not found: {dir_path}"
    try:
        files = [str(p.relative_to(PROJECT_ROOT)) for p in safe_path.iterdir()]
        return json.dumps(files)
    except Exception as e:
        return f"Error: {str(e)}"

def call_llm(messages: list) -> str:
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
        return data["choices"][0]["message"]["content"]
    return "API error"

def parse_tool_call(content: str) -> dict:
    # Try JSON format first
    try:
        data = json.loads(content)
        if "tool_call" in data and data["tool_call"]:
            return data["tool_call"]
        if "tool" in data:
            return {"tool": data["tool"], "args": data.get("args", {})}
    except:
        pass
    
    # Try XML-like format: <function=list_files dir="." />
    list_match = re.search(r'<function[=:\s]+list_files[^>]*dir[=:\s]+["\']?([^"\'\s>]+)["\']?', content, re.IGNORECASE)
    if list_match:
        return {"tool": "list_files", "args": {"dir": list_match.group(1)}}
    
    # Try: list_files(dir=".")
    list_match2 = re.search(r'list_files\s*\(\s*dir\s*[=:]\s*["\']?([^"\'\)]+)["\']?\s*\)', content, re.IGNORECASE)
    if list_match2:
        return {"tool": "list_files", "args": {"dir": list_match2.group(1)}}
    
    # Try: read_file(path="...")
    read_match = re.search(r'read_file\s*\(\s*path\s*[=:]\s*["\']?([^"\'\)]+)["\']?\s*\)', content, re.IGNORECASE)
    if read_match:
        return {"tool": "read_file", "args": {"path": read_match.group(1)}}
    
    return None

def agent_loop(question: str, max_iterations: int = 10) -> dict:
    system_prompt = """You are a documentation agent. You have two tools:
1. list_files(dir=".") - List files in a directory
2. read_file(path="file.txt") - Read a file

To use a tool, write exactly: list_files(dir=".") or read_file(path="AGENT.md")

Respond in JSON format:
{"answer": "your answer", "tool_call": {"tool": "list_files", "args": {"dir": "."}}}

If you can answer directly, set tool_call to null."""

    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": question})
    tool_calls_log = []
    
    for i in range(max_iterations):
        content = call_llm(messages)
        
        tool_call = parse_tool_call(content)
        
        if not tool_call:
            return {
                "answer": content,
                "source": "",
                "tool_calls": tool_calls_log
            }
        
        tool_name = tool_call.get("tool", "")
        tool_args = tool_call.get("args", {})
        
        if tool_name == "read_file":
            tool_result = read_file(tool_args.get("path", ""))
        elif tool_name == "list_files":
            tool_result = list_files(tool_args.get("dir", ""))
        else:
            tool_result = f"Unknown tool: {tool_name}"
        
        tool_calls_log.append({"tool": tool_name, "args": tool_args, "result": tool_result})
        messages.append({"role": "assistant", "content": f"Tool result: {tool_result}"})
    
    return {"answer": "Max iterations reached", "tool_calls": tool_calls_log}

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "What files are in the project?"
    result = agent_loop(prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))