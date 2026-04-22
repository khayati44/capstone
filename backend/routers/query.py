"""
POST /api/query — Text-to-SQL natural language queries on transaction data.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.auth.dependencies import get_current_user
from backend.text_to_sql.query_engine import get_query_engine
from backend.schemas import QueryRequest, QueryResponse
from backend.guardrails.query_safety import check_query_safety
from backend.guardrails.rate_limiter import check_query_rate
from backend.guardrails.audit_logger import log_query_blocked, log_query_allowed, log_rate_limit_blocked

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def natural_language_query(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Answer natural language questions about transactions using Text-to-SQL.
    """
    # ── Guardrail: Rate Limiting ──────────────────────────────────────────────
    rate_result = check_query_rate(str(current_user.id))
    if not rate_result.allowed:
        log_rate_limit_blocked("/api/query", current_user.id, None, rate_result.retry_after_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Query rate limit exceeded. Try again in {rate_result.retry_after_seconds}s.",
            headers={"Retry-After": str(rate_result.retry_after_seconds)},
        )

    # ── Guardrail: Query Safety ─────────────────────────────────────────────
    safety = check_query_safety(request.question)
    if not safety.is_safe:
        log_query_blocked(
            request.question, safety.blocked_code or "UNSAFE",
            safety.risk_level, current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Query blocked by safety guardrail",
                "reason": safety.blocked_reason,
                "code": safety.blocked_code,
            },
        )

    log_query_allowed(request.question, current_user.id)

    # Use sanitized query for downstream processing
    safe_question = safety.sanitized_query
    engine = get_query_engine()
    result = engine.query(safe_question, user_id=current_user.id)

    return QueryResponse(
        question=result["question"],
        sql=result["sql"],
        result=result["result"],
        answer=result["answer"],
    )
