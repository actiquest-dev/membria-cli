#!/usr/bin/env python3
"""
OpenAI Codex Adapter for Membria MCP Server

This adapter bridges Membria MCP tools to OpenAI's function calling format.
It allows using Membria decision intelligence tools with OpenAI Codex/GPT models.

Usage:
    python openai_adapter.py

Then use the OpenAI API with functions defined in openai_functions.json
"""

import os
import sys
import json
import subprocess
from typing import Dict, Any, List, Optional

# Add membria to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from membria.mcp_server import MembriaMCPServer


class OpenAIAdapter:
    """Adapter to use Membria MCP tools with OpenAI function calling."""
    
    def __init__(self):
        self.server = MembriaMCPServer()
        
    def get_functions_schema(self) -> List[Dict[str, Any]]:
        """Get OpenAI function definitions for Membria tools."""
        return [
            {
                "name": "membria_capture_decision",
                "description": "Capture a decision for team learning. Records the decision statement, alternatives considered, and confidence level.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "statement": {
                            "type": "string",
                            "description": "The decision statement (e.g., 'Use PostgreSQL for user database')"
                        },
                        "alternatives": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of alternative options considered"
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Confidence level from 0 to 1"
                        },
                        "module": {
                            "type": "string",
                            "description": "Module or domain (e.g., 'database', 'auth', 'api')"
                        }
                    },
                    "required": ["statement", "alternatives", "confidence"]
                }
            },
            {
                "name": "membria_record_outcome",
                "description": "Record the outcome of a decision after implementation. Used for calibration and learning.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "decision_id": {
                            "type": "string",
                            "description": "ID of the decision to update"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["success", "failure", "partial"],
                            "description": "Outcome status"
                        },
                        "score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Outcome score from 0 to 1"
                        },
                        "domain": {
                            "type": "string",
                            "description": "Decision domain"
                        }
                    },
                    "required": ["decision_id", "status"]
                }
            },
            {
                "name": "membria_get_calibration",
                "description": "Get team calibration data for a domain. Shows success rates and confidence gaps.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "Domain to get calibration for (e.g., 'database', 'auth')"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "membria_get_decision_context",
                "description": "Get context for a decision, including past decisions, success rates, and warnings.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "statement": {
                            "type": "string",
                            "description": "Decision statement to get context for"
                        },
                        "module": {
                            "type": "string",
                            "description": "Module or domain"
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Your current confidence level"
                        }
                    },
                    "required": ["statement"]
                }
            },
            {
                "name": "membria_get_plan_context",
                "description": "PRE-PLAN: Get context before planning. Returns past plans, patterns, and recommendations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "Domain for planning (e.g., 'auth', 'database')"
                        },
                        "scope": {
                            "type": "string",
                            "description": "Scope of the plan"
                        }
                    },
                    "required": ["domain"]
                }
            },
            {
                "name": "membria_validate_plan",
                "description": "MID-PLAN: Validate a plan against known failures and antipatterns.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of plan steps"
                        },
                        "domain": {
                            "type": "string",
                            "description": "Domain for validation"
                        }
                    },
                    "required": ["steps"]
                }
            },
            {
                "name": "membria_record_plan",
                "description": "POST-PLAN: Record a finalized plan for future reference and learning.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "plan_steps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of plan steps"
                        },
                        "domain": {
                            "type": "string",
                            "description": "Domain of the plan"
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Confidence in the plan (0-1)"
                        },
                        "duration_estimate": {
                            "type": "string",
                            "description": "Estimated duration"
                        }
                    },
                    "required": ["plan_steps", "domain"]
                }
            }
        ]
    
    def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Membria function and return the result."""
        
        # Map OpenAI function names to MCP tool names
        tool_mapping = {
            "membria_capture_decision": "membria.capture_decision",
            "membria_record_outcome": "membria.record_outcome",
            "membria_get_calibration": "membria.get_calibration",
            "membria_get_decision_context": "membria.get_decision_context",
            "membria_get_plan_context": "membria.get_plan_context",
            "membria_validate_plan": "membria.validate_plan",
            "membria_record_plan": "membria.record_plan"
        }
        
        tool_name = tool_mapping.get(function_name)
        if not tool_name:
            return {"error": f"Unknown function: {function_name}"}
        
        # Create MCP request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        # Execute via MCP server
        response = self.server.handle_request(request)
        
        if response.error:
            return {"error": response.error}
        
        # Parse the result
        if response.result and "content" in response.result:
            for content in response.result["content"]:
                if content.get("type") == "text":
                    try:
                        return json.loads(content["text"])
                    except json.JSONDecodeError:
                        return {"result": content["text"]}
        
        return response.result or {}


def create_openai_client_example():
    """Example of how to use Membria with OpenAI API."""
    return '''
import openai
from openai_adapter import OpenAIAdapter

# Initialize adapter
membria = OpenAIAdapter()

# Create OpenAI client
client = openai.OpenAI(api_key="your-api-key")

# Example 1: Capture decision
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "I decided to use PostgreSQL for the user database. I'm 85% confident."}
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
    print(f"Function result: {result}")

# Example 2: Get decision context
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "What do we know about caching decisions?"}
    ],
    functions=membria.get_functions_schema(),
    function_call={"name": "membria_get_decision_context"}
)

# Example 3: Validate plan
plan_steps = [
    "Setup database schema",
    "Create API endpoints",
    "Add authentication"
]

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": f"Validate this plan: {plan_steps}"}
    ],
    functions=membria.get_functions_schema(),
    function_call={"name": "membria_validate_plan"}
)
'''


def main():
    """Main entry point for testing."""
    print("Membria OpenAI Adapter")
    print("=" * 50)
    
    # Set FalkorDB host
    os.environ["FALKORDB_HOST"] = os.environ.get("FALKORDB_HOST", "192.168.0.105")
    
    adapter = OpenAIAdapter()
    
    # Print available functions
    print("\nAvailable OpenAI Functions:")
    print("-" * 50)
    for func in adapter.get_functions_schema():
        print(f"  • {func['name']}")
        print(f"    {func['description'][:60]}...")
    
    # Test a function
    print("\nTesting membria_get_calibration:")
    print("-" * 50)
    result = adapter.execute_function("membria_get_calibration", {"domain": "general"})
    print(json.dumps(result, indent=2))
    
    print("\n" + "=" * 50)
    print("Adapter ready for OpenAI function calling!")
    print("\nUsage example:")
    print(create_openai_client_example())


if __name__ == "__main__":
    main()
