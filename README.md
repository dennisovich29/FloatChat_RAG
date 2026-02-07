# FloatChat RAG - Argo Float Data Pipeline

A robust data pipeline for fetching, processing, and semantically searching Argo oceanographic float data with RAG (Retrieval-Augmented Generation) capabilities.

## Features

- **Direct API Access**: Stream data from NOAA's THREDDS server without downloads
- **Robust Fallback**: Automatic HTTPS download when OPeNDAP streaming fails
- **Parallel Processing**: Multi-threaded data fetching with thread-safe database writes
- **Vector Database**: Semantic search over float metadata using ChromaDB
- **Multiple Formats**: Export to SQLite and Parquet
- **Production Ready**: Proper package structure, configuration, and error handling

## Project Structure

```
FloatChat_RAG/
├── src/floatchat/          # Source code
│   ├── pipeline/           # Data pipeline
│   │   ├── client.py       # API client
│   │   ├── processor.py    # Data processor
│   │   └── runner.py       # Pipeline orchestration
│   └── vector_db/          # Vector database
│       ├── embedder.py     # Embeddings
│       └── store.py        # ChromaDB storage
├── scripts/                # Executable scripts
│   ├── run_pipeline.py     # Run data pipeline
│   ├── index_vectors.py    # Index vector DB
│   └── check_db.py         # Database inspection
├── data/                   # Data storage
│   ├── databases/          # SQLite databases
│   ├── processed/          # Parquet files
│   └── vector_db/          # ChromaDB storage
├── config/                 # Configuration
│   └── config.yaml         # Settings
├── tests/                  # Unit tests
└── docs/                   # Documentation
```

## Installation

### Option 1: Development Install
```bash
# Clone the repository
git clone https://github.com/yourusername/FloatChat_RAG.git
cd FloatChat_RAG

# Install in editable mode
pip install -e .
```

### Option 2: Regular Install
```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Run the Data Pipeline
```bash
# Using the installed command
floatchat-pipeline

# Or directly
python scripts/run_pipeline.py
```

### 2. Index Vector Database
```bash
# Index existing data
python scripts/index_vectors.py --index
```

### 3. Semantic Search
```bash
# Search for floats
python scripts/index_vectors.py --query "warm water in the Atlantic" --limit 5
```

### 4. Check Database
```bash
python scripts/check_db.py
```

## Configuration

Edit `config/config.yaml` to customize:
- Data center and number of floats
- Database paths
- Vector DB settings
- API parameters

## Usage Examples

### Programmatic Access
```python
from floatchat import ArgoAPIClient, ArgoStreamProcessor

# Fetch data
client = ArgoAPIClient()
floats = client.list_floats("aoml", max_floats=5)

# Process data
processor = ArgoStreamProcessor()
for float_id in floats:
    ds, _ = client.fetch_float_data("aoml", float_id)
    if ds:
        processor.stream_to_sql(ds, float_id, "aoml")
```

### Vector Search
```python
from floatchat import ArgoMetadataEmbedder, ArgoChromaStore

embedder = ArgoMetadataEmbedder()
store = ArgoChromaStore()

results = store.search("floats near the equator", embedder, k=5)
print(results)
```

## Architecture

### Producer-Consumer Pattern
- **5 Producer Threads**: Fetch data in parallel (I/O-bound)
- **1 Consumer Thread**: Write to SQLite sequentially (prevents locking)
- **Thread-Safe Queue**: Coordinates data flow

### Hybrid Data Access
1. **Primary**: OPeNDAP streaming (fast, direct)
2. **Fallback**: HTTPS download (reliable when streaming fails)
3. **Memory Safe**: Immediate cleanup of temporary files

## Development

### Run Tests
```bash
pytest tests/
```

### Code Formatting & Linting
```bash
# Activate venv first
source .venv/bin/activate

# Format code
ruff format src/ scripts/ mcp_server/

# Lint code
ruff check src/ scripts/ mcp_server/

# Auto-fix linting issues
ruff check --fix src/ scripts/ mcp_server/
```

### Type Checking
```bash
mypy src/
```

---

## MCP Server Integration

### What is MCP?

The **Model Context Protocol (MCP)** server enables LLM clients like Claude Desktop to query your Argo float data using natural language.

### Installation

MCP SDK is already included in the dependencies. If you need to install it separately:

```bash
uv pip install mcp
```

### Running the MCP Server

```bash
python mcp_server/server.py
```

The server runs on stdio and communicates via the MCP protocol.

### Claude Desktop Configuration

Add this to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "floatchat-rag": {
      "command": "python",
      "args": [
        "/absolute/path/to/FloatChat_RAG/mcp_server/server.py"
      ],
      "cwd": "/absolute/path/to/FloatChat_RAG"
    }
  }
}
```

### Available Tools

1. **search_profiles** - Semantic search using natural language
   ```
   "Show me temperature profiles near the equator"
   ```

2. **get_statistics** - Database statistics
   ```
   "What's in the database?"
   ```

3. **get_float_details** - Specific float information
   ```
   "Get details for float 13857"
   ```

4. **query_database** - Custom SQL queries
   ```
   "Run: SELECT * FROM profiles WHERE latitude > 0 LIMIT 10"
   ```

5. **get_profiles_by_location** - Geographic filtering
   ```
   "Find profiles between 30°N-40°N and 120°W-130°W"
   ```

6. **get_profiles_by_date** - Temporal filtering
   ```
   "Show profiles from January 2023"
   ```

### Available Resources

- **argo://profiles/recent** - Last 20 profiles
- **argo://database/schema** - Database schema information

### Example Usage in Claude

Once configured, you can chat with your data:

```
You: "What ocean data do we have?"
Claude: [Uses get_statistics tool]
        "We have 188 profiles and 18,649 measurements from 2 floats..."

You: "Show me profiles with warm water"
Claude: [Uses search_profiles tool]
        "Here are 5 profiles with warm water characteristics..."

You: "Get details for float 13857"
Claude: [Uses get_float_details tool]
        "Float 13857 has 140 profiles recorded between..."
```

---

## License

MIT License - see LICENSE file

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Acknowledgments

- Data from [NOAA's THREDDS server](https://www.ncei.noaa.gov/thredds-ocean/)
- Built with xarray, ChromaDB, and sentence-transformers