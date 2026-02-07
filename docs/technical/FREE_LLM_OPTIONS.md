# Free LLM Alternatives for FloatChat RAG

## 🆓 100% Free Options

### Option 1: Ollama (Recommended - Completely Free!)

**Run LLMs locally on your Mac - NO API costs, NO internet needed!**

#### Setup (5 minutes):

```bash
# 1. Install Ollama
brew install ollama

# 2. Start Ollama service
ollama serve

# 3. Download a model (one-time, ~4GB)
ollama pull llama3.2:3b  # Fast, good quality
# or
ollama pull mistral      # Better quality, slower
```

#### Update app.py:

```python
# Replace this:
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", api_key=api_key)

# With this:
from langchain_ollama import ChatOllama
llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0,
    base_url="http://localhost:11434"
)
```

#### Install dependency:

```bash
source .venv/bin/activate
uv pip install langchain-ollama
```

**Pros:**
- ✅ 100% FREE
- ✅ No API key needed
- ✅ Works offline
- ✅ Privacy (data stays local)
- ✅ No rate limits

**Cons:**
- ❌ Slower than Claude
- ❌ Lower quality responses
- ❌ Requires ~4-8GB RAM

---

### Option 2: Groq (Free API - Very Fast!)

**Free API with generous limits - 30 requests/minute!**

#### Setup:

```bash
# 1. Get free API key from: https://console.groq.com
# 2. Add to .env:
GROQ_API_KEY=gsk_xxxxx

# 3. Install
uv pip install langchain-groq
```

#### Update app.py:

```python
from langchain_groq import ChatGroq

llm = ChatGroq(
    model="llama-3.3-70b-versatile",  # or mixtral-8x7b-32768
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)
```

**Pros:**
- ✅ 100% FREE (generous limits)
- ✅ Very fast (faster than Claude!)
- ✅ Good quality
- ✅ 30 requests/minute free

**Cons:**
- ❌ Requires internet
- ❌ Need API key (but free!)

---

### Option 3: Google Gemini (Free Tier)

**Free tier: 60 requests/minute!**

#### Setup:

```bash
# 1. Get free API key: https://makersuite.google.com/app/apikey
# 2. Add to .env:
GOOGLE_API_KEY=AIzaSy...

# 3. Install
uv pip install langchain-google-genai
```

#### Update app.py:

```python
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",  # Free tier
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0
)
```

**Pros:**
- ✅ FREE (60 req/min)
- ✅ Fast
- ✅ Good quality
- ✅ Multimodal (images)

**Cons:**
- ❌ Requires internet
- ❌ Need API key

---

### Option 4: Hugging Face (Free API)

**Free inference API for open models**

#### Setup:

```bash
# 1. Get free token: https://huggingface.co/settings/tokens
# 2. Add to .env:
HUGGINGFACEHUB_API_TOKEN=hf_...

# 3. Install
uv pip install langchain-huggingface
```

#### Update app.py:

```python
from langchain_huggingface import HuggingFaceEndpoint

llm = HuggingFaceEndpoint(
    repo_id="mistralai/Mistral-7B-Instruct-v0.2",
    huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
    temperature=0
)
```

---

## 📊 Comparison

| Option | Cost | Speed | Quality | Setup | Internet |
|--------|------|-------|---------|-------|----------|
| **Ollama** | FREE | Medium | Good | Easy | No |
| **Groq** | FREE | Very Fast | Good | Easy | Yes |
| **Gemini** | FREE | Fast | Very Good | Easy | Yes |
| **HuggingFace** | FREE | Slow | Medium | Medium | Yes |
| Claude | $5 free | Fast | Excellent | Easy | Yes |

---

## 🎯 Recommendation

### For Testing/Development:
**Use Ollama** - Completely free, works offline, no API key needed!

### For Production:
**Use Groq** - Free, fast, good quality, generous limits

### For Best Quality:
**Use Gemini Free Tier** - 60 req/min, excellent quality

---

## 🚀 Quick Start with Ollama (Easiest)

```bash
# 1. Install Ollama
brew install ollama

# 2. Start service (in new terminal)
ollama serve

# 3. Download model
ollama pull llama3.2:3b

# 4. Install LangChain integration
source .venv/bin/activate
uv pip install langchain-ollama

# 5. Create app_ollama.py (see below)

# 6. Run
streamlit run app_ollama.py
```

---

## 📝 Modified app.py for Ollama

I'll create a version that works with Ollama (no API key needed):

```python
# At the top of app.py, replace the LLM initialization:

# OLD (requires API key):
# from langchain_anthropic import ChatAnthropic
# llm = ChatAnthropic(...)

# NEW (free, no API key):
from langchain_ollama import ChatOllama

@st.cache_resource
def init_agent():
    """Initialize LangChain agent with tools"""
    
    tools = [
        search_profiles,
        get_statistics,
        get_float_details,
        query_database,
        get_profiles_by_location,
        get_profiles_by_date,
    ]
    
    # Use Ollama (FREE!)
    llm = ChatOllama(
        model="llama3.2:3b",
        temperature=0,
        base_url="http://localhost:11434"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an oceanography assistant..."""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    return agent_executor
```

---

## 💡 Summary

**You have 4 completely FREE options:**

1. **Ollama** - Best for offline/privacy (my recommendation!)
2. **Groq** - Best for speed
3. **Gemini** - Best for quality
4. **HuggingFace** - Most models

**No need to pay anything!** The $5 Anthropic credit is just a bonus if you want the best quality.

Want me to create a version of `app.py` that uses Ollama so you can run it completely free?
