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
    ├── setup/              # Installation & configuration
    ├── manuals/            # User guides
    └── technical/          # Technical details
```

## Documentation

### Setup & Configuration
- [Quickstart Guide](docs/setup/QUICKSTART.md)
- [Ollama Quickstart](docs/setup/OLLAMA_QUICKSTART.md)
- [Setup for Friends](docs/setup/SETUP_FOR_FRIENDS.md)
- [API Key Guide](docs/setup/API_KEY_GUIDE.md)

### User Manuals
- [Streamlit Guide](docs/manuals/STREAMLIT_GUIDE.md)

### Technical Details
- [Deployment Plan](docs/technical/WEB_DEPLOYMENT_PLAN.md)
- [Free LLM Options](docs/technical/FREE_LLM_OPTIONS.md)
- [Edge Cases](docs/technical/EDGE_CASES.md)

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
ruff format src/ scripts/

# Lint code
ruff check src/ scripts/

# Auto-fix linting issues
ruff check --fix src/ scripts/
```

### Type Checking
```bash
mypy src/
```

---

## License

MIT License - see LICENSE file

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Acknowledgments

- Data from [NOAA's THREDDS server](https://www.ncei.noaa.gov/thredds-ocean/)
- Built with xarray, ChromaDB, and sentence-transformers