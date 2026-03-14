#!/usr/bin/env python3
import os
import sys
import json
import httpx
from dotenv import load_dotenv

load_dotenv(".env.agent.secret")

def call_llm(prompt: str) -> dict:
    response = httpx.post(
        os.getenv("LLM_API_BASE") + "/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('LLM_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={
            "model": os.getenv("LLM_MODEL"),
            "messages": [
                {"role": "system", "content": "Respond in JSON format with an 'answer' field."},
                {"role": "user", "content": prompt}
            ]
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
    else:
        return {"answer": "API error", "error": str(data)}

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "Say hello"
    result = call_llm(prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))
