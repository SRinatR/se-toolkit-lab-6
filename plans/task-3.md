# Task 3: The API Agent

## Overview
Agent that can query the LMS API to get information about students, assignments, and submissions.

## Tools

### query_api(endpoint: str, method: str = "GET", body: dict = None) -> str
Makes HTTP requests to the LMS API with Bearer token authentication.

## Architecture
1. Parse user question
2. LLM decides which tool to call (read_file, list_files, or query_api)
3. Execute tool and get result
4. Loop up to 10 iterations
5. Return final answer with tool_calls log

## API Endpoints
- GET /api/students - List all students
- GET /api/students/{id} - Get student by ID
- GET /api/assignments - List all assignments
- GET /api/submissions - List all submissions

## Configuration
- LMS_API_KEY: API key from .env.docker.secret
- API_BASE_URL: http://127.0.0.1:42002

## Output Format
{
  "answer": "response text",
  "source": "API endpoint or file path",
  "tool_calls": [{"tool": "...", "args": {...}, "result": "..."}]
}
