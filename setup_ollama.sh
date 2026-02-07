#!/bin/bash
# Setup script for Ollama + FloatChat RAG

echo "🌊 FloatChat RAG - Ollama Setup"
echo "================================"
echo ""

# Check if Ollama is installed
if command -v ollama &> /dev/null; then
    echo "✓ Ollama is installed"
    ollama --version
else
    echo "✗ Ollama not found"
    echo "Please install from: https://ollama.com/download"
    exit 1
fi

echo ""
echo "Checking if Ollama is running..."


# Check if Ollama service is running
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama service is running"
else
    echo "✗ Ollama service not running"
    echo ""
    echo "Starting Ollama in background..."
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 3
    
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✓ Ollama service started"
    else
        echo "✗ Failed to start Ollama"
        echo ""
        echo "Please start manually in a new terminal:"
        echo "  ollama serve"
        exit 1
    fi
fi

echo ""
echo "Checking for llama3.2:3b model..."

# Check if model is downloaded
if ollama list | grep -q "llama3.2:3b"; then
    echo "✓ Model llama3.2:3b is already downloaded"
else
    echo "✗ Model not found"
    echo ""
    echo "Downloading llama3.2:3b (~2GB, this may take a few minutes)..."
    ollama pull llama3.2:3b
    
    if [ $? -eq 0 ]; then
        echo "✓ Model downloaded successfully"
    else
        echo "✗ Failed to download model"
        exit 1
    fi
fi

echo ""
echo "================================"
echo "✅ Setup complete!"
echo ""
echo "To run the app:"
echo "  source .venv/bin/activate"
echo "  streamlit run app_ollama.py"
echo ""
echo "The app will open at: http://localhost:8501"
