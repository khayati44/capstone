#!/usr/bin/env python3
"""Test PDF extraction with uploaded file"""

from backend.ocr.extractor import extract_transactions_from_pdf

# Read the uploaded PDF
with open("/app/uploads/user1_sample_bank_statement.pdf", "rb") as f:
    pdf_bytes = f.read()

print(f"PDF file size: {len(pdf_bytes)} bytes")
print("=" * 60)

# Extract transactions
transactions, extracted_text, bank_name = extract_transactions_from_pdf(pdf_bytes)

print(f"\n✓ Extracted {len(transactions)} transactions")
print(f"✓ Bank: {bank_name}")
print(f"✓ Text extracted: {len(extracted_text)} chars")

if transactions:
    print(f"\nFirst 5 transactions:")
    for i, tx in enumerate(transactions[:5], 1):
        print(f"  {i}. {tx.date} | {tx.description[:50] if tx.description else 'N/A'} | Debit: ₹{tx.debit_amount}")
else:
    print("\n✗ NO TRANSACTIONS FOUND!")
    print("\nDebugging info:")
    print(f"Extracted text preview (first 500 chars):")
    print(extracted_text[:500])
