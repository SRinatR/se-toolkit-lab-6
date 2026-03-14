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

def query_api(endpoint: str, method: str = "GET", body: dict = None) -> str:
    api_key = os.getenv("LMS_API_KEY")
    base_url = os.getenv("AGENT_API_BASE_URL", "http://127.0.0.1:42002")
    url = f"{base_url}{endpoint}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        if method == "GET":
            response = httpx.get(url, headers=headers, timeout=30.0)
        elif method == "POST":
            response = httpx.post(url, headers=headers, json=body, timeout=30.0)
        else:
            return json.dumps({"error": f"Unsupported method: {method}"})
        
        result = response.json() if response.status_code == 200 else {"error": f"Status {response.status_code}"}
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

def call_llm(messages: list) -> str:
    try:
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
    except Exception as e:
        pass
    return ""

def parse_tool_call(content: str) -> dict:
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            if "tool_call" in data and data["tool_call"]:
                return data["tool_call"]
            if "tool" in data:
                return {"tool": data["tool"], "args": data.get("args", {})}
    except:
        pass
    
    list_match = re.search(r'list_files\s*\(\s*dir\s*[=:]\s*["\']?([^"\'\)]+)["\']?\s*\)', content, re.IGNORECASE)
    if list_match:
        return {"tool": "list_files", "args": {"dir": list_match.group(1)}}
    
    read_match = re.search(r'read_file\s*\(\s*path\s*[=:]\s*["\']?([^"\'\)]+)["\']?\s*\)', content, re.IGNORECASE)
    if read_match:
        return {"tool": "read_file", "args": {"path": read_match.group(1)}}
    
    api_match = re.search(r'query_api\s*\(\s*endpoint\s*[=:]\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
    if api_match:
        return {"tool": "query_api", "args": {"endpoint": api_match.group(1)}}
    
    return None

def agent_loop(question: str, max_iterations: int = 10) -> dict:
    system_prompt = """You are a helpful documentation agent. You have three tools:
1. list_files(dir=".") - List files in a directory
2. read_file(path="file.txt") - Read a file content  
3. query_api(endpoint="/api/students") - Query the LMS API

RULES:
- Call ONE tool at a time, then WAIT for the result
- After receiving tool result, use it to answer the question
- Do NOT call the same tool twice with same arguments
- When you have enough information, return final answer with tool_call: null

Respond in JSON format ONLY:
{"answer": "your final answer or empty if calling tool", "tool_call": {"tool": "name", "args": {}} or null}

Example 1 (calling tool): {"answer": "", "tool_call": {"tool": "list_files", "args": {"dir": "."}}}
Example 2 (final answer): {"answer": "The project has 50 files", "tool_call": null}"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": question})
    tool_calls_log = []
    seen_calls = set()
    
    for i in range(max_iterations):
        content = call_llm(messages)
        
        tool_call = parse_tool_call(content)
        
        # If no tool call or tool_call is null, return answer
        if not tool_call:
            answer = content.strip()
            try:
                data = json.loads(content)
                answer = data.get("answer", content)
            except:
                pass
            return {"answer": answer, "source": "", "tool_calls": tool_calls_log}
        
        # Prevent infinite loops - check if we already made this exact call
        call_key = f"{tool_call.get('tool')}:{json.dumps(tool_call.get('args'), sort_keys=True)}"
        if call_key in seen_calls:
            # Already made this call, return answer with what we have
            answer = f"Got results from {tool_call.get('tool')}. " + content[:200]
            try:
                data = json.loads(content)
                if "answer" in data and data["answer"]:
                    answer = data["answer"]
            except:
                pass
            return {"answer": answer, "source": "", "tool_calls": tool_calls_log}
        seen_calls.add(call_key)
        
        tool_name = tool_call.get("tool", "")
        tool_args = tool_call.get("args", {})
        
        if tool_name == "read_file":
            tool_result = read_file(tool_args.get("path", ""))
        elif tool_name == "list_files":
            tool_result = list_files(tool_args.get("dir", ""))
        elif tool_name == "query_api":
            tool_result = query_api(tool_args.get("endpoint", ""), tool_args.get("method", "GET"), tool_args.get("body"))
        else:
            tool_result = json.dumps({"error": f"Unknown tool: {tool_name}"})
        
        tool_calls_log.append({"tool": tool_name, "args": tool_args, "result": tool_result})
        messages.append({"role": "assistant", "content": f"Tool result: {tool_result}\n\nNow answer the user's question using this information. Set tool_call to null."})
    
    return {"answer": "Max iterations reached", "source": "", "tool_calls": tool_calls_log}

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "What files are in the project?"
    result = agent_loop(prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))