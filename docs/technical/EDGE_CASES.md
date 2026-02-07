# FloatChat RAG MCP Server - Edge Cases & Error Handling

## 1. Database Edge Cases

### Empty Database
**Scenario:** Database exists but has no data
```python
# get_statistics returns:
{
  "profile_count": 0,
  "measurement_count": 0,
  "float_count": 0,
  "date_range": {"earliest": null, "latest": null}
}
```
**Impact:** Tools will return empty results
**Mitigation:** Check if data exists before querying

### Missing Database File
**Scenario:** `data/databases/argo_data.db` doesn't exist
```
Error: sqlite3.OperationalError: unable to open database file
```
**Fix:** Run data pipeline first: `python scripts/run_pipeline.py`

### Corrupted Database
**Scenario:** Database file is corrupted
```
Error: sqlite3.DatabaseError: database disk image is malformed
```
**Fix:** Delete and regenerate database

---

## 2. ChromaDB Edge Cases

### Empty Vector Database
**Scenario:** ChromaDB exists but no embeddings indexed
```python
# search_profiles returns:
{"query": "warm water", "results": []}
```
**Fix:** Run `python scripts/index_vectors.py --index`

### Missing ChromaDB Directory
**Scenario:** `data/vector_db/` doesn't exist
```
Error: chromadb.errors.InvalidDimensionException
```
**Fix:** Create directory and run indexing

### Embedding Model Download Failure
**Scenario:** No internet connection when loading model
```
Error: HTTPError: 503 Server Error
```
**Fix:** Pre-download model or use cached version

---

## 3. MCP Server Edge Cases

### Invalid Float ID
**Scenario:** User requests non-existent float
```bash
# Query: "Get details for float 99999"
```
**Result:**
```json
{
  "float_id": "99999",
  "profile_count": 0,
  "profiles": [],
  "sample_measurements": []
}
```
**Behavior:** Returns empty results, no error

### SQL Injection Attempt
**Scenario:** Malicious SQL in query_database
```bash
# Query: "Run: DROP TABLE profiles"
```
**Protection:**
```python
if not sql.upper().startswith("SELECT"):
    return {"error": "Only SELECT queries are allowed"}
```
**Result:** Blocked ✅

### Invalid Date Format
**Scenario:** Wrong date format in get_profiles_by_date
```bash
# Query: "Profiles from 01/15/2023"  # Wrong format
```
**Result:** SQL error or no results
**Expected:** YYYY-MM-DD format
**Fix:** Add date validation

### Invalid Geographic Bounds
**Scenario:** Invalid lat/lon ranges
```bash
# min_lat > max_lat or min_lon > max_lon
```
**Result:** No results or SQL error
**Fix:** Add bounds validation

---

## 4. Claude Desktop Integration Edge Cases

### Python Not in PATH
**Scenario:** Claude Desktop can't find python
```
Error: spawn python ENOENT
```
**Fix:** Use absolute path in config:
```json
"command": "/path/to/.venv/bin/python"
```

### Virtual Environment Not Activated
**Scenario:** Missing dependencies
```
Error: ModuleNotFoundError: No module named 'mcp'
```
**Fix:** Use venv python in config

### ChromaDB Sandbox Permissions
**Scenario:** Read-only file system in sandbox
```
Error: chromadb.errors.InternalError: Read-only file system
```
**Fix:** Disable telemetry (already implemented):
```python
os.environ["ANONYMIZED_TELEMETRY"] = "False"
```

### Server Crashes During Query
**Scenario:** Unexpected error in tool execution
```python
# Server logs error and returns:
{"error": "Internal server error"}
```
**Behavior:** Server stays running, Claude gets error message

---

## 5. Search Edge Cases

### No Matching Results
**Scenario:** Semantic search finds nothing relevant
```bash
# Query: "profiles on Mars"
```
**Result:**
```json
{"query": "profiles on Mars", "results": []}
```
**Behavior:** Returns empty list, no error

### Very Long Query
**Scenario:** Query exceeds embedding model limits
```bash
# Query: 1000+ words
```
**Result:** May truncate or fail
**Fix:** Add query length validation

### Special Characters in Query
**Scenario:** Query contains SQL special chars
```bash
# Query: "profiles with temperature > 20°C"
```
**Behavior:** Semantic search handles it fine
**SQL queries:** Need proper escaping

---

## 6. Data Consistency Edge Cases

### Profiles Without Measurements
**Scenario:** Profile exists but no measurements
```python
# get_float_details returns:
{
  "float_id": "13857",
  "profile_count": 5,
  "profiles": [...],
  "sample_measurements": []  # Empty
}
```
**Behavior:** Valid response, just empty measurements

### Duplicate Float IDs
**Scenario:** Same float_id with different cycles
```sql
SELECT * FROM profiles WHERE float_id = '13857'
-- Returns multiple rows (different cycles)
```
**Behavior:** All profiles returned correctly

### Missing Metadata Fields
**Scenario:** Profile missing lat/lon or datetime
```python
# Semantic search may have incomplete metadata
{"latitude": null, "longitude": null}
```
**Impact:** Location-based queries won't find it

---

## 7. Performance Edge Cases

### Large Result Sets
**Scenario:** Query returns thousands of rows
```bash
# Query: "SELECT * FROM measurements"  # 18,649 rows
```
**Impact:** Slow response, large JSON payload
**Fix:** Add LIMIT clause or pagination

### Concurrent Requests
**Scenario:** Multiple Claude Desktop instances
```
Multiple MCP servers accessing same ChromaDB
```
**Behavior:** ChromaDB handles concurrent reads
**Risk:** Potential lock contention

### Memory Exhaustion
**Scenario:** Loading large embeddings
```
Embedding model + ChromaDB + Large queries
```
**Impact:** Server may crash
**Fix:** Monitor memory usage, add limits

---

## 8. Configuration Edge Cases

### Wrong Working Directory
**Scenario:** MCP server runs from wrong directory
```json
"cwd": "/wrong/path"
```
**Result:** Can't find data files
**Fix:** Use absolute paths in server.py (already implemented)

### Missing Config File
**Scenario:** `config/config.yaml` missing
```
Error: FileNotFoundError
```
**Impact:** Server may use defaults or fail
**Fix:** Ensure config exists or use fallbacks

---

## 9. Network Edge Cases

### Hugging Face API Rate Limit
**Scenario:** Too many model downloads
```
Error: HTTPError: 429 Too Many Requests
```
**Fix:** Use cached model or wait

### Offline Mode
**Scenario:** No internet connection
```
First run: Can't download embedding model
Subsequent runs: Uses cached model ✅
```

---

## 10. User Input Edge Cases

### Ambiguous Queries
**Scenario:** Unclear natural language
```bash
# Query: "Show me data"  # Too vague
```
**Behavior:** Claude may ask for clarification or use best guess

### Mixed Tool Requirements
**Scenario:** Query needs multiple tools
```bash
# Query: "Compare warm water profiles from 1998 vs 2000"
```
**Behavior:** Claude chains multiple tool calls

### Contradictory Parameters
**Scenario:** Invalid parameter combinations
```bash
# start_date: "2000-01-01", end_date: "1999-01-01"
```
**Result:** No results (end before start)
**Fix:** Add validation

---

## Recommended Improvements

### 1. Add Input Validation
```python
def validate_date_range(start_date, end_date):
    if start_date > end_date:
        raise ValueError("Start date must be before end date")

def validate_bounds(min_lat, max_lat, min_lon, max_lon):
    if not (-90 <= min_lat <= max_lat <= 90):
        raise ValueError("Invalid latitude range")
    if not (-180 <= min_lon <= max_lon <= 180):
        raise ValueError("Invalid longitude range")
```

### 2. Add Result Limits
```python
MAX_RESULTS = 1000

# In query_database:
if len(df) > MAX_RESULTS:
    return {"warning": f"Results truncated to {MAX_RESULTS} rows", ...}
```

### 3. Add Error Recovery
```python
try:
    results = chroma_store.search(query, embedder, k=limit)
except Exception as e:
    logger.error(f"Search failed: {e}")
    return {"error": "Search temporarily unavailable", "details": str(e)}
```

### 4. Add Health Check Tool
```python
Tool(
    name="health_check",
    description="Check if all components are working",
    inputSchema={"type": "object", "properties": {}}
)
```

### 5. Add Logging
```python
# Log all tool calls for debugging
logger.info(f"Tool called: {name} with args: {arguments}")
```

---

## Testing Edge Cases

Run these tests to verify edge case handling:

```bash
# Test empty results
python -c "from mcp_server.server import *; ..."

# Test invalid inputs
# Test concurrent access
# Test memory limits
# Test network failures
```

---

## Monitoring Recommendations

1. **Log all errors** to file for debugging
2. **Track tool usage** to identify common failures
3. **Monitor memory** for large queries
4. **Set up alerts** for server crashes
5. **Version control** config changes
