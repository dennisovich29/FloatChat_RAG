#!/usr/bin/env python3
"""Quick script to check database contents"""
import sqlite3

db_path = "data/databases/argo_data.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    if not tables:
        print("❌ No tables found in database")
    else:
        print(f"✓ Found {len(tables)} table(s):")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  - {table_name}: {count} rows")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
