#!/usr/bin/env python3
"""
Test script for Streamlit app components (without requiring API key)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing Streamlit App Components...")
print("=" * 50)

# Test 1: Import dependencies
print("\n1. Testing imports...")
try:
    import streamlit as st
    from langchain.tools import tool
    from langchain_anthropic import ChatAnthropic
    print("   ✓ All imports successful")
except ImportError as e:
    print(f"   ✗ Import error: {e}")
    sys.exit(1)

# Test 2: Database connection
print("\n2. Testing database connection...")
try:
    from sqlalchemy import create_engine, text
    db_engine = create_engine("sqlite:///data/databases/argo_data.db")
    
    with db_engine.connect() as conn:
        profile_count = conn.execute(text("SELECT COUNT(*) FROM profiles")).scalar()
        print(f"   ✓ Database connected: {profile_count} profiles")
except Exception as e:
    print(f"   ✗ Database error: {e}")
    sys.exit(1)

# Test 3: ChromaDB
print("\n3. Testing ChromaDB...")
try:
    import os
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    
    from floatchat.vector_db.store import ArgoChromaStore
    from floatchat.vector_db.embedder import ArgoMetadataEmbedder
    
    chroma_store = ArgoChromaStore()
    embedder = ArgoMetadataEmbedder()
    
    # Test search
    results = chroma_store.search("warm water", embedder, k=1)
    result_count = len(results["documents"][0])
    print(f"   ✓ ChromaDB working: {result_count} results")
except Exception as e:
    print(f"   ✗ ChromaDB error: {e}")
    sys.exit(1)

# Test 4: Tool definitions
print("\n4. Testing tool definitions...")
try:
    @tool
    def test_search_profiles(query: str, limit: int = 5) -> str:
        """Test search tool"""
        return "test"
    
    print(f"   ✓ Tool decorator working")
    print(f"   ✓ Tool name: {test_search_profiles.name}")
    print(f"   ✓ Tool description: {test_search_profiles.description}")
except Exception as e:
    print(f"   ✗ Tool error: {e}")
    sys.exit(1)

# Test 5: Check app.py exists and is valid Python
print("\n5. Testing app.py...")
try:
    app_path = Path("app.py")
    if not app_path.exists():
        raise FileNotFoundError("app.py not found")
    
    # Try to compile it (syntax check)
    with open(app_path) as f:
        compile(f.read(), "app.py", "exec")
    
    print(f"   ✓ app.py exists and is valid Python")
except Exception as e:
    print(f"   ✗ app.py error: {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("✅ All component tests passed!")
print("\nTo run the app:")
print("1. Create .env file with ANTHROPIC_API_KEY")
print("2. Run: streamlit run app.py")
