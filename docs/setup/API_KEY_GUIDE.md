# How to Get Your Anthropic API Key

## 🔑 Step-by-Step Guide

### 1. Go to Anthropic Console
Visit: **https://console.anthropic.com/**

### 2. Sign Up / Log In
- If you don't have an account, click **"Sign Up"**
- Use your email or Google account
- Verify your email if needed

### 3. Navigate to API Keys
- Once logged in, click on **"API Keys"** in the left sidebar
- Or go directly to: https://console.anthropic.com/settings/keys

### 4. Create a New API Key
- Click **"Create Key"** button
- Give it a name (e.g., "FloatChat RAG")
- Click **"Create Key"**

### 5. Copy Your Key
- **IMPORTANT:** Copy the key immediately!
- It starts with `sk-ant-`
- You won't be able to see it again after closing the dialog

### 6. Add to Your Project
Create a `.env` file in your project:

```bash
cd /Users/dennisprathyushpaul/Desktop/Projects/FloatChat_Rag/FloatChat_RAG
cp .env.example .env
```

Edit `.env` and paste your key:
```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 💰 Pricing

### Free Tier
- **$5 free credits** when you sign up
- Good for ~1,000 queries with Claude 3.5 Sonnet
- Perfect for testing!

### Paid Pricing (Claude 3.5 Sonnet)
- **Input:** $3 per million tokens (~$0.003 per 1K tokens)
- **Output:** $15 per million tokens (~$0.015 per 1K tokens)
- **Average query:** ~$0.01-0.05

### Cost Estimates for FloatChat
- **100 queries:** ~$2-5
- **1,000 queries:** ~$20-50
- **10,000 queries:** ~$200-500

---

## 🔒 Security Best Practices

### ✅ DO:
- Store key in `.env` file (already in `.gitignore`)
- Never commit `.env` to git
- Use environment variables in production
- Rotate keys periodically

### ❌ DON'T:
- Hard-code keys in source code
- Share keys publicly
- Commit keys to GitHub
- Use the same key for multiple projects

---

## 🚀 Quick Setup

```bash
# 1. Copy example
cp .env.example .env

# 2. Edit .env and add your key
# ANTHROPIC_API_KEY=sk-ant-xxxxx

# 3. Test it works
source .venv/bin/activate
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
key = os.getenv('ANTHROPIC_API_KEY')
if key and key.startswith('sk-ant-'):
    print('✓ API key loaded successfully!')
else:
    print('✗ API key not found or invalid')
"

# 4. Run Streamlit app
streamlit run app.py
```

---

## 🔧 Troubleshooting

### "API key not found"
```bash
# Check .env file exists
ls -la .env

# Check key is set
cat .env | grep ANTHROPIC_API_KEY
```

### "Invalid API key"
- Make sure key starts with `sk-ant-`
- No extra spaces or quotes
- Key is active in console

### "Rate limit exceeded"
- You've used your free credits
- Add payment method in console
- Or wait for rate limit to reset

---

## 🌐 For Streamlit Cloud Deployment

When deploying to Streamlit Cloud:

1. Go to your app settings
2. Click **"Secrets"**
3. Add:
```toml
ANTHROPIC_API_KEY = "sk-ant-xxxxx"
```

---

## 📊 Monitor Usage

Check your usage at:
**https://console.anthropic.com/settings/usage**

- See total tokens used
- Track costs
- Set spending limits

---

## Alternative: Use OpenAI Instead

If you prefer OpenAI (GPT-4):

1. Get key from: https://platform.openai.com/api-keys
2. Install: `uv pip install langchain-openai`
3. Edit `app.py`:
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4-turbo-preview",
    api_key=os.getenv("OPENAI_API_KEY")
)
```

---

## 🎯 Summary

1. **Get key:** https://console.anthropic.com/settings/keys
2. **Create `.env`:** `cp .env.example .env`
3. **Add key:** `ANTHROPIC_API_KEY=sk-ant-xxxxx`
4. **Run app:** `streamlit run app.py`

**You get $5 free credits to start!** 🎉
