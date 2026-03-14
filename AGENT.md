# Agent Architecture

## Overview
This agent is a CLI tool that can call LLM API and use tools to read files and list directories.

## Components

### agent.py
Main entry point with agent loop and tool implementations.

### Tools
- read_file(path): Read content of a file with path traversal protection
- list_files(dir): List files in a directory with path traversal protection

### Configuration
- LLM_API_KEY: OpenRouter API key
- LLM_API_BASE: https://openrouter.ai/api/v1
- LLM_MODEL: stepfun/step-3.5-flash:free

## Task 1 Implementation
Basic LLM call with JSON response.

## Task 2 Implementation
Agent loop with tool calling. The LLM decides which tool to call based on the question.
Maximum 10 iterations to prevent infinite loops.

## Safety
- All paths are validated to start with PROJECT_ROOT
- Path traversal (../) is blocked
- Max iterations limit

## Environment Variables
All LLM configuration is read from environment variables, not hardcoded.
