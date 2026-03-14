# Task 2: The Documentation Agent

## Overview
Agent that can read project files and list directory contents to answer questions about the codebase.

## Tools

### read_file(path: str) -> str
Reads content of a file. Validates path to prevent traversal attacks.

### list_files(dir: str) -> list
Lists files in a directory. Validates path to prevent traversal attacks.

## Architecture
1. Parse user question
2. LLM decides which tool to call (or answer directly)
3. Execute tool if needed
4. Loop up to 10 iterations
5. Return final answer with source and tool_calls log

## Safety
- Validate all paths start with PROJECT_ROOT
- Block path traversal (../)
- Max 10 iterations to prevent infinite loops

## Output Format
{
  "answer": "response text",
  "source": "file/path.md",
  "tool_calls": [{"tool": "read_file", "path": "...", "result": "..."}]
}
