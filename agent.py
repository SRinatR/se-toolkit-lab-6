#!/usr/bin/env python3
"""
CLI Documentation Agent with tools and agentic loop.
Compatible with Polza AI API.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

MAX_ITERATIONS = 10
PROJECT_ROOT = Path(__file__).parent.resolve()


def load_env() -> dict[str, str]:
    """Load environment variables."""
    env_path = Path(__file__).parent / ".env.agent.secret"
    if not env_path.exists():
        print(f"Error: {env_path} not found", file=sys.stderr)
        sys.exit(1)

    load_dotenv(env_path)
    
    docker_env_path = Path(__file__).parent / ".env.docker.secret"
    if docker_env_path.exists():
        load_dotenv(docker_env_path, override=False)

    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")
    lms_api_key = os.getenv("LMS_API_KEY")
    agent_api_base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

    if not api_key:
        print("Error: LLM_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    if not api_base:
        print("Error: LLM_API_BASE not set", file=sys.stderr)
        sys.exit(1)
    if not model:
        print("Error: LLM_MODEL not set", file=sys.stderr)
        sys.exit(1)

    return {
        "api_key": api_key,
        "api_base": api_base.rstrip("/"),
        "model": model,
        "lms_api_key": lms_api_key or "",
        "agent_api_base_url": agent_api_base_url.rstrip("/"),
    }


def validate_path(user_path: str) -> Path:
    """Validate path (security check)."""
    if ".." in user_path:
        raise ValueError("Path traversal not allowed")
    full_path = (PROJECT_ROOT / user_path).resolve()
    if not str(full_path).startswith(str(PROJECT_ROOT)):
        raise ValueError("Path outside project directory")
    return full_path


def read_file(path: str) -> str:
    """Read file contents."""
    try:
        validated_path = validate_path(path)
        if not validated_path.exists():
            return f"Error: File not found: {path}"
        if not validated_path.is_file():
            return f"Error: Not a file: {path}"
        return validated_path.read_text(encoding="utf-8")[:15000]
    except Exception as e:
        return f"Error: {str(e)}"


def list_files(path: str) -> str:
    """List files in directory."""
    try:
        validated_path = validate_path(path)
        if not validated_path.exists():
            return f"Error: Path not found: {path}"
        if not validated_path.is_dir():
            return f"Error: Not a directory: {path}"
        entries = sorted([e.name for e in validated_path.iterdir()])
        return "\n".join(entries)
    except Exception as e:
        return f"Error: {str(e)}"


def query_api(method: str, path: str, body: str = "", skip_auth: bool = False, config: dict[str, str] | None = None) -> str:
    """Query backend API."""
    if config is None:
        config = {"lms_api_key": "", "agent_api_base_url": "http://localhost:42002"}

    if ".." in path:
        return json.dumps({"status_code": 0, "error": "Path traversal not allowed"})

    if not path.startswith("/"):
        path = "/" + path

    base_url = config.get("agent_api_base_url", "http://localhost:42002")
    url = f"{base_url}{path}"
    lms_api_key = config.get("lms_api_key", "") if not skip_auth else ""

    headers = {"Content-Type": "application/json"}
    if lms_api_key and not skip_auth:
        headers["Authorization"] = f"Bearer {lms_api_key}"

    try:
        with httpx.Client(timeout=30.0) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = client.post(url, headers=headers, content=body or "{}")
            elif method.upper() == "PUT":
                response = client.put(url, headers=headers, content=body or "{}")
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                return json.dumps({"status_code": 0, "error": f"Unsupported method: {method}"})

            try:
                body_data = response.json()
            except:
                body_data = response.text

            return json.dumps({"status_code": response.status_code, "body": body_data})

    except httpx.TimeoutException:
        return json.dumps({"status_code": 0, "error": "Request timeout"})
    except httpx.ConnectError as e:
        return json.dumps({"status_code": 0, "error": f"Cannot connect: {str(e)}"})
    except Exception as e:
        return json.dumps({"status_code": 0, "error": str(e)})


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file in the project",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from project root"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path from project root"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Query the backend API",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                    "path": {"type": "string", "description": "API endpoint path"},
                    "body": {"type": "string", "description": "JSON body for POST/PUT"},
                    "skip_auth": {"type": "boolean", "description": "Omit Authorization header"},
                },
                "required": ["method", "path"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are a documentation and system assistant for a software engineering project.

Available tools:
- list_files(path): List files in a directory
- read_file(path): Read file contents  
- query_api(method, path, body?, skip_auth?): Query backend API

GUIDELINES:
1. Auth questions (without auth/header) → query_api with skip_auth=true
2. Wiki questions → list_files then read_file
3. Source code questions → read_file on backend/ files
4. Counting questions (how many items/learners) → query_api with auth, then count from response
   - If response has "total" field → use that number
   - If response has "count" field → use that number
   - If response has "items" or "learners" array → count elements
   - Answer format: "There are X items/learners in the database."
5. Docker/request flow questions → read docker-compose.yml, Dockerfile, Caddyfile, main.py
6. For multi-file questions → read all relevant files before answering

Answer in natural language. Be concise. Mention source in answer.
Do NOT output JSON in your answer text.
Maximum 10 tool calls per question."""


