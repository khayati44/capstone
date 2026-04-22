#!/usr/bin/env python3
"""Test the query endpoint"""

import requests

BASE_URL = "http://localhost:8000"

# Login first
login_data = {"email": "test@example.com", "password": "testpass123"}
resp = requests.post(f"{BASE_URL}/auth/login", json=login_data)
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Test query
print("Testing query endpoint...")
query_data = {"question": "How much did I spend on insurance?"}
resp = requests.post(f"{BASE_URL}/api/query", headers=headers, json=query_data)

print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")

if resp.status_code == 200:
    result = resp.json()
    print(f"\nQuestion: {result['question']}")
    print(f"SQL: {result['sql']}")
    print(f"Result: {result['result']}")
    print(f"Answer: {result['answer']}")
else:
    print(f"ERROR: {resp.text}")
