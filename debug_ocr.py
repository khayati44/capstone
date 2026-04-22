"""
Quick test to see what text is extracted from the PDF
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.ocr.extractor import extract_transactions_from_pdf

with open('sample_bank_statement.pdf', 'rb') as f:
    pdf_bytes = f.read()

transactions, full_text, bank_name = extract_transactions_from_pdf(pdf_bytes)

print("EXTRACTED TEXT:")
print("=" * 60)
print(full_text)
print("=" * 60)
print(f"\nTransactions found: {len(transactions)}")

if transactions:
    print("\nTransactions:")
    for tx in transactions:
        print(f"  {tx.date} | {tx.description} | {tx.debit_amount}")
