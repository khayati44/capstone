"""
GET /api/deductions — Fetch deduction results for current user.
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Transaction, DeductionReport as DeductionReportModel
from backend.auth.dependencies import get_current_user
from backend.schemas import TransactionResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/deductions")
def get_deductions(
    upload_id: int = Query(..., description="Upload ID to fetch deductions for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch the deduction report for a specific upload."""
    report = db.query(DeductionReportModel).filter(
        DeductionReportModel.upload_id == upload_id,
        DeductionReportModel.user_id == current_user.id,
    ).order_by(DeductionReportModel.created_at.desc()).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deduction report found for this upload. Please run analysis first.",
        )

    report_data = json.loads(report.report_json) if report.report_json else {}
    return {
        "id": report.id,
        "upload_id": report.upload_id,
        "total_deductions": report.total_deductions,
        "estimated_tax_saved_20": report.estimated_tax_saved_20,
        "estimated_tax_saved_30": report.estimated_tax_saved_30,
        "sections_covered": report.sections_covered.split(",") if report.sections_covered else [],
        "created_at": report.created_at.isoformat(),
        "report": report_data,
    }


@router.get("/deductions/transactions", response_model=list[TransactionResponse])
def get_deduction_transactions(
    upload_id: int = Query(..., description="Upload ID"),
    tax_relevant_only: bool = Query(False, description="Filter only tax-relevant transactions"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch transactions with deduction info for a specific upload."""
    query = db.query(Transaction).filter(
        Transaction.upload_id == upload_id,
        Transaction.user_id == current_user.id,
    )
    if tax_relevant_only:
        query = query.filter(Transaction.is_tax_relevant == True)

    transactions = query.order_by(Transaction.date).all()
    return transactions


@router.get("/deductions/summary")
def get_deductions_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get overall deduction summary across all uploads."""
    reports = db.query(DeductionReportModel).filter(
        DeductionReportModel.user_id == current_user.id
    ).all()

    return {
        "total_uploads_analyzed": len(reports),
        "total_deductions_all": sum(r.total_deductions for r in reports),
        "total_tax_saved_20": sum(r.estimated_tax_saved_20 for r in reports),
        "total_tax_saved_30": sum(r.estimated_tax_saved_30 for r in reports),
        "reports": [
            {
                "id": r.id,
                "upload_id": r.upload_id,
                "total_deductions": r.total_deductions,
                "sections_covered": r.sections_covered,
                "created_at": r.created_at.isoformat(),
            }
            for r in reports
        ],
    }
