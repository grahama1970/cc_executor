#!/usr/bin/env python3
"""Simple test to check if python-arango is working."""

import os
from arango import ArangoClient
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    """Test basic ArangoDB connection."""
    try:
        # Connect to ArangoDB
        client = ArangoClient(hosts=os.getenv("ARANGO_URL", "http://localhost:8529"))
        
        # System database connection
        sys_db = client.db(
            "_system",
            username=os.getenv("ARANGO_USERNAME", "root"),
            password=os.getenv("ARANGO_PASSWORD", "openSesame")
        )
        
        # Test connection
        version = sys_db.version()
        print(f"✅ Connected to ArangoDB version: {version}")
        
        # List databases
        databases = sys_db.databases()
        print(f"✅ Available databases: {databases}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)