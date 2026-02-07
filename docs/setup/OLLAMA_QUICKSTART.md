# 🚀 Run FloatChat RAG with Ollama (100% FREE!)

## ✅ You Already Have Ollama Installed!

Just 3 simple steps to run:

### Step 1: Start Ollama Service

Open a **new terminal** and run:
```bash
ollama serve
```

Leave this terminal running.

### Step 2: Download Model (One-Time)

In **another terminal**, download the model (~2GB):
```bash
ollama pull llama3.2:3b
```

This takes 5-10 minutes depending on your internet.

### Step 3: Run the App

```bash
cd /Users/dennisprathyushpaul/Desktop/Projects/FloatChat_Rag/FloatChat_RAG
source .venv/bin/activate
streamlit run app_ollama.py
```

**Done!** App opens at http://localhost:8501

---

## 🎯 Quick Test

Once the app is running, try:
- "What ocean data do we have?"
- "Show me warm water profiles"

---

## 💡 Tips

**Model already downloaded?** Check with:
```bash
ollama list
```

**Ollama not responding?** Restart:
```bash
# Kill existing
pkill ollama

# Start fresh
ollama serve
```

**Want a better model?**
```bash
ollama pull mistral  # Better quality, slower
```

Then edit `app_ollama.py` line 236:
```python
model="mistral"  # instead of llama3.2:3b
```

---

## 🆓 100% Free Forever!

- No API keys
- No internet needed (after download)
- No rate limits
- Runs on your Mac

**Enjoy!** 🌊
