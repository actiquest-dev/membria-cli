# Provider Management System - Interactive Menu

## Overview

The `/settings providers` command now features an **interactive provider management system** that replaces the basic static menu. This allows you to dynamically enable, disable, configure, and test LLM providers directly from the CLI.

## Commands

### View All Providers
```bash
/settings providers
```
Shows an interactive menu with all configured providers, their status, models, and endpoints.

**Output Example:**
```
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
```

### Toggle Provider On/Off

Enable or disable a provider without removing it:

```bash
/settings toggle anthropic
```

**Response:**
```
✓ Provider 'anthropic' ENABLED
```

Or to disable:
```
✗ Provider 'openai' DISABLED
```

### Set or Update API Key

Configure authentication for a provider:

```bash
/settings set-key anthropic sk-ant-v0-abc123...
```

**Response:**
```
✓ API key set for 'anthropic' (ends with: ...abc123)
```

### Change Model

Update the model used by a provider:

```bash
/settings set-model openai gpt-4-turbo
```

**Response:**
```
✓ Model updated: gpt-4 → gpt-4-turbo
```

### Test Provider Connection

Verify that a provider is accessible and properly configured:

```bash
/settings test-provider openai
```

**Response:**
```
Testing provider: openai
  Status: ENABLED
  Type: openai
  Model: gpt-4-turbo
  Endpoint: https://api.openai.com/v1
  Auth: ✓ Configured

✓ Provider configuration valid
```

If authentication is missing:
```
Testing provider: kilo
  Status: DISABLED
  Type: kilo
  Model: kilo-code
  Endpoint: http://kilo.ai
  Auth: ⚠ Missing API key

✓ Provider configuration valid
```

### Add New Provider

Create a new provider configuration:

```bash
/settings add-provider claude anthropic claude-3-5-sonnet-latest
```

**Response:**
```
✓ Provider 'claude' added successfully
```

### Remove Provider

Delete a provider from configuration:

```bash
/settings remove kilo
```

**Response:**
```
✓ Provider 'kilo' removed
```

## Use Cases

### Switching Between Providers
Toggle providers on/off to switch between different LLM backends:

```bash
/settings toggle anthropic    # Turn off Anthropic
/settings toggle openai       # Turn on OpenAI
```

### Managing Multiple API Keys
Update API keys for different providers:

```bash
/settings set-key anthropic $ANTHROPIC_KEY
/settings set-key openai $OPENAI_KEY
/settings set-key kilo $KILO_KEY
```

### Testing Connectivity
Before using a provider, test that it's properly configured:

```bash
/settings test-provider anthropic
/settings test-provider openai
/settings test-provider kilo
```

### Configuring Custom Models
Switch between different models for the same provider:

```bash
/settings set-model anthropic claude-3-opus-latest
/settings set-model openai gpt-4-turbo
/settings set-model openai gpt-3.5-turbo  # Cheaper alternative
```

### Adding Custom Providers
Add new LLM providers (e.g., locally hosted models):

```bash
/settings add-provider ollama ollama llama2
/settings set-key ollama http://localhost:11434
```

## Configuration Storage

Provider settings are stored in `claude_config.json`:

```json
{
  "providers": {
    "anthropic": {
      "type": "anthropic",
      "model": "claude-3-5-sonnet-latest",
      "api_key": "sk-ant-v0-...",
      "endpoint": "https://api.anthropic.com/v1",
      "enabled": true
    },
    "openai": {
      "type": "openai",
      "model": "gpt-4-turbo",
      "api_key": "sk-...",
      "endpoint": "https://api.openai.com/v1",
      "enabled": true
    },
    "kilo": {
      "type": "kilo",
      "model": "kilo-code",
      "api_key": "",
      "endpoint": "http://kilo.ai",
      "enabled": false
    }
  }
}
```

## Status Indicators

- **✓ ENABLED** - Provider is active and ready to use
- **✗ DISABLED** - Provider is configured but not active
- **✓ Configured** - Authorization is set
- **⚠ Missing** - API key needs to be configured

## Workflow

Typical workflow for setting up a new provider:

1. **Add provider** → `/settings add-provider myai mytype mymodel`
2. **Set API key** → `/settings set-key myai <your-api-key>`
3. **Test connection** → `/settings test-provider myai`
4. **Enable if valid** → `/settings toggle myai`
5. **Check list** → `/settings providers`

## Main Settings Menu

View all provider-related commands:

```bash
/settings
```

Shows the complete settings menu with all provider management options, roles configuration, and advanced settings.
