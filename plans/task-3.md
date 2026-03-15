# Task 3: The System Agent - Implementation Plan

## Overview
This task extends the documentation agent from Task 2 with a new `query_api` tool that enables interaction with the deployed backend API. The agent can now answer questions about live system data, authentication behavior, and API endpoints.

## Implementation Plan

### 1. query_api Tool Schema
- Added function-calling schema with parameters: method, path, body, skip_auth
- method: HTTP method (GET, POST, PUT, DELETE)
- path: API endpoint path (e.g., '/items/', '/learners/', '/analytics/completion-rate')
- body: Optional JSON request body for POST/PUT requests
- skip_auth: Boolean flag to omit Authorization header for testing

### 2. Authentication Handling
- Uses LMS_API_KEY from .env.docker.secret environment variable
- Automatically includes Bearer token in Authorization header
- skip_auth=true omits the header for testing authentication requirements
- Handles 401 Unauthorized responses gracefully

### 3. System Prompt Updates
- Added guidelines for authentication questions (use skip_auth=true)
- Added guidelines for counting questions (extract total/count from API response)
- Added guidelines for live data questions (use query_api with GET)
- Added guidelines for Docker/request flow questions (read multiple files)
- Instructs LLM to answer in natural language, not JSON

### 4. Output Format
- answer: Natural language response to the user's question
- source: File path or API endpoint used as reference
- tool_calls: List of executed tools with arguments and results

### 5. Error Handling
- 30 second timeout for API requests
- 60 second timeout for LLM API calls
- Maximum 10 iterations per question
- Always output valid JSON even on errors
- Graceful handling of connection errors and invalid responses

### 6. Counting Logic
- Extract "total" field from API response if present
- Extract "count" field if present
- Count elements in "items" or "learners" arrays
- Handle direct list responses

## Testing Strategy
1. Test authentication questions with skip_auth=true
2. Test counting questions with authenticated API calls
3. Test wiki/documentation questions with read_file
4. Test source code questions with backend file access
5. Test Docker flow questions with multiple file reads

## Expected Results
- Local evaluation: 4-5/5 visible questions
- Autochecker evaluation: 8+/10 total (including hidden questions)

## Iteration History
1. Fixed JSON output format (was outputting JSON inside answer field)
2. Fixed Polza AI API integration (correct URL path)
3. Fixed authentication status code detection (401 instead of 502)
4. Added automatic count extraction for "how many" questions
5. Improved source extraction for better traceability
6. Added always-valid JSON output with error handling
7. Added support for /learners/ endpoint counting
