# Membria + OpenAI Codex Integration

This guide shows how to use Membria decision intelligence tools with OpenAI Codex/GPT models.

## Overview

Membria provides an OpenAI adapter that bridges MCP tools to OpenAI's function calling format. This allows you to use all 7 Membria tools with GPT-4, GPT-4-turbo, and other OpenAI models.

## Quick Start

### 1. Set Environment Variables

```bash
export FALKORDB_HOST=192.168.0.105  # Your FalkorDB server
export OPENAI_API_KEY=your-api-key   # Your OpenAI API key
```

### 2. Use the Adapter

```python
import openai
import json
from openai_adapter import OpenAIAdapter

# Initialize Membria adapter
membria = OpenAIAdapter()

# Create OpenAI client
client = openai.OpenAI()

# Use Membria tools with OpenAI
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "I'm deciding between PostgreSQL and MongoDB for user data. What do you recommend?"}
    ],
    functions=membria.get_functions_schema(),
    function_call="auto"
)

# Handle function calls
message = response.choices[0].message
if message.function_call:
    function_name = message.function_call.name
    arguments = json.loads(message.function_call.arguments)
    result = membria.execute_function(function_name, arguments)
    print(f"Membria result: {result}")
```

## Available Functions

### 1. membria_capture_decision

Capture a decision for team learning.

```python
# OpenAI will automatically call this when user makes a decision
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "I decided to use PostgreSQL for the user database. I'm 85% confident. Alternatives were MongoDB and MySQL."}
    ],
    functions=membria.get_functions_schema()
)
```

### 2. membria_get_decision_context

Get context about past decisions.

```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "What has the team learned about caching strategies?"}
    ],
    functions=membria.get_functions_schema(),
    function_call={"name": "membria_get_decision_context"}
)
```

### 3. membria_get_calibration

Get team calibration data.

```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "How well calibrated is our team in database decisions?"}
    ],
    functions=membria.get_functions_schema()
)
```

### 4. membria_validate_plan

Validate a plan against known failures.

```python
plan = """
1. Setup PostgreSQL database
2. Create REST API
3. Add JWT authentication
4. Deploy to production
"""

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": f"Validate this plan for issues: {plan}"}
    ],
    functions=membria.get_functions_schema()
)
```

### 5. membria_get_plan_context

Get context before planning.

```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "I need to plan an authentication system. What should I know?"}
    ],
    functions=membria.get_functions_schema()
)
```

### 6. membria_record_plan

Record a finalized plan.

```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Save this plan: 1) Setup DB, 2) Create API, 3) Add auth. Domain: backend. Confidence: 0.85"}
    ],
    functions=membria.get_functions_schema()
)
```

### 7. membria_record_outcome

Record decision outcome.

```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "The PostgreSQL migration was successful! Record this outcome."}
    ],
    functions=membria.get_functions_schema()
)
```

## Complete Example: Decision Workflow

```python
import openai
import json
from openai_adapter import OpenAIAdapter

# Initialize
membria = OpenAIAdapter()
client = openai.OpenAI()

def chat_with_membria(user_message: str) -> str:
    """Chat with GPT-4 with Membria tools enabled."""
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system", 
                "content": "You are a helpful assistant with access to Membria decision intelligence tools. Use them proactively to help users make better decisions."
            },
            {"role": "user", "content": user_message}
        ],
        functions=membria.get_functions_schema(),
        function_call="auto"
    )
    
    message = response.choices[0].message
    
    # Handle function calls
    if message.function_call:
        function_name = message.function_call.name
        arguments = json.loads(message.function_call.arguments)
        
        # Execute Membria function
        result = membria.execute_function(function_name, arguments)
        
        # Continue conversation with result
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant with access to Membria decision intelligence tools."},
                {"role": "user", "content": user_message},
                message,  # The function call
                {
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(result)
                }
            ],
            functions=membria.get_functions_schema()
        )
        
        return response.choices[0].message.content
    
    return message.content

# Example usage
print(chat_with_membria("I'm deciding between Redis and Memcached for caching. What does the team know?"))
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FALKORDB_HOST` | `localhost` | FalkorDB server host |
| `FALKORDB_PORT` | `6379` | FalkorDB server port |
| `FALKORDB_PASSWORD` | `None` | FalkorDB password (if any) |
| `OPENAI_API_KEY` | Required | Your OpenAI API key |

## Testing the Adapter

```bash
cd ~/Developer/membria-cli
source venv/bin/activate
FALKORDB_HOST=192.168.0.105 python openai_adapter.py
```

This will show all available functions and test the connection.

## Architecture

```
OpenAI GPT-4
    |
    v
Function Calling API
    |
    v
openai_adapter.py
    |
    v
MembriaMCPServer
    |
    v
FalkorDB (192.168.0.105:6379)
```

## Comparison: Claude vs OpenAI

| Feature | Claude (MCP) | OpenAI (Functions) |
|---------|--------------|-------------------|
| Protocol | MCP (stdio) | OpenAI Functions |
| Configuration | `.claude/claude.json` | Python code |
| Auto-invoke | Yes | Manual handling |
| Tools | 7 Membria tools | 7 Membria tools |
| Real-time | Yes | Yes |

## Troubleshooting

### "Cannot connect to FalkorDB"

```bash
# Check FalkorDB is running
redis-cli -h 192.168.0.105 ping
# Should return: PONG
```

### "OpenAI API error"

```bash
# Check your API key
echo $OPENAI_API_KEY

# Set if needed
export OPENAI_API_KEY=sk-...
```

### "Function not found"

Make sure you're using the correct function names:
- `membria_capture_decision`
- `membria_record_outcome`
- `membria_get_calibration`
- `membria_get_decision_context`
- `membria_get_plan_context`
- `membria_validate_plan`
- `membria_record_plan`

## Next Steps

1. Integrate into your OpenAI-powered applications
2. Add to your CI/CD pipeline for decision tracking
3. Use with GitHub Copilot via VSCode extension
4. Combine with other MCP tools

---

**Version:** 1.0.0  
**Date:** 2026-02-14  
**Status:** Ready for use