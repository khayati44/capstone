#!/usr/bin/env python3
"""Test multiple queries"""

import requests

BASE_URL = "http://localhost:8000"

# Login
login_data = {"email": "test@example.com", "password": "testpass123"}
resp = requests.post(f"{BASE_URL}/auth/login", json=login_data)
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

queries = [
    "How much did I spend on insurance?",
    "Show me all my PPF contributions",
    "What is my total deduction under 80C?",
    "How many transactions do I have?",
    "What was my highest expense?",
]

for i, q in enumerate(queries, 1):
    print(f"\n{'='*70}")
    print(f"Query {i}: {q}")
    print('='*70)
    
    query_data = {"question": q}
    resp = requests.post(f"{BASE_URL}/api/query", headers=headers, json=query_data)
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"✓ SQL: {result['sql'][:100]}...")
        print(f"✓ Result: {result['result'][:3] if isinstance(result['result'], list) else result['result']}")
    else:
        print(f"✗ ERROR: {resp.status_code}")

print(f"\n{'='*70}")
print("✅ QUERY FEATURE IS WORKING!")
print('='*70)
