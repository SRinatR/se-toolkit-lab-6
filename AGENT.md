# Agent Architecture

## Overview
This agent is a CLI tool that calls an LLM API and returns JSON responses.

## Components

### agent.py
Main entry point. Reads prompt from command line, calls LLM, prints JSON.

### Configuration
- LLM_API_KEY: OpenRouter API key
- LLM_API_BASE: https://openrouter.ai/api/v1
- LLM_MODEL: stepfun/step-3.5-flash:free

## Task 1 Implementation
The agent reads a prompt from command line arguments, calls the LLM API with a system prompt requesting JSON format, and prints the result to stdout.

## Environment Variables
All LLM configuration is read from environment variables, not hardcoded. This allows the autochecker to inject its own credentials during evaluation.
