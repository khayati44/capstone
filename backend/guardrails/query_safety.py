"""
Guardrail 3 — Query Safety Checker
Validates natural language queries before they reach the Text-to-SQL engine.

Checks:
- Length limits (prevent context flooding)
- SQL injection patterns
- Prompt injection attempts targeting the LLM
- Forbidden keywords that could expose other users' data
- Scope enforcement (only tax/transaction domain questions)
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 500
MIN_QUERY_LENGTH = 3

# ── SQL Injection patterns ────────────────────────────────────────────────────
SQL_INJECTION_PATTERNS = [
    r";\s*(DROP|DELETE|TRUNCATE|ALTER|CREATE|INSERT|UPDATE)\s",
    r"--\s*$",                          # SQL comment at end
    r"/\*.*?\*/",                       # Block comments
    r"\bUNION\s+(ALL\s+)?SELECT\b",    # UNION SELECT
    r"\bOR\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?",  # OR '1'='1'
    r"\bEXEC\s*\(",                     # EXEC(
    r"\bxp_\w+",                        # SQL Server extended procs
    r"0x[0-9a-fA-F]+",                 # Hex literals (obfuscation)
    r"\bINFORMATION_SCHEMA\b",         # Schema enumeration
    r"\bSYS\.(TABLES|COLUMNS|OBJECTS)\b",  # System tables
]

# ── Prompt injection patterns ─────────────────────────────────────────────────
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+a",
    r"forget\s+(everything|all|your)",
    r"new\s+instruction[s]?\s*:",
    r"system\s*:\s*",
    r"act\s+as\s+(if\s+you\s+are|a\s+)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"jailbreak",
    r"DAN\s+mode",
    r"override\s+(your\s+)?(safety|system|instructions)",
    r"<\s*/?system\s*>",               # XML-style system tags
    r"\[INST\]|\[/INST\]",            # Llama instruction tokens
    r"###\s*Human:|###\s*Assistant:",  # Role-play injection
]

# ── Data exfiltration patterns ────────────────────────────────────────────────
DATA_EXFILTRATION_PATTERNS = [
    r"\bALL\s+USERS?\b",               # Trying to query all users
    r"\bUSER[S]?\s+TABLE\b",
    r"\bhashed_password\b",            # Trying to extract passwords
    r"\bsecret_key\b",
    r"\bpassword[s]?\b",
    r"user_id\s*[!=<>]+\s*\d+.*user_id",  # Cross-user data access
    r"\*\s+FROM\s+users",             # SELECT * FROM users
]

# ── Domain scope (only tax/transaction queries allowed) ───────────────────────
TAX_DOMAIN_KEYWORDS = {
    "transaction", "payment", "deduction", "tax", "section", "insurance",
    "premium", "loan", "emi", "rent", "donation", "investment", "amount",
    "total", "sum", "average", "list", "show", "find", "get", "how much",
    "how many", "what", "which", "when", "monthly", "annual", "yearly",
    "balance", "credit", "debit", "bank", "income", "salary", "expense",
    "elss", "ppf", "epf", "nps", "lic", "mutual fund", "fd", "fixed deposit",
    "80c", "80d", "80e", "80g", "80gg", "24b", "rupee", "inr", "₹",
    "health", "education", "home", "house", "charity", "ngo", "interest",
    "principal", "fy", "ay", "financial year", "assessment year",
}


@dataclass
class QuerySafetyResult:
    is_safe: bool
    risk_level: str          # "SAFE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    blocked_reason: Optional[str] = None
    blocked_code: Optional[str] = None
    sanitized_query: Optional[str] = None


def check_query_safety(query: str) -> QuerySafetyResult:
    """
    Run all query safety guardrails. Returns QuerySafetyResult.
    Always call this before passing a query to the Text-to-SQL engine.
    """
    # 1. Length checks
    if not query or len(query.strip()) < MIN_QUERY_LENGTH:
        return QuerySafetyResult(
            is_safe=False,
            risk_level="LOW",
            blocked_code="QUERY_TOO_SHORT",
            blocked_reason=f"Query must be at least {MIN_QUERY_LENGTH} characters",
        )

    if len(query) > MAX_QUERY_LENGTH:
        return QuerySafetyResult(
            is_safe=False,
            risk_level="MEDIUM",
            blocked_code="QUERY_TOO_LONG",
            blocked_reason=f"Query exceeds {MAX_QUERY_LENGTH} character limit (got {len(query)})",
        )

    query_lower = query.lower()

    # 2. SQL injection check
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"[GUARDRAIL:query_safety] SQL_INJECTION blocked: pattern='{pattern}' query='{query[:100]}'")
            return QuerySafetyResult(
                is_safe=False,
                risk_level="CRITICAL",
                blocked_code="SQL_INJECTION_DETECTED",
                blocked_reason="Query contains SQL injection patterns and cannot be processed",
            )

    # 3. Prompt injection check
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"[GUARDRAIL:query_safety] PROMPT_INJECTION blocked: pattern='{pattern}' query='{query[:100]}'")
            return QuerySafetyResult(
                is_safe=False,
                risk_level="HIGH",
                blocked_code="PROMPT_INJECTION_DETECTED",
                blocked_reason="Query appears to attempt prompt injection and has been blocked",
            )

    # 4. Data exfiltration check
    for pattern in DATA_EXFILTRATION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"[GUARDRAIL:query_safety] DATA_EXFIL blocked: pattern='{pattern}' query='{query[:100]}'")
            return QuerySafetyResult(
                is_safe=False,
                risk_level="HIGH",
                blocked_code="DATA_EXFILTRATION_ATTEMPT",
                blocked_reason="Query attempts to access data outside your permitted scope",
            )

    # 5. Domain relevance check (soft warning, not blocking — log only)
    has_domain_keyword = any(kw in query_lower for kw in TAX_DOMAIN_KEYWORDS)
    if not has_domain_keyword:
        logger.info(f"[GUARDRAIL:query_safety] OUT_OF_DOMAIN (allowed): query='{query[:80]}'")
        # Allow but note it — the LLM may return empty results

    # 6. Sanitize — strip leading/trailing whitespace, collapse internal spaces
    sanitized = re.sub(r"\s+", " ", query.strip())

    logger.info(f"[GUARDRAIL:query_safety] SAFE — query='{sanitized[:80]}'")
    return QuerySafetyResult(
        is_safe=True,
        risk_level="SAFE",
        sanitized_query=sanitized,
    )
