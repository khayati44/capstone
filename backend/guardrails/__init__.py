"""
backend.guardrails — Production guardrail suite for Smart Tax Deduction Finder

5 active guardrails:
  1. file_validator      — blocks malicious / invalid uploads
  2. rate_limiter        — sliding-window per-user / per-IP throttling
  3. query_safety        — SQL/prompt injection detection for NL queries
  4. llm_output_validator — validates & sanitizes Groq LLM responses
  5. audit_logger        — structured security event trail
"""

from backend.guardrails.file_validator import validate_upload, FileValidationResult
from backend.guardrails.rate_limiter import (
    check_login_rate, check_upload_rate, check_analysis_rate, check_query_rate,
    reset_login_rate, RateLimitResult,
)
from backend.guardrails.query_safety import check_query_safety, QuerySafetyResult
from backend.guardrails.llm_output_validator import (
    validate_categorizer_output, validate_tax_rule_output, validate_deduction_amounts,
)
from backend.guardrails.audit_logger import audit_log

__all__ = [
    "validate_upload", "FileValidationResult",
    "check_login_rate", "check_upload_rate", "check_analysis_rate", "check_query_rate",
    "reset_login_rate", "RateLimitResult",
    "check_query_safety", "QuerySafetyResult",
    "validate_categorizer_output", "validate_tax_rule_output", "validate_deduction_amounts",
    "audit_log",
]
