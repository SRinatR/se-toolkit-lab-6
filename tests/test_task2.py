import json
import subprocess

def test_agent_has_tools():
    result = subprocess.run(
        ["uv", "run", "python", "agent.py", "List files in current directory"],
        capture_output=True,
        text=True
    )
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    assert "answer" in data or "tool_calls" in data

def test_read_file_works():
    result = subprocess.run(
        ["uv", "run", "python", "agent.py", "Read the AGENT.md file"],
        capture_output=True,
        text=True
    )
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
