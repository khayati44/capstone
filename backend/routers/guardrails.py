"""
GET  /api/guardrails/status  — live config & stats for all 5 guardrails
POST /api/guardrails/test/file   — demo: test file validation
POST /api/guardrails/test/query  — demo: test query safety
POST /api/guardrails/test/rate   — demo: simulate rate limit
GET  /api/guardrails/audit       — last N security audit events
"""

import io
import logging
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from backend.auth.dependencies import get_current_user
from backend.models import User
from backend.guardrails.file_validator import validate_upload
from backend.guardrails.query_safety import check_query_safety
from backend.guardrails.rate_limiter import (
    check_upload_rate, check_query_rate, check_analysis_rate, check_login_rate,
    _limiter,
)
from backend.guardrails.llm_output_validator import (
    validate_tax_rule_output, validate_categorizer_output,
    VALID_TAX_SECTIONS,
)
from backend.guardrails.audit_logger import (
    audit_log,
    log_file_blocked, log_file_allowed,
    log_query_blocked, log_query_allowed,
)

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_DEMO_SIZE = 10 * 1024 * 1024  # 10 MB


# ── /api/guardrails/status ────────────────────────────────────────────────────

@router.get("/guardrails/status")
def guardrails_status(current_user: User = Depends(get_current_user)):
    """Return live configuration and cumulative stats for every guardrail."""
    return {
        "guardrails": [
            {
                "id": "file_validator",
                "name": "File Validator",
                "description": "Blocks malicious uploads: checks magic bytes, extension whitelist, size limit, executable signatures, path traversal",
                "status": "active",
                "checks": [
                    "Extension whitelist (.pdf only)",
                    "PDF magic bytes (%PDF)",
                    "Max file size (10 MB)",
                    "Executable signature detection (MZ, ELF, ZIP, HTML)",
                    "Filename path-traversal & shell injection",
                    "Empty / corrupted file",
                ],
            },
            {
                "id": "rate_limiter",
                "name": "Rate Limiter",
                "description": "Sliding-window rate limiter per user / IP to prevent brute-force & abuse",
                "status": "active",
                "limits": {
                    "login": "5 attempts / 60 s (per IP)",
                    "upload": "10 uploads / 3600 s (per user)",
                    "analyze": "5 analyses / 3600 s (per user)",
                    "query": "20 queries / 3600 s (per user)",
                },
            },
            {
                "id": "query_safety",
                "name": "Query Safety",
                "description": "Blocks SQL injection, prompt injection, and data-exfiltration attempts in NL queries",
                "status": "active",
                "checks": [
                    "SQL injection patterns (DROP, UNION, EXEC …)",
                    "Prompt injection (ignore instructions, DAN mode …)",
                    "Data exfiltration (hashed_password, SELECT * FROM users …)",
                    "Query length bounds (3–500 chars)",
                    "Off-domain query warning",
                ],
            },
            {
                "id": "llm_output_validator",
                "name": "LLM Output Validator",
                "description": "Validates Groq LLM responses before they reach the database or UI",
                "status": "active",
                "checks": [
                    f"Tax section whitelist ({len(VALID_TAX_SECTIONS)} valid sections)",
                    "Deduction % bounds [0–100]",
                    "Amount sanity (no negatives, ≤ ₹10 Cr)",
                    "XSS / script injection in LLM text",
                    "is_tax_relevant boolean coercion",
                ],
            },
            {
                "id": "audit_logger",
                "name": "Audit Logger",
                "description": "Structured event log for every guardrail decision — supports compliance review",
                "status": "active",
                "buffer_size": MAX_DEMO_SIZE,
                "stats": audit_log.get_stats(),
            },
        ],
        "audit_stats": audit_log.get_stats(),
    }


# ── /api/guardrails/test/file ─────────────────────────────────────────────────

