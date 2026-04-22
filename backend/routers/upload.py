"""
POST /api/upload — PDF upload, OCR extraction, PII redaction, DB storage.
"""

import os
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from fastapi import Request
from backend.config import get_settings
from backend.database import get_db
from backend.models import User, UploadRecord, Transaction
from backend.auth.dependencies import get_current_user
from backend.ocr.extractor import extract_transactions_from_pdf
from backend.pii.redactor import redact_pii
from backend.schemas import UploadResponse
from backend.guardrails.file_validator import validate_upload
from backend.guardrails.rate_limiter import check_upload_rate
from backend.guardrails.audit_logger import log_file_blocked, log_file_allowed, log_rate_limit_blocked

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()

MAX_SIZE_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a bank statement PDF, extract transactions via OCR, store in DB.
    """
    ip = request.client.host if request.client else "unknown"

    # ── Guardrail: Rate Limiting ──────────────────────────────────────────────
    rate_result = check_upload_rate(str(current_user.id))
    if not rate_result.allowed:
        log_rate_limit_blocked("/api/upload", current_user.id, ip, rate_result.retry_after_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Upload rate limit exceeded. Try again in {rate_result.retry_after_seconds}s.",
            headers={"Retry-After": str(rate_result.retry_after_seconds)},
        )

    pdf_bytes = await file.read()

    # ── Guardrail: File Validation ────────────────────────────────────────────
    val = validate_upload(
        filename=file.filename or "",
        content_type=file.content_type or "",
        file_bytes=pdf_bytes,
        max_size_bytes=MAX_SIZE_BYTES,
    )
    if not val.is_valid:
        log_file_blocked(file.filename or "", val.error_code or "UNKNOWN", current_user.id, ip)
        status_code = (
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if val.error_code == "FILE_TOO_LARGE"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=val.error_message)

    log_file_allowed(file.filename or "", len(pdf_bytes), current_user.id)

    # Save file to disk
    os.makedirs(settings.upload_dir, exist_ok=True)
    safe_filename = f"user{current_user.id}_{file.filename}"
    file_path = os.path.join(settings.upload_dir, safe_filename)
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    # Create upload record
    upload_record = UploadRecord(
        user_id=current_user.id,
        filename=file.filename,
        file_size=len(pdf_bytes),
        status="processing",
    )
    db.add(upload_record)
    db.commit()
    db.refresh(upload_record)

    try:
        # Run OCR pipeline
        transactions, full_text, bank_name = extract_transactions_from_pdf(pdf_bytes)

        # Redact PII from full text
        redacted_text = redact_pii(full_text)

        # Update upload record
        upload_record.bank_name = bank_name
        upload_record.raw_text = redacted_text
        upload_record.status = "completed"

        # Store transactions
        tx_count = 0
        for tx in transactions:
            clean_desc = redact_pii(tx.description or "")
            clean_raw = redact_pii(tx.raw_text or "")

            db_tx = Transaction(
                user_id=current_user.id,
                upload_id=upload_record.id,
                date=tx.date,
                description=clean_desc,
                debit_amount=tx.debit_amount,
                credit_amount=tx.credit_amount,
                balance=tx.balance,
                raw_text=clean_raw,
            )
            db.add(db_tx)
            tx_count += 1

        db.commit()
        db.refresh(upload_record)

        logger.info(f"Upload {upload_record.id}: {tx_count} transactions stored for user {current_user.id}")

        return UploadResponse(
            id=upload_record.id,
            filename=upload_record.filename,
            status=upload_record.status,
            bank_name=upload_record.bank_name,
            transaction_count=tx_count,
            created_at=upload_record.created_at,
        )

    except Exception as e:
        upload_record.status = "failed"
        db.commit()
        logger.error(f"OCR/processing error for upload {upload_record.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF processing failed: {str(e)}",
        )


@router.get("/uploads", response_model=list[UploadResponse])
def list_uploads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all uploads for the current user."""
    uploads = db.query(UploadRecord).filter(
        UploadRecord.user_id == current_user.id
    ).order_by(UploadRecord.created_at.desc()).all()

    results = []
    for u in uploads:
        tx_count = db.query(Transaction).filter(Transaction.upload_id == u.id).count()
        results.append(UploadResponse(
            id=u.id,
            filename=u.filename,
            status=u.status,
            bank_name=u.bank_name,
            transaction_count=tx_count,
            created_at=u.created_at,
        ))
    return results
