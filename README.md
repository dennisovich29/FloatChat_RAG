# FloatChat_RAG

# ARGO Float Data Pipeline

Automated pipeline to fetch, process, and analyze ARGO oceanographic float data from NOAA THREDDS server.

## Features

- 🌊 Direct API access to ARGO float data (no downloads required)
- 📊 Convert NetCDF to SQL and Parquet formats
- 🔍 Vector database integration (FAISS & ChromaDB) for semantic search
- 🚀 Fast, scalable, and production-ready

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/argo-pipeline.git
cd argo-pipeline
```

### 2. Create Virtual Environment

**Important:** Always use a virtual environment!

```bash
# Create venv
python -m venv venv

# Activate it
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python -c "import xarray; import pandas; print('✓ All dependencies installed!')"
```

## Quick Start

### Fetch Data via API

```bash
python argo_api_pipeline.py
```

This will:
1. Connect to NOAA THREDDS server
2. Download 10 floats from AOML center
3. Convert to SQL and Parquet
4. Create `argo_data.db` database

### Populate Vector Database

```bash
python argo_vector_db.py
```

This creates semantic search indexes for intelligent querying.

## Project Structure

```
argo-pipeline/
├── argo_api_pipeline.py      # Main data fetching & processing
├── argo_vector_db.py          # Vector database integration
├── requirements.txt           # Python dependencies
├── .gitignore                # Git ignore rules
├── README.md                 # This file
├── venv/                     # Virtual environment (not in git)
├── argo_data.db              # SQLite database (created)
├── argo_output/              # Parquet files (created)
├── faiss_index/              # FAISS indexes (created)
└── chroma_db/                # ChromaDB storage (created)
```

## Usage Examples

### Example 1: Fetch Data

```python
from argo_api_pipeline import stream_multiple_floats

stream_multiple_floats(
    data_center='atlantic',
    num_floats=50,
    db_url="sqlite:///argo_data.db"
)
```

### Example 2: Query with SQL

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("sqlite:///argo_data.db")

query = """
SELECT * FROM profiles 
WHERE latitude BETWEEN 30 AND 40 
AND longitude BETWEEN -80 AND -60
"""
data = pd.read_sql(query, engine)
```

### Example 3: Semantic Search

```python
from argo_vector_db import ArgoMetadataEmbedder, ArgoChromaStore

embedder = ArgoMetadataEmbedder()
chroma = ArgoChromaStore()

query = "warm tropical Pacific profiles from 2024"
embedding = embedder.embed_text(query)

results = chroma.search(embedding, k=10)
```

## Configuration

### Using PostgreSQL Instead of SQLite

```python
DB_URL = "postgresql://user:password@localhost:5432/argo_db"
stream_multiple_floats(data_center='aoml', db_url=DB_URL)
```

### GPU Acceleration for Vector Search

Edit `requirements.txt`:
```txt
# Replace:
faiss-cpu>=1.7.4
# With:
faiss-gpu>=1.7.4
```

Then reinstall:
```bash
pip install -r requirements.txt --force-reinstall
```

## Troubleshooting

### "Module not found" error
```bash
# Make sure venv is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### "Database locked" error
SQLite doesn't handle concurrent writes well. Use PostgreSQL for production:
```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb argo_db

# Update DB_URL in code
```

### Slow downloads
The THREDDS server may be slow. Use parallel processing:
```python
# In argo_api_pipeline.py, use ThreadPoolExecutor for concurrent downloads
```

## Development

### Adding New Features

1. Create a new branch:
```bash
git checkout -b feature/my-new-feature
```

2. Make changes and test

3. Commit and push:
```bash
git add .
git commit -m "Add new feature"
git push origin feature/my-new-feature
```

4. Create a Pull Request on GitHub

### Running Tests

```bash
pytest tests/
```

## Team Workflow

### Daily Workflow

```bash
# 1. Pull latest changes
git pull origin main

# 2. Activate venv
source venv/bin/activate

# 3. Update dependencies (if requirements.txt changed)
pip install -r requirements.txt

# 4. Work on your code
# ...

# 5. Commit changes
git add .
git commit -m "Your message"
git push origin your-branch
```

### If Someone Updated Dependencies

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

## Data Sources

- **NOAA THREDDS Server**: https://www.ncei.noaa.gov/thredds-ocean/catalog/argo/gadr/catalog.html
- **Argo Program**: https://argo.ucsd.edu/

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file

## Contact

- Your Name - your.email@example.com
- Project Link: https://github.com/yourusername/argo-pipeline

## Acknowledgments

- NOAA for providing ARGO float data
- Argo Program for oceanographic measurements