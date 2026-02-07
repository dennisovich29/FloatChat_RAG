# FloatChat RAG MCP Server - Setup Guide

## Quick Start

### 1. Test the MCP Server

Run the test script to verify all tools work:

```bash
source .venv/bin/activate
python test_mcp_tools.py
```

You should see:
```
✅ All tests passed!
```

### 2. Configure Claude Desktop

**Step 1:** Copy the configuration file

```bash
# Create Claude config directory if it doesn't exist
mkdir -p ~/Library/Application\ Support/Claude

# Copy the config
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Step 2:** Verify the configuration

The file should contain:
```json
{
  "mcpServers": {
    "floatchat-rag": {
      "command": "python",
      "args": [
        "/Users/dennisprathyushpaul/Desktop/Projects/FloatChat_Rag/FloatChat_RAG/mcp_server/server.py"
      ],
      "cwd": "/Users/dennisprathyushpaul/Desktop/Projects/FloatChat_Rag/FloatChat_RAG"
    }
  }
}
```

### 3. Restart Claude Desktop

1. Quit Claude Desktop completely
2. Reopen Claude Desktop
3. The MCP server will load automatically

### 4. Test in Claude Desktop

Try these queries:

**Query 1: Get Statistics**
```
What ocean data do we have?
```

Expected: Claude will use `get_statistics` tool and tell you about 188 profiles and 18,649 measurements.

**Query 2: Semantic Search**
```
Show me profiles with warm water
```

Expected: Claude will use `search_profiles` and return relevant profiles.

**Query 3: Float Details**
```
Get details for float 13857
```

Expected: Claude will use `get_float_details` and show profile information.

---

## Available Tools

| Tool | What It Does | Example |
|------|--------------|---------|
| `search_profiles` | Semantic search | "warm water profiles" |
| `get_statistics` | Database stats | "what's in the database?" |
| `get_float_details` | Specific float | "details for float 13857" |
| `query_database` | Custom SQL | "SELECT * FROM profiles LIMIT 5" |
| `get_profiles_by_location` | Geographic filter | "profiles between 30°N-40°N" |
| `get_profiles_by_date` | Date filter | "profiles from 1997" |

---

## Troubleshooting

### MCP Server Not Loading

1. Check Claude Desktop logs:
   ```bash
   tail -f ~/Library/Logs/Claude/mcp*.log
   ```

2. Verify paths in config are absolute paths

3. Test server manually:
   ```bash
   python mcp_server/server.py
   ```

### Tools Not Working

Run the test script:
```bash
python test_mcp_tools.py
```

If tests fail, check:
- Virtual environment is activated
- Database exists at `data/databases/argo_data.db`
- ChromaDB is initialized

---

## Next Steps

Once working in Claude Desktop:

1. **Explore your data** with natural language
2. **Share with colleagues** - they can use the same config
3. **Add more tools** - extend `mcp_server/server.py`
4. **Build a web UI** - for non-Claude users

Enjoy chatting with your ocean data! 🌊
