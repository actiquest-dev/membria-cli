#!/usr/bin/env python3
"""
Example: Interactive Provider Management System

Demonstrates the new provider management commands in Membria CLI.
"""

# Example 1: View all providers
print("""
$ /settings providers

╭─ Provider Manager ─╮

1. ✓ anthropic (ENABLED)
   Type: anthropic | Model: claude-3-5-sonnet-latest
   Endpoint: default
   Auth: Configured

2. ✓ openai (ENABLED)
   Type: openai | Model: gpt-4-turbo
   Endpoint: https://api.openai.com/v1
   Auth: Configured

3. ✗ kilo (DISABLED)
   Type: kilo | Model: kilo-code
   Endpoint: http://kilo.ai
   Auth: Missing

Quick Commands:
  /settings toggle <name>        Enable/disable provider
  /settings set-key <name> <key> Set API key
  /settings set-model <name> <m> Change model
  /settings test-provider <name> Test connection
  /settings add-provider <name>  Add new provider
  /settings remove <name>        Remove provider
""")

# Example 2: Toggle a provider
print("""
$ /settings toggle kilo
✓ Provider 'kilo' ENABLED

$ /settings toggle kilo
✗ Provider 'kilo' DISABLED
""")

# Example 3: Set API key
print("""
$ /settings set-key anthropic sk-ant-v0-abcdef1234567890
✓ API key set for 'anthropic' (ends with: ...7890)
""")

# Example 4: Change model
print("""
$ /settings set-model anthropic claude-3-opus-latest
✓ Model updated: claude-3-5-sonnet-latest → claude-3-opus-latest

$ /settings set-model openai gpt-3.5-turbo
✓ Model updated: gpt-4-turbo → gpt-3.5-turbo
""")

# Example 5: Test provider
print("""
$ /settings test-provider anthropic

Testing provider: anthropic
  Status: ENABLED
  Type: anthropic
  Model: claude-3-5-sonnet-latest
  Endpoint: default
  Auth: ✓ Configured

✓ Provider configuration valid
""")

# Example 6: Add new provider
print("""
$ /settings add-provider ollama ollama llama2
✓ Provider 'ollama' added successfully

$ /settings set-key ollama http://localhost:11434
✓ API key set for 'ollama' (ends with: ...434)

$ /settings test-provider ollama

Testing provider: ollama
  Status: ENABLED
  Type: ollama
  Model: llama2
  Endpoint: http://localhost:11434
  Auth: ✓ Configured

✓ Provider configuration valid
""")

# Example 7: Remove provider
print("""
$ /settings remove kilo
✓ Provider 'kilo' removed
""")

# Example 8: Switching providers by toggling
print("""
# Use only Anthropic
$ /settings toggle openai
✗ Provider 'openai' DISABLED

$ /settings providers

╭─ Provider Manager ─╮

1. ✓ anthropic (ENABLED)   ← Only this one is active
   Type: anthropic | Model: claude-3-5-sonnet-latest
   Endpoint: default
   Auth: Configured

2. ✗ openai (DISABLED)      ← This one is disabled
   Type: openai | Model: gpt-4-turbo
   Endpoint: https://api.openai.com/v1
   Auth: Configured
""")

# Example 9: Main settings menu
print("""
$ /settings

╭─ Membria Settings ─╮

🔌 Provider Management
  /settings providers              List all providers (interactive)
  /settings toggle <name>          Enable/disable provider
  /settings set-key <name> <key>   Set or update API key
  /settings set-model <name> <m>   Change model for provider
  /settings test-provider <name>   Test provider connection
  /settings add-provider <n> <t>   Add new provider
  /settings remove <name>          Remove provider

👥 Roles & Agents
  /settings roles                  List all expert roles
  /settings assign-role <r> <p>   Assign role to provider
  /settings calibrate <r> <score> Update accuracy score

⚙️  Advanced
  /settings mode                   Show/change orchestration mode
  /settings monitoring             Set monitoring level
  /settings reset                  Reset to defaults

╰──────────────────────────────╯
""")

"""
Key Benefits of New System:

1. **No Removal Required** - Disable instead of delete
2. **Dynamic Configuration** - Change settings without restart
3. **Validation** - Test providers before using them
4. **Multiple Providers** - Easily switch between multiple LLMs
5. **Clear Status** - See which providers are enabled/disabled
6. **Easy Setup** - Add new providers in seconds
7. **Flexible Models** - Switch models per provider
8. **Auth Management** - Update API keys securely

Use Cases:
- A/B testing different LLM providers
- Using cheaper models for development
- Fallback providers if one goes down
- Per-task provider selection
- Easy on-boarding of new providers
"""
