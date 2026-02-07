# Quick Start for GitHub Users

## 🚀 5-Minute Setup

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/FloatChat_RAG.git
cd FloatChat_RAG

# 2. Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Setup environment
uv venv
source .venv/bin/activate
uv pip install -e .

# 4. Fetch data
python scripts/run_pipeline.py

# 5. Index vectors
python scripts/index_vectors.py --index

# 6. Test
python test_mcp_tools.py
```

## 📋 Configure Claude Desktop

```bash
# Generate config
python -c "
import json
from pathlib import Path

p = Path.cwd().absolute()
config = {
    'mcpServers': {
        'floatchat-rag': {
            'command': str(p / '.venv' / 'bin' / 'python'),
            'args': [str(p / 'mcp_server' / 'server.py')],
            'cwd': str(p)
        }
    }
}
print(json.dumps(config, indent=2))
"

# Copy output to: ~/Library/Application Support/Claude/claude_desktop_config.json
# Restart Claude Desktop
```

## ✅ Test Queries

- "What ocean data do we have?"
- "Show me warm water profiles"
- "Get details for float 13857"

**Full guide:** See `SETUP_FOR_FRIENDS.md`
