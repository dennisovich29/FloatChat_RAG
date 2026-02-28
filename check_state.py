#!/usr/bin/env python3
"""Check the current state of all project components"""
import sqlite3
import os

print("=" * 50)
print("FloatChat RAG - Current State Check")
print("=" * 50)

# 1. Check SQLite database
db_path = "data/databases/argo_data.db"
print(f"\n1. SQLite Database ({db_path}):")
if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    print(f"   Tables: {tables}")
    for t in tables:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"   {t}: {c.fetchone()[0]} rows")
    conn.close()
else:
    print("   NOT FOUND or EMPTY - needs pipeline run")

# 2. Check ChromaDB
chroma_path = "data/vector_db/chroma.sqlite3"
print(f"\n2. ChromaDB ({chroma_path}):")
if os.path.exists(chroma_path) and os.path.getsize(chroma_path) > 0:
    conn = sqlite3.connect(chroma_path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    print(f"   Tables: {tables}")
    for t in tables:
        try:
            c.execute(f"SELECT COUNT(*) FROM [{t}]")
            print(f"   {t}: {c.fetchone()[0]} rows")
        except:
            pass
    # Check collections
    try:
        c.execute("SELECT id, name FROM collections")
        colls = c.fetchall()
        print(f"   Collections: {colls}")
    except:
        pass
    # Check embeddings count
    try:
        c.execute("SELECT COUNT(*) FROM embeddings")
        print(f"   Total embeddings: {c.fetchone()[0]}")
    except:
        pass
    conn.close()
else:
    print("   NOT FOUND or EMPTY")

# 3. Check Parquet files
print("\n3. Parquet files:")
parquet_dir = "data/processed"
if os.path.exists(parquet_dir):
    files = [f for f in os.listdir(parquet_dir) if f.endswith('.parquet')]
    print(f"   Found {len(files)} parquet files")
    for f in files:
        size = os.path.getsize(os.path.join(parquet_dir, f))
        print(f"   {f}: {size} bytes")
else:
    print("   Directory not found")

# 4. Check .env
print("\n4. Environment:")
if os.path.exists(".env"):
    print("   .env file EXISTS")
else:
    print("   .env file NOT FOUND")
if os.path.exists(".env.example"):
    print("   .env.example EXISTS")

print("\n" + "=" * 50)
