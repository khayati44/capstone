#!/usr/bin/env python3
"""
COMPLETE END-TO-END TEST
Tests: Upload → Extraction → Categorization → Tax Matching → Deduction Calculation
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

print("=" * 70)
print("COMPREHENSIVE PROJECT TEST - Tax Deduction Finder")
print("=" * 70)

# Step 1: Register/Login
print("\n[STEP 1] Authentication...")
try:
    # Register
    register_data = {
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User"
    }
    resp = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if resp.status_code == 400 and "already registered" in resp.text.lower():
        print("  [OK] User already exists, logging in...")
    elif resp.status_code == 201:
        print("  [OK] User registered successfully")
    
    # Login
    login_data = {
        "email": "test@example.com",
        "password": "testpass123"
    }
    resp = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    resp.raise_for_status()
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  [OK] Logged in successfully")
except Exception as e:
    print(f"  [FAIL] Authentication failed: {e}")
    exit(1)

# Step 2: Upload PDF
print("\n[STEP 2] Uploading PDF...")
try:
    with open("sample_bank_statement.pdf", "rb") as f:
        files = {"file": ("sample_bank_statement.pdf", f, "application/pdf")}
        resp = requests.post(f"{BASE_URL}/api/upload", headers=headers, files=files)
        resp.raise_for_status()
        upload_data = resp.json()
        upload_id = upload_data["id"]
        tx_count = upload_data["transaction_count"]
        print(f"  [OK] Upload ID: {upload_id}")
        print(f"  [OK] Transactions extracted: {tx_count}")
        
        if tx_count == 0:
            print(f"  [FAIL] NO TRANSACTIONS EXTRACTED!")
            print(f"  Response: {json.dumps(upload_data, indent=2)}")
            exit(1)
except Exception as e:
    print(f"  [FAIL] Upload failed: {e}")
    exit(1)

# Step 3: Get transactions
print("\n[STEP 3] Fetching transactions...")
try:
    resp = requests.get(f"{BASE_URL}/api/uploads", headers=headers)
    resp.raise_for_status()
    uploads = resp.json()
    print(f"  [OK] Total uploads: {len(uploads)}")
    
    latest = uploads[0]
    print(f"  [OK] Latest upload: {latest['filename']}")
    print(f"  [OK] Status: {latest['status']}")
    print(f"  [OK] Bank: {latest['bank_name']}")
    print(f"  [OK] Transaction count: {latest['transaction_count']}")
except Exception as e:
    print(f"  [FAIL] Failed to fetch transactions: {e}")
    exit(1)

# Step 4: Run COMPLETE analysis (categorization + tax matching + deduction calc)
print("\n[STEP 4] Running complete AI analysis pipeline...")
try:
    analyze_data = {"upload_id": upload_id}
    resp = requests.post(f"{BASE_URL}/api/analyze", headers=headers, json=analyze_data)
    resp.raise_for_status()
    analysis_result = resp.json()
    
    # Extract report data
    report = analysis_result.get('report', {})
    
    print(f"  [OK] Upload ID: {analysis_result.get('upload_id')}")
    print(f"  [OK] Tax-relevant transactions: {analysis_result.get('tax_relevant_count')}")
    print(f"  [OK] Matched transactions: {analysis_result.get('matched_count')}")
    print(f"  [OK] Total gross deductions: Rs.{report.get('total_gross_deductions', 0):,.2f}")
    print(f"  [OK] Total capped deductions: Rs.{report.get('total_capped_deductions', 0):,.2f}")
    print(f"  [OK] Tax saved @ 20%: Rs.{report.get('estimated_tax_saved_20_percent', 0):,.2f}")
    print(f"  [OK] Tax saved @ 30%: Rs.{report.get('estimated_tax_saved_30_percent', 0):,.2f}")
    
    if report.get('total_capped_deductions', 0) == 0:
        print(f"  [FAIL] ZERO TAX DEDUCTIONS CALCULATED!")
        print(f"  Response: {json.dumps(analysis_result, indent=2)}")
        exit(1)
    
    # Show section breakdown
    print(f"\n  Section-wise breakdown:")
    for section_data in report.get('section_summaries', []):
        section = section_data['section']
        gross = section_data['total_deductible']
        capped = section_data['capped_deductible']
        count = section_data['transaction_count']
        print(f"    - Section {section}: Rs.{gross:,.2f} → Rs.{capped:,.2f} ({count} txns)")
        
except Exception as e:
    print(f"  [FAIL] Analysis failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Final Summary
print("\n" + "=" * 70)
print("TEST RESULTS SUMMARY")
print("=" * 70)
print(f"[OK] Upload completed: {tx_count} transactions extracted")
print(f"[OK] Analysis completed: {analysis_result.get('tax_relevant_count')} tax-relevant")
print(f"[OK] Deductions calculated: Rs.{report.get('total_capped_deductions', 0):,.2f}")
print(f"[OK] Tax savings @ 30%: Rs.{report.get('estimated_tax_saved_30_percent', 0):,.2f}")
print("\n✅ ALL TESTS PASSED - PROJECT IS FULLY FUNCTIONAL!")
print("=" * 70)
