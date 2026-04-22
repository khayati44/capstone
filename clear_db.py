#!/usr/bin/env python3
"""Clear all uploads and transactions from database"""

from backend.database import SessionLocal
from backend.models import UploadRecord, Transaction

db = SessionLocal()

# Delete all transactions first (foreign key constraint)
tx_count = db.query(Transaction).delete()
print(f"Deleted {tx_count} transactions")

# Delete all upload records
upload_count = db.query(UploadRecord).delete()
print(f"Deleted {upload_count} upload records")

db.commit()
db.close()

print("\n✓ Database cleared! Ready for fresh uploads.")
