#!/usr/bin/env python3
"""Test PDF extraction in Docker container"""

from backend.ocr.extractor import extract_transactions_from_pdf
import sys

pdf_path = "/app/uploads/user1_sample_bank_statement.pdf"
print(f"Testing extraction from: {pdf_path}")
print("=" * 60)

try:
    transactions = extract_transactions_from_pdf(pdf_path)
    print(f"\n✓ Extracted {len(transactions)} transactions")
    
    if transactions:
        print("\nFirst 3 transactions:")
        for i, tx in enumerate(transactions[:3], 1):
            print(f"  {i}. {tx.get('date')} | {tx.get('description')} | ₹{tx.get('debit_amount', 0)}")
    else:
        print("\n✗ NO TRANSACTIONS EXTRACTED!")
        print("This means the parser is not working correctly.")
        
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
