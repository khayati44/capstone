"""
DEBUG endpoint to inspect raw transactions and categorization results
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Transaction
from backend.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/debug/transactions")
def debug_transactions(
    upload_id: int = Query(..., description="Upload ID to debug"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Debug endpoint: See raw transaction data and categorization results.
    """
    transactions = db.query(Transaction).filter(
        Transaction.upload_id == upload_id,
        Transaction.user_id == current_user.id,
    ).all()

    if not transactions:
        return {"error": "No transactions found", "upload_id": upload_id}

    result = {
        "upload_id": upload_id,
        "total_transactions": len(transactions),
        "tax_relevant_count": sum(1 for t in transactions if t.is_tax_relevant),
        "matched_count": sum(1 for t in transactions if t.matched_section and t.matched_section != "NONE"),
        "transactions": []
    }

    for tx in transactions[:10]:  # Show first 10
        result["transactions"].append({
            "id": tx.id,
            "date": tx.date,
            "description": tx.description[:100] if tx.description else None,
            "debit_amount": float(tx.debit_amount) if tx.debit_amount else 0,
            "credit_amount": float(tx.credit_amount) if tx.credit_amount else 0,
            "merchant_type": tx.merchant_type,
            "likely_purpose": tx.likely_purpose,
            "is_tax_relevant": tx.is_tax_relevant,
            "matched_section": tx.matched_section,
            "deduction_percentage": float(tx.deduction_percentage) if tx.deduction_percentage else 0,
            "deductible_amount": float(tx.deductible_amount) if tx.deductible_amount else 0,
        })

    return result
