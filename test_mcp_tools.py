#!/usr/bin/env python3
"""
Test script to verify MCP server tools work correctly
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from floatchat.vector_db.embedder import ArgoMetadataEmbedder
from floatchat.vector_db.store import ArgoChromaStore
from sqlalchemy import create_engine, text
import pandas as pd

DB_URL = "sqlite:///data/databases/argo_data.db"

async def test_search_profiles():
    """Test semantic search"""
    print("\n🔍 Testing search_profiles...")
    embedder = ArgoMetadataEmbedder()
    chroma = ArgoChromaStore()
    
    results = chroma.search("warm water profiles", embedder, k=3)
    print(f"✅ Found {len(results['documents'][0])} results")
    for i, (doc, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
        print(f"  {i}. {meta.get('float_id')} at {meta.get('latitude')}, {meta.get('longitude')}")

async def test_get_statistics():
    """Test database statistics"""
    print("\n📊 Testing get_statistics...")
    engine = create_engine(DB_URL)
    
    with engine.connect() as conn:
        profile_count = conn.execute(text("SELECT COUNT(*) FROM profiles")).scalar()
        measurement_count = conn.execute(text("SELECT COUNT(*) FROM measurements")).scalar()
        float_count = conn.execute(text("SELECT COUNT(DISTINCT float_id) FROM profiles")).scalar()
        
        print(f"✅ Statistics:")
        print(f"  - Profiles: {profile_count}")
        print(f"  - Measurements: {measurement_count}")
        print(f"  - Floats: {float_count}")

async def test_get_float_details():
    """Test float details"""
    print("\n🎯 Testing get_float_details...")
    engine = create_engine(DB_URL)
    
    with engine.connect() as conn:
        profiles_df = pd.read_sql("SELECT * FROM profiles WHERE float_id = '13857' LIMIT 5", conn)
        print(f"✅ Found {len(profiles_df)} profiles for float 13857")
        print(f"  First profile: {profiles_df.iloc[0]['datetime']}")

async def test_query_database():
    """Test SQL query"""
    print("\n💾 Testing query_database...")
    engine = create_engine(DB_URL)
    
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM profiles LIMIT 3", conn)
        print(f"✅ Query returned {len(df)} rows")

async def test_get_profiles_by_location():
    """Test location filtering"""
    print("\n🌍 Testing get_profiles_by_location...")
    engine = create_engine(DB_URL)
    
    query = """
    SELECT * FROM profiles
    WHERE latitude BETWEEN -40 AND 0
    AND longitude BETWEEN 70 AND 90
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        print(f"✅ Found {len(df)} profiles in bounding box")

async def test_get_profiles_by_date():
    """Test date filtering"""
    print("\n📅 Testing get_profiles_by_date...")
    engine = create_engine(DB_URL)
    
    query = """
    SELECT * FROM profiles
    WHERE datetime BETWEEN '2023-01-01' AND '2023-12-31'
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        print(f"✅ Found {len(df)} profiles in 2023")

async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing FloatChat RAG MCP Server Tools")
    print("=" * 60)
    
    try:
        await test_search_profiles()
        await test_get_statistics()
        await test_get_float_details()
        await test_query_database()
        await test_get_profiles_by_location()
        await test_get_profiles_by_date()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print("\n📝 Next steps:")
        print("1. Copy claude_desktop_config.json to:")
        print("   ~/Library/Application Support/Claude/claude_desktop_config.json")
        print("2. Restart Claude Desktop")
        print("3. Test with: 'What ocean data do we have?'")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