def execute_tool(name: str, args: dict[str, Any], config: dict[str, str] | None = None) -> str:
    """Execute a tool."""
    if name == "read_file":
        return read_file(args.get("path", ""))
    elif name == "list_files":
        return list_files(args.get("path", ""))
    elif name == "query_api":
        return query_api(
            args.get("method", "GET"),
            args.get("path", ""),
            args.get("body", ""),
            args.get("skip_auth", False),
            config
        )
    return f"Error: Unknown tool: {name}"


def call_llm(messages: list[dict[str, Any]], config: dict[str, str]) -> dict[str, Any]:
    """Call LLM API."""
    base = config['api_base'].rstrip('/')
    url = f"{base}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
    }
    
    payload = {
        "model": config["model"],
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "max_tokens": 2048,
        "temperature": 0.7,
    }
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("choices"):
                return {"content": "No response from LLM", "tool_calls": []}

            message = data["choices"][0]["message"]
            content = message.get("content") or ""
            tool_calls_list = []

            if message.get("tool_calls"):
                for tc in message["tool_calls"]:
                    tool_calls_list.append({
                        "id": tc.get("id") or "",
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    })

            return {"content": content, "tool_calls": tool_calls_list}
            
    except Exception as e:
        print(f"LLM Error: {str(e)}", file=sys.stderr)
        return {"content": f"Error: {str(e)}", "tool_calls": []}


def extract_source(tool_calls_log: list[dict[str, Any]]) -> str:
    """Extract source from tool calls."""
    for call in reversed(tool_calls_log):
        if call["tool"] in ["read_file", "list_files", "query_api"]:
            path = call["args"].get("path", "")
            method = call["args"].get("method", "")
            if path:
                if method and call["tool"] == "query_api":
                    return f"{method} {path}"
                return path
    return ""


def extract_count_from_results(tool_calls_log: list[dict[str, Any]]) -> int | None:
    """Extract count from API response."""
    for call in tool_calls_log:
        if call["tool"] == "query_api":
            try:
                result = json.loads(call["result"])
                body = result.get("body")
                
                if isinstance(body, dict):
                    if "total" in body:
                        return body["total"]
                    if "count" in body:
                        return body["count"]
                    if "items" in body and isinstance(body["items"], list):
                        return len(body["items"])
                    if "learners" in body and isinstance(body["learners"], list):
                        return len(body["learners"])
                
                if isinstance(body, list):
                    return len(body)
                    
            except:
                pass
    return None


def run_agentic_loop(question: str, config: dict[str, str]) -> dict[str, Any]:
    """Run agentic loop."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    
    tool_calls_log = []
    final_answer = ""
    
    for iteration in range(MAX_ITERATIONS):
        print(f"Iteration {iteration + 1}/{MAX_ITERATIONS}...", file=sys.stderr)
        
        response = call_llm(messages, config)
        
        if response["tool_calls"]:
            tool_calls_formatted = []
            for tc in response["tool_calls"]:
                tool_calls_formatted.append({
                    "id": tc.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"],
                    }
                })
            
            messages.append({
                "role": "assistant",
                "tool_calls": tool_calls_formatted,
            })
            
            for tool_call in response["tool_calls"]:
                name = tool_call["name"]
                try:
                    args = json.loads(tool_call["arguments"])
                except:
                    args = {}

                print(f"  Calling {name}({args})...", file=sys.stderr)
                result = execute_tool(name, args, config)

                tool_calls_log.append({
                    "tool": name,
                    "args": args,
                    "result": result[:1000] if len(result) > 1000 else result,
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result,
                })
            continue
        else:
            final_answer = response["content"]
            break
    
    count = extract_count_from_results(tool_calls_log)
    if count is not None:
        q_lower = question.lower()
        if "how many" in q_lower or "сколько" in q_lower or "count" in q_lower:
            if "item" in q_lower or "items" in q_lower:
                final_answer = f"There are {count} items in the database."
            elif "learner" in q_lower or "learners" in q_lower:
                final_answer = f"There are {count} learners in the database."
            elif "user" in q_lower or "users" in q_lower:
                final_answer = f"There are {count} users in the database."
            else:
                final_answer = f"There are {count} items."
    
    source = extract_source(tool_calls_log)
    
    if not final_answer or not final_answer.strip():
        if tool_calls_log:
            final_answer = f"Data from {source}: {tool_calls_log[-1]['result'][:300]}"
        else:
            final_answer = "No answer could be generated."
    
    return {
        "answer": final_answer.strip(),
        "source": source,
        "tool_calls": tool_calls_log,
    }


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    if not question.strip():
        print("Error: Question cannot be empty", file=sys.stderr)
        sys.exit(1)
    
    print(f"Question: {question}", file=sys.stderr)
    
    config = load_env()
    print(f"Using model: {config['model']} @ {config['api_base']}", file=sys.stderr)
    
    try:
        result = run_agentic_loop(question, config)
    except Exception as e:
        result = {
            "answer": f"Error: {str(e)}",
            "source": "",
            "tool_calls": [],
        }
    
    try:
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({
            "answer": f"Error: {str(e)}",
            "source": "",
            "tool_calls": [],
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()