#!/usr/bin/env python3
"""Test the fixed extraction locally"""

import sys
sys.path.insert(0, 'C:/Users/khayatimittal/Downloads/tax_deduction_finder-20260418T111013Z-3-001/tax_deduction_finder')

from backend.ocr.extractor import extract_transactions_from_pdf

# Read the sample PDF
with open("sample_bank_statement.pdf", "rb") as f:
    pdf_bytes = f.read()

print("Testing fixed extraction...")
print("=" * 60)

transactions, text, bank = extract_transactions_from_pdf(pdf_bytes)

print(f"\n[OK] Extracted {len(transactions)} transactions")
print(f"[OK] Text: {len(text)} chars")

if transactions:
    print(f"\nTransactions:")
    for i, tx in enumerate(transactions, 1):
        print(f"  {i}. {tx.date} | {tx.description[:40]} | Rs.{tx.debit_amount:,.2f}")
    
    print(f"\nTotal Deductions: Rs.{sum(tx.debit_amount for tx in transactions):,.2f}")
else:
    print("\n[FAIL] - No transactions!")
    print("Text preview:")
    print(text[:500])
