# FloatChat RAG - Setup Guide for Friends

## Quick Start (5 minutes)

### Prerequisites
- macOS (for Claude Desktop)
- Python 3.8+
- [uv](https://github.com/astral-sh/uv) package manager
- [Claude Desktop](https://claude.ai/download)

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/FloatChat_RAG.git
cd FloatChat_RAG
```

---

## Step 2: Install uv (if not installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Step 3: Create Virtual Environment & Install Dependencies

```bash
# Create virtual environment
uv venv

# Activate it
source .venv/bin/activate

# Install all dependencies
uv pip install -e .
```

This will install:
- Core dependencies (xarray, pandas, requests, etc.)
- Vector DB (chromadb, sentence-transformers)
- MCP server (mcp)
- Dev tools (ruff, pytest, mypy)

---

## Step 4: Fetch Sample Data

```bash
# Run the data pipeline to fetch Argo float data
python scripts/run_pipeline.py
```

This will:
- Fetch 2 Argo floats from AOML data center
- Store data in `data/databases/argo_data.db`
- Save processed Parquet files

**Expected output:**
```
✓ Fetched 188 profiles
✓ Saved to database
```

---

## Step 5: Index Vector Database

```bash
# Create embeddings for semantic search
python scripts/index_vectors.py --index
```

This will:
- Download embedding model (all-MiniLM-L6-v2)
- Generate embeddings for all 188 profiles
- Store in ChromaDB at `data/vector_db/`

**Expected output:**
```
✓ Successfully indexed 188 profiles
```

---

## Step 6: Test the MCP Server

```bash
# Run test script
python test_mcp_tools.py
```

**Expected output:**
```
✅ All tests passed!
```

---

## Step 7: Configure Claude Desktop

### Create config file:

```bash
# Get your absolute path
pwd
# Copy this path, you'll need it
```

### Edit Claude Desktop config:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "floatchat-rag": {
      "command": "/ABSOLUTE/PATH/TO/FloatChat_RAG/.venv/bin/python",
      "args": [
        "/ABSOLUTE/PATH/TO/FloatChat_RAG/mcp_server/server.py"
      ],
      "cwd": "/ABSOLUTE/PATH/TO/FloatChat_RAG"
    }
  }
}
```

**Replace `/ABSOLUTE/PATH/TO/FloatChat_RAG` with your actual path from `pwd`**

### Quick config script:

```bash
# Run this to generate the config automatically
python -c "
import json
from pathlib import Path

project_path = Path.cwd().absolute()
config = {
    'mcpServers': {
        'floatchat-rag': {
            'command': str(project_path / '.venv' / 'bin' / 'python'),
            'args': [str(project_path / 'mcp_server' / 'server.py')],
            'cwd': str(project_path)
        }
    }
}
print(json.dumps(config, indent=2))
print('\n📋 Copy the above to:')
print('~/Library/Application Support/Claude/claude_desktop_config.json')
"
```

---

## Step 8: Restart Claude Desktop

```bash
# Quit Claude Desktop completely
killall Claude

# Reopen it
open -a Claude
```

---

## Step 9: Test in Claude Desktop

Try these queries:

### Query 1: Get Statistics
```
What ocean data do we have?
```

**Expected:** Claude tells you about 188 profiles, 18,649 measurements, 2 floats

### Query 2: Semantic Search
```
Show me warm water profiles
```

**Expected:** Claude returns relevant profiles using semantic search

### Query 3: Float Details
```
Get details for float 13857
```

**Expected:** Claude shows profile and measurement data

---

## Troubleshooting

### MCP Server Not Loading

Check logs:
```bash
tail -f ~/Library/Logs/Claude/mcp-server-floatchat-rag.log
```

Should see:
```
INFO:__main__:✓ Components initialized successfully
INFO:__main__:FloatChat RAG MCP Server running on stdio
```

### Common Issues

**1. "spawn python ENOENT"**
- Fix: Use absolute path to `.venv/bin/python` in config

**2. "ModuleNotFoundError: No module named 'mcp'"**
- Fix: Make sure you ran `uv pip install -e .`

**3. "Read-only file system"**
- Fix: Already handled in server.py (telemetry disabled)

**4. Empty database**
- Fix: Run `python scripts/run_pipeline.py` first

**5. No search results**
- Fix: Run `python scripts/index_vectors.py --index`

---

## Project Structure

```
FloatChat_RAG/
├── mcp_server/          # MCP server (6 tools, 2 resources)
│   ├── __init__.py
│   └── server.py
├── src/floatchat/       # Core RAG pipeline
│   ├── api/             # Argo API client
│   ├── pipeline/        # Data processing
│   └── vector_db/       # ChromaDB & embeddings
├── scripts/             # Utility scripts
│   ├── run_pipeline.py  # Fetch data
│   └── index_vectors.py # Create embeddings
├── data/                # Data storage (gitignored)
│   ├── databases/       # SQLite
│   ├── processed/       # Parquet files
│   └── vector_db/       # ChromaDB
├── tests/               # Unit tests
└── config/              # Configuration files
```

---

## Available MCP Tools

| Tool | Description | Example |
|------|-------------|---------|
| `search_profiles` | Semantic search | "warm water profiles" |
| `get_statistics` | Database stats | "what's in the database?" |
| `get_float_details` | Specific float | "details for float 13857" |
| `query_database` | Custom SQL | "SELECT * FROM profiles LIMIT 5" |
| `get_profiles_by_location` | Geographic filter | "profiles between 30°N-40°N" |
| `get_profiles_by_date` | Date filter | "profiles from 1997" |

---

## Development

### Run Tests
```bash
pytest tests/
```

### Format Code
```bash
source .venv/bin/activate
ruff format src/ scripts/ mcp_server/
ruff check --fix src/ scripts/ mcp_server/
```

### Type Checking
```bash
mypy src/
```

---

## Adding More Data

To fetch more floats:

```python
# Edit scripts/run_pipeline.py
stream_multiple_floats(
    data_center="aoml",
    num_floats=10,  # Change this
    db_url="sqlite:///data/databases/argo_data.db"
)
```

Then re-run:
```bash
python scripts/run_pipeline.py
python scripts/index_vectors.py --index
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

---

## Support

- **Issues:** Open a GitHub issue
- **Documentation:** See `README.md`, `MCP_SETUP.md`, `EDGE_CASES.md`
- **Logs:** `~/Library/Logs/Claude/mcp-server-floatchat-rag.log`

---

## What You'll Have

After setup, you can:
- ✅ Query oceanographic data using natural language
- ✅ Perform semantic search on 188 Argo float profiles
- ✅ Run custom SQL queries via Claude
- ✅ Filter by location and date
- ✅ Get detailed float information

**Enjoy exploring ocean data with AI!** 🌊
