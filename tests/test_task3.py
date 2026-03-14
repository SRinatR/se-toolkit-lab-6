import json
import subprocess

def test_agent_returns_valid_json():
    result = subprocess.run(
        ["uv", "run", "python", "agent.py", "What files are in the project?"],
        capture_output=True,
        text=True
    )
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    assert "answer" in data

def test_agent_has_query_api():
    result = subprocess.run(
        ["uv", "run", "python", "agent.py", "Query the API"],
        capture_output=True,
        text=True
    )
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
