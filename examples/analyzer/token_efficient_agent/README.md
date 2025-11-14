# Token-Efficient Agent

Interactive CLI agent that generates and executes Python code for data analysis with 90%+ token efficiency.

## Quick Start

### Setup

```bash
# From project root
uv sync
source .venv/bin/activate
cd examples/analyzer/token_efficient_agent
```

### Option 1: Pre-build (recommended)

```bash
# 1. Pre-build the Docker image
./build.sh

# 2. Run the CLI with pre-built image
./run_cli.sh --image token-efficient-agent
```

This is fastest - image is ready before you start chatting.

### Option 2: Auto-build (slower first run)

```bash
# Run the CLI (builds Docker image automatically on first execution)
./run_cli.sh
```

Note: First run takes 3-5 minutes to build the Docker image.

**Important**: Use `./run_cli.sh` instead of `uv run cli.py` or `python cli.py` to avoid stdin buffering issues with interactive input.

## How It Works

### Architecture

```
Agent (Host) → Generates code, manages conversation
    ↓
Sandbox (gVisor Container) → Executes code with volume mounts
    ├── /mnt/datasets    (mounted from ../datasets/)
    ├── /mnt/servers     (mounted from ../servers/)
    └── Persistent Python session
```

### Token Efficiency

**Traditional**: Send 100KB CSV in every prompt = 150K tokens across 3 turns

**This approach**: Generate code that loads CSV once = 8K tokens across 3 turns

**Savings: 94%**

### Example Interaction

```
You: What datasets are available?

Agent: I'll check for you.

```python
import sys
sys.path.append('/mnt')

async def main():
    from servers.filesystem import list_directory
    result = await list_directory("/mnt/datasets")
    for entry in result['entries']:
        print(f"{entry['name']}")

import asyncio
asyncio.run(main())
```

[Executing code...]
car_price_prediction_.csv

You: Load it and show summary stats

Agent: [Generates code that uses the same session - df persists!]
```

## Features

- **Streaming responses** - See agent thinking in real-time
- **Session persistence** - Variables persist across turns
- **Volume mounts** - Direct access to datasets (no uploads)
- **MCP tools** - Secure filesystem operations
- **Sandboxed** - Runs in gVisor-isolated container

## Commands

- `/exit` - Quit
- `/clear` - Clear conversation history
- `/help` - Show help

## Files

- `agent.py` - Core agent with streaming and code execution
- `cli.py` - Interactive terminal interface
- `Dockerfile` - Container image with Node.js + Python packages

## Requirements

- Docker with gVisor (recommended)
- OpenAI API key (in .env file at project root)
- Python packages: ray, openai, python-dotenv, docker

## Customization

### Add Python packages

Edit `Dockerfile`:
```dockerfile
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    your-package
```

Rebuild: `docker build -t token-efficient-agent .`

### Change model

Edit `cli.py`:
```python
agent = TokenEfficientAgent(..., model="gpt-4o-mini")
```

### Adjust timeout

Edit `agent.py`:
```python
execute_code.remote(..., timeout=120)  # 2 minutes
```
