# FloatChat RAG - Web Deployment Plan

## Overview

Deploy your FloatChat RAG system as a web application so anyone can query oceanographic data through a browser interface.

---

## Architecture Options

### Option 1: Simple Chat Interface (Recommended for MVP)
**Stack:** FastAPI + React + LangChain
**Deployment:** Vercel (Frontend) + Railway/Render (Backend)
**Cost:** Free tier available

### Option 2: Full-Featured Dashboard
**Stack:** Next.js + Python Backend + Plotly
**Deployment:** Vercel (Full-stack)
**Cost:** Free tier available

### Option 3: Streamlit (Fastest to Deploy)
**Stack:** Streamlit (All-in-one)
**Deployment:** Streamlit Cloud
**Cost:** Free

---

## Recommended: Option 1 (FastAPI + React)

### Backend: FastAPI Server

```python
# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate
from langchain.tools import tool
import os

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize your existing components
from floatchat.vector_db.embedder import ArgoMetadataEmbedder
from floatchat.vector_db.store import ArgoChromaStore
from sqlalchemy import create_engine

embedder = ArgoMetadataEmbedder()
chroma_store = ArgoChromaStore()
db_engine = create_engine("sqlite:///data/databases/argo_data.db")

# Create LangChain tools from your existing functions
@tool
def search_profiles(query: str, limit: int = 5) -> dict:
    """Search Argo profiles using semantic search."""
    results = chroma_store.search(query, embedder, k=limit)
    output = {"query": query, "results": []}
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        output["results"].append({"description": doc, "metadata": meta})
    return output

@tool
def get_statistics() -> dict:
    """Get database statistics."""
    with db_engine.connect() as conn:
        from sqlalchemy import text
        profile_count = conn.execute(text("SELECT COUNT(*) FROM profiles")).scalar()
        measurement_count = conn.execute(text("SELECT COUNT(*) FROM measurements")).scalar()
        float_count = conn.execute(text("SELECT COUNT(DISTINCT float_id) FROM profiles")).scalar()
        return {
            "profile_count": profile_count,
            "measurement_count": measurement_count,
            "float_count": float_count
        }

# Add more tools...

# Create LangChain agent
tools = [search_profiles, get_statistics]
llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", api_key=os.getenv("ANTHROPIC_API_KEY"))
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an oceanography assistant. Help users explore Argo float data."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    tools_used: list[str] = []

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint"""
    try:
        result = agent_executor.invoke({"input": request.message})
        return ChatResponse(
            response=result["output"],
            tools_used=[step.tool for step in result.get("intermediate_steps", [])]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}
```

### Frontend: React Chat Interface

```typescript
// frontend/src/App.tsx
import React, { useState } from 'react';
import axios from 'axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  tools_used?: string[];
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/chat', {
        message: input
      });

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.response,
        tools_used: response.data.tools_used
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header>
        <h1>🌊 FloatChat RAG</h1>
        <p>Explore oceanographic data with AI</p>
      </header>

      <div className="chat-container">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="content">{msg.content}</div>
            {msg.tools_used && msg.tools_used.length > 0 && (
              <div className="tools">
                Tools used: {msg.tools_used.join(', ')}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="loading">Thinking...</div>}
      </div>

      <div className="input-container">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask about ocean data..."
        />
        <button onClick={sendMessage} disabled={loading}>
          Send
        </button>
      </div>
    </div>
  );
}

export default App;
```

---

## Alternative: Streamlit (Fastest)

```python
# app.py
import streamlit as st
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate
from langchain.tools import tool
import os

st.set_page_config(page_title="FloatChat RAG", page_icon="🌊")

# Initialize components (same as above)
# ...

# Streamlit UI
st.title("🌊 FloatChat RAG")
st.caption("Explore oceanographic data with AI")

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about ocean data..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = agent_executor.invoke({"input": prompt})
            response = result["output"]
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
```

---

## Deployment Steps

### For Streamlit (Easiest)

1. **Create `requirements.txt`:**
```txt
streamlit
langchain
langchain-anthropic
chromadb
sentence-transformers
sqlalchemy
pandas
```

2. **Deploy to Streamlit Cloud:**
```bash
# Push to GitHub
git add .
git commit -m "Add Streamlit app"
git push

# Go to share.streamlit.io
# Connect your GitHub repo
# Set environment variable: ANTHROPIC_API_KEY
# Deploy!
```

### For FastAPI + React

1. **Backend (Railway/Render):**
```bash
# Create Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **Frontend (Vercel):**
```bash
# Build React app
npm run build

# Deploy to Vercel
vercel deploy
```

---

## Cost Estimates

### Free Tier (Recommended for Start)
- **Streamlit Cloud:** Free (1 app)
- **Railway:** $5/month (500 hours)
- **Vercel:** Free (hobby)
- **Anthropic API:** Pay-per-use (~$0.01/query)

### Paid (Production)
- **Railway:** $20/month
- **Vercel Pro:** $20/month
- **Database:** Supabase/PlanetScale ($10/month)
- **Total:** ~$50/month

---

## Features to Add

### Phase 1: MVP
- ✅ Chat interface
- ✅ Semantic search
- ✅ Database queries
- ✅ Basic auth (optional)

### Phase 2: Enhanced
- 📊 Data visualizations (Plotly)
- 🗺️ Interactive maps (Mapbox)
- 📈 Profile charts
- 💾 Export results (CSV/JSON)

### Phase 3: Advanced
- 👥 Multi-user support
- 📱 Mobile app
- 🔔 Real-time updates
- 🤖 Scheduled data fetching

---

## Security Considerations

1. **API Key Management:**
```python
# Use environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Never commit keys to git
# Add to .env and .gitignore
```

2. **Rate Limiting:**
```python
from slowapi import Limiter
limiter = Limiter(key_func=lambda: "global")

@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: ChatRequest):
    # ...
```

3. **Authentication:**
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/chat")
async def chat(request: ChatRequest, token: str = Depends(security)):
    # Verify token
    # ...
```

---

## Database Considerations

### For Production:
- **SQLite:** Good for demo, not for production
- **PostgreSQL:** Recommended (Supabase, Railway)
- **ChromaDB:** Consider hosted version (Chroma Cloud)

### Migration:
```python
# Update connection string
DB_URL = os.getenv("DATABASE_URL")  # PostgreSQL
CHROMA_URL = os.getenv("CHROMA_URL")  # Chroma Cloud
```

---

## Monitoring

### Add Logging:
```python
import logging
from loguru import logger

logger.add("app.log", rotation="500 MB")

@app.post("/chat")
async def chat(request: ChatRequest):
    logger.info(f"Query: {request.message}")
    # ...
```

### Add Analytics:
```python
from mixpanel import Mixpanel
mp = Mixpanel(os.getenv("MIXPANEL_TOKEN"))

mp.track(user_id, "chat_query", {
    "query": request.message,
    "tools_used": tools_used
})
```

---

## Next Steps

1. **Choose deployment option** (Streamlit recommended for MVP)
2. **Set up Anthropic API key**
3. **Create web interface** (use templates above)
4. **Deploy to cloud**
5. **Share with users**

---

## Example Queries for Demo

- "What ocean data do we have?"
- "Show me warm water profiles"
- "Get details for float 13857"
- "Profiles from the Atlantic Ocean"
- "Temperature measurements from 1998"

---

## Resources

- **Streamlit:** https://streamlit.io
- **FastAPI:** https://fastapi.tiangolo.com
- **LangChain:** https://python.langchain.com
- **Railway:** https://railway.app
- **Vercel:** https://vercel.com

**Ready to deploy? Start with Streamlit for fastest results!** 🚀
