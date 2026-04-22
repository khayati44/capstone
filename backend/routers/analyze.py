"""
POST /api/analyze — Run 3-agent pipeline on uploaded transactions.
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UploadRecord, Transaction, DeductionReport as DeductionReportModel
from backend.auth.dependencies import get_current_user
from backend.agents.orchestrator import run_pipeline
from backend.schemas import AnalyzeRequest, DeductionReportSchema
from backend.guardrails.rate_limiter import check_analysis_rate
from backend.guardrails.audit_logger import log_rate_limit_blocked

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze")
def analyze_upload(
    request: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run 3-agent AI analysis pipeline on an uploaded bank statement.
    Returns DeductionReport with all identified deductions.
    """
    # ── Guardrail: Rate Limiting ──────────────────────────────────────────────
    rate_result = check_analysis_rate(str(current_user.id))
    if not rate_result.allowed:
        log_rate_limit_blocked("/api/analyze", current_user.id, None, rate_result.retry_after_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Analysis rate limit exceeded. Try again in {rate_result.retry_after_seconds}s.",
            headers={"Retry-After": str(rate_result.retry_after_seconds)},
        )
    upload = db.query(UploadRecord).filter(
        UploadRecord.id == request.upload_id,
        UploadRecord.user_id == current_user.id,
    ).first()

    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found or access denied",
        )

    if upload.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload processing failed — please re-upload the file",
        )

    # Fetch transactions for this upload
    transactions = db.query(Transaction).filter(
        Transaction.upload_id == request.upload_id,
        Transaction.user_id == current_user.id,
    ).all()

    if not transactions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No transactions found for this upload. OCR may have failed.",
        )

    # Convert ORM objects to dicts for the pipeline
    tx_dicts = []
    for tx in transactions:
        tx_dicts.append({
            "id": tx.id,
            "date": tx.date,
            "description": tx.description,
            "debit_amount": tx.debit_amount,
            "credit_amount": tx.credit_amount,
            "balance": tx.balance,
            "raw_text": tx.raw_text,
        })

    # Run pipeline
    logger.info(f"Running pipeline for upload_id={request.upload_id}, user_id={current_user.id}")
    try:
        result = run_pipeline(tx_dicts, upload_id=request.upload_id)
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis pipeline failed: {str(e)}",
        )

    if result["status"] != "success":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "Pipeline failed"),
        )

    # Update transactions in DB with categorization + matching results
    tx_id_map = {tx.id: tx for tx in transactions}
    for cat_tx in result["categorized_transactions"]:
        tx_id = cat_tx.get("id")
        if tx_id and tx_id in tx_id_map:
            db_tx = tx_id_map[tx_id]
            db_tx.merchant_type = cat_tx.get("merchant_type")
            db_tx.likely_purpose = cat_tx.get("likely_purpose")
            db_tx.is_tax_relevant = bool(cat_tx.get("is_tax_relevant", False))
            db_tx.matched_section = cat_tx.get("matched_section")
            db_tx.deduction_percentage = cat_tx.get("deduction_percentage")
            db_tx.conditions = cat_tx.get("conditions")

            # Find deductible amount from line items
            report_data = result["report"]
            for li in report_data.get("line_items", []):
                if li["transaction_id"] == tx_id:
                    db_tx.deductible_amount = li["deductible_amount"]
                    break

    # Save deduction report
    report_data = result["report"]
    existing_report = db.query(DeductionReportModel).filter(
        DeductionReportModel.upload_id == request.upload_id,
        DeductionReportModel.user_id == current_user.id,
    ).first()

    if existing_report:
        existing_report.total_deductions = report_data["total_capped_deductions"]
        existing_report.estimated_tax_saved_20 = report_data["estimated_tax_saved_20_percent"]
        existing_report.estimated_tax_saved_30 = report_data["estimated_tax_saved_30_percent"]
        existing_report.sections_covered = ",".join(report_data["sections_covered"])
        existing_report.report_json = json.dumps(report_data)
    else:
        db_report = DeductionReportModel(
            user_id=current_user.id,
            upload_id=request.upload_id,
            total_deductions=report_data["total_capped_deductions"],
            estimated_tax_saved_20=report_data["estimated_tax_saved_20_percent"],
            estimated_tax_saved_30=report_data["estimated_tax_saved_30_percent"],
            sections_covered=",".join(report_data["sections_covered"]),
            report_json=json.dumps(report_data),
        )
        db.add(db_report)

    db.commit()

    return {
        "status": "success",
        "upload_id": request.upload_id,
        "transaction_count": result["transaction_count"],
        "tax_relevant_count": result["tax_relevant_count"],
        "matched_count": result["matched_count"],
        "report": result["report"],
    }
