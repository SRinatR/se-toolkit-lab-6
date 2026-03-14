# Agent Architecture

## Overview
This agent is a CLI tool that can call LLM API and use tools to read files, list directories, and query the LMS API. The agent implements a ReAct-style loop where the LLM decides which tool to call based on the user's question.

## Components

### agent.py
Main entry point containing the agent loop and all tool implementations. The agent reads configuration from environment variables and processes user questions through an iterative tool-calling loop.

### Tools
- **read_file(path)**: Reads content of a file with path traversal protection. Returns file content or error message.
- **list_files(dir)**: Lists files in a directory with path traversal protection. Returns JSON array of file paths.
- **query_api(endpoint, method, body)**: Makes HTTP requests to the LMS API with Bearer token authentication. Returns JSON response or error.

### Configuration
All configuration is read from environment variables:
- LLM_API_KEY: OpenRouter API key for LLM access
- LLM_API_BASE: https://openrouter.ai/api/v1
- LLM_MODEL: stepfun/step-3.5-flash:free
- LMS_API_KEY: LMS API key from .env.docker.secret
- API_BASE_URL: http://127.0.0.1:42002

## Task 1 Implementation
Basic LLM call with JSON response. The agent reads a prompt from command line, calls the LLM API, and prints the result.

## Task 2 Implementation
Added read_file and list_files tools with an agent loop. The LLM decides which tool to call based on the question. Maximum 10 iterations to prevent infinite loops.

## Task 3 Implementation
Added query_api tool for LMS API integration. The agent can now query student data, assignments, and submissions. The tool uses Bearer token authentication with the LMS_API_KEY.

## Safety
- All file paths are validated to start with PROJECT_ROOT
- Path traversal (../) is blocked
- Maximum iterations limit (10) prevents infinite loops
- API errors are caught and returned as JSON

## Lessons Learned
1. LLMs don't always return valid JSON - need robust parsing
2. Tool calling requires clear prompts and examples
3. Environment variables make testing easier
4. Path validation is critical for security
5. Max iterations prevent hanging on complex questions

## Environment Variables
All configuration is read from environment variables, not hardcoded. This allows the autochecker to inject its own credentials during evaluation.