@router.post("/guardrails/test/file")
async def test_file_guardrail(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload any file and see the file-validator guardrail decision in real-time."""
    file_bytes = await file.read()
    result = validate_upload(
        filename=file.filename or "",
        content_type=file.content_type or "",
        file_bytes=file_bytes,
        max_size_bytes=MAX_DEMO_SIZE,
    )

    if result.is_valid:
        log_file_allowed(file.filename or "", len(file_bytes), current_user.id)
    else:
        log_file_blocked(file.filename or "", result.error_code or "UNKNOWN", current_user.id)

    return {
        "filename": file.filename,
        "size_bytes": len(file_bytes),
        "content_type": file.content_type,
        "guardrail": "file_validator",
        "is_valid": result.is_valid,
        "error_code": result.error_code,
        "error_message": result.error_message,
        "details": result.details,
        "verdict": "✅ ALLOWED" if result.is_valid else f"🚫 BLOCKED — {result.error_code}",
    }


# ── /api/guardrails/test/query ────────────────────────────────────────────────

class QueryTestRequest(BaseModel):
    query: str


@router.post("/guardrails/test/query")
def test_query_guardrail(
    body: QueryTestRequest,
    current_user: User = Depends(get_current_user),
):
    """Submit any text and see the query-safety guardrail decision in real-time."""
    result = check_query_safety(body.query)

    if result.is_safe:
        log_query_allowed(body.query, current_user.id)
    else:
        log_query_blocked(body.query, result.blocked_code or "UNSAFE", result.risk_level, current_user.id)

    return {
        "original_query": body.query,
        "guardrail": "query_safety",
        "is_safe": result.is_safe,
        "risk_level": result.risk_level,
        "blocked_reason": result.blocked_reason,
        "blocked_code": result.blocked_code,
        "sanitized_query": result.sanitized_query,
        "verdict": "✅ ALLOWED" if result.is_safe else f"🚫 BLOCKED — {result.blocked_code}",
    }


# ── /api/guardrails/test/llm ──────────────────────────────────────────────────

class LLMOutputTestRequest(BaseModel):
    matched_section: str = "80C"
    deduction_percentage: float = 100.0
    conditions: str = "Test condition"
    confidence: str = "HIGH"


@router.post("/guardrails/test/llm")
def test_llm_output_guardrail(
    body: LLMOutputTestRequest,
    current_user: User = Depends(get_current_user),
):
    """Submit a simulated LLM tax-rule output and see validation result."""
    data = body.dict()
    result = validate_tax_rule_output(data)
    return {
        "input": data,
        "guardrail": "llm_output_validator",
        "is_valid": result.is_valid,
        "warnings": result.warnings,
        "sanitized_data": result.sanitized_data,
        "verdict": "✅ VALID" if result.is_valid else f"⚠️ SANITIZED — {'; '.join(result.warnings)}",
    }


# ── /api/guardrails/test/rate ─────────────────────────────────────────────────

@router.get("/guardrails/test/rate")
def test_rate_limiter(current_user: User = Depends(get_current_user)):
    """Check current rate-limit status for the authenticated user (non-destructive)."""
    uid = str(current_user.id)
    upload = check_upload_rate(uid)
    analyze = check_analysis_rate(uid)
    query = check_query_rate(uid)
    return {
        "guardrail": "rate_limiter",
        "user_id": current_user.id,
        "limits": {
            "upload":  {"allowed": upload.allowed,  "remaining": upload.remaining,  "limit": upload.limit},
            "analyze": {"allowed": analyze.allowed, "remaining": analyze.remaining, "limit": analyze.limit},
            "query":   {"allowed": query.allowed,   "remaining": query.remaining,   "limit": query.limit},
        },
    }


@router.post("/guardrails/reset/analyze/{user_id}")
def reset_analyze_rate_limiter(user_id: int, current_user: User = Depends(get_current_user)):
    """Reset the in-memory analyze rate limiter for a user.

    Dev helper: only allows a user to reset their own counter.
    """
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only reset your own rate limits")

    # key format used by rate_limiter: analyze:user:<id>
    try:
        _limiter.reset(f"analyze:user:{user_id}")
    except Exception as e:
        logger.error(f"Failed to reset rate limiter for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reset rate limiter")

    return {"status": "ok", "message": "analyze rate limiter reset for user", "user_id": user_id}


# ── /api/guardrails/audit ─────────────────────────────────────────────────────

@router.get("/guardrails/audit")
def get_audit_log(
    limit: int = 50,
    blocked_only: bool = False,
    current_user: User = Depends(get_current_user),
):
    """Return the most recent security audit events from the in-memory audit log."""
    if blocked_only:
        events = audit_log.get_blocked_events(limit=limit)
    else:
        events = audit_log.get_recent(limit=limit)
    return {
        "events": events,
        "stats": audit_log.get_stats(),
    }
