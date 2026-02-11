# Membria CLI

AI-powered decision memory for developers. Phase 1 - Solo Developer Edition.

## Installation

```bash
# Using pipx (recommended)
pipx install membria

# Using pip
pip install membria
```

## Quick Start

```bash
# Initialize Membria
membria init

# Start the MCP daemon
membria daemon start

# Check status
membria doctor
```

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/
```

## Features (Phase 1)

- ✅ Local Reasoning Graph (FalkorDB embedded)
- ✅ MCP Server for Claude Code integration
- ✅ Engrams (Agent Session capture)
- ✅ Decision tracking and retrieval
- ✅ Monty runtime for agent execution
- ✅ Offline-first with graceful degradation

## Documentation

See [membria-cli-spec.md](./membria-cli-spec.md) for full specification.
