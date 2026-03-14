import json
import subprocess

def test_agent_returns_json():
    result = subprocess.run(
        ["uv", "run", "python", "agent.py", "Say hello"],
        capture_output=True,
        text=True
    )
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    assert "answer" in data
