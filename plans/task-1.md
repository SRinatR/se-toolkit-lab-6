# Task 1: Call an LLM from Code

## LLM Provider
OpenRouter API

## Model
stepfun/step-3.5-flash:free

## Architecture
1. Read prompt from command line arguments
2. Load LLM config from .env.agent.secret (LLM_API_KEY, LLM_API_BASE, LLM_MODEL)
3. Call LLM API with system prompt for JSON response
4. Parse and print JSON response to stdout

## Output Format
{"answer": "response text"}

## Tests
1 test: verify agent returns valid JSON with answer field
