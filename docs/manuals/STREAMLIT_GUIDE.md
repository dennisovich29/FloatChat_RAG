# Streamlit Web App - Quick Start

## 🚀 Run Locally

### 1. Set up API Key

Create a `.env` file:
```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 2. Run the App

```bash
source .venv/bin/activate
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## 📋 Features

- **Chat Interface**: Natural language queries
- **6 Tools**: Semantic search, stats, SQL queries, location/date filters
- **Sidebar**: Quick stats and example queries
- **Tool Tracking**: See which tools the AI used
- **Conversation History**: Full chat context

---

## 💡 Example Queries

- "What ocean data do we have?"
- "Show me warm water profiles"
- "Get details for float 13857"
- "Profiles from the Atlantic Ocean"
- "Show me profiles from 1998"

---

## 🌐 Deploy to Streamlit Cloud

### 1. Push to GitHub

```bash
git add .
git commit -m "Add Streamlit app"
git push
```

### 2. Deploy

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Select your repository
4. Set main file: `app.py`
5. Add secret: `ANTHROPIC_API_KEY = your_key`
6. Click "Deploy"

Done! Your app is live in ~2 minutes.

---

## 🔧 Troubleshooting

### "ANTHROPIC_API_KEY not found"
- Make sure `.env` file exists
- Check the key is correct
- Restart the app

### "Failed to initialize components"
- Run `python scripts/run_pipeline.py` first
- Run `python scripts/index_vectors.py --index`
- Check database exists at `data/databases/argo_data.db`

### Tools not working
- Check ChromaDB is indexed
- Verify database has data
- Check logs in terminal

---

## 📊 Architecture

```
User Browser
    ↓
Streamlit UI (app.py)
    ↓
LangChain Agent
    ↓
Claude API (Anthropic)
    ↓
6 Tools → ChromaDB + SQLite
```

---

## 🎨 Customization

### Change LLM Model

Edit `app.py`:
```python
llm = ChatAnthropic(
    model="claude-3-opus-20240229",  # or claude-3-haiku-20240307
    temperature=0
)
```

### Add More Tools

```python
@tool
def my_new_tool(param: str) -> str:
    """Tool description for the LLM"""
    # Your logic here
    return result

# Add to tools list
tools = [
    search_profiles,
    get_statistics,
    my_new_tool,  # Add here
    # ...
]
```

### Customize UI

Edit the CSS in `app.py`:
```python
st.markdown("""
<style>
    .main-header {
        /* Your styles */
    }
</style>
""", unsafe_allow_html=True)
```

---

## 📝 Requirements

Already installed via `uv pip install`:
- streamlit
- langchain
- langchain-anthropic
- python-dotenv

Plus existing dependencies:
- chromadb
- sentence-transformers
- sqlalchemy
- pandas

---

**Enjoy your web-based RAG system!** 🌊
