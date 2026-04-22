"""
Guardrail 4 — LLM Output Validator
Validates and sanitizes responses from the Groq LLM agents before they
are used in downstream processing or returned to the user.

Checks:
- JSON schema validation for Agent 1 & 2 outputs
- Section name whitelist (no hallucinated sections)
- Deduction percentage bounds (0–100)
- Amount reasonableness (no absurd values)
- Toxic/harmful content detection in text fields
"""

import re
import json
import logging
from typing import Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Whitelist of valid Indian tax sections
VALID_TAX_SECTIONS = {
    "80C", "80CCC", "80CCD", "80CCD(1B)",
    "80D", "80DD", "80DDB",
    "80E", "80EE", "80EEA",
    "80G", "80GG", "80GGA",
    "24B",
    "Section 37", "37",
    "NONE",
}

MAX_DEDUCTION_PERCENTAGE = 100.0
MIN_DEDUCTION_PERCENTAGE = 0.0
MAX_REASONABLE_AMOUNT = 100_000_000  # ₹10 crore — sanity cap
MAX_DESCRIPTION_LENGTH = 1000

# Patterns that should never appear in LLM output fields
TOXIC_CONTENT_PATTERNS = [
    r"<script[^>]*>",          # XSS
    r"javascript\s*:",         # JS injection
    r"on\w+\s*=\s*['\"]",     # HTML event handlers
    r"data\s*:\s*text/html",   # Data URIs
    r"\beval\s*\(",            # JS eval
    r"base64\s*,",             # Base64 data URIs
]


@dataclass
class LLMOutputValidationResult:
    is_valid: bool
    risk_level: str                      # SAFE / LOW / HIGH / CRITICAL
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sanitized_data: Optional[Any] = None


def validate_categorizer_output(data: Any, original_count: int) -> LLMOutputValidationResult:
    """
    Validate Agent 1 (TransactionCategorizer) output.
    Expects a list of dicts with merchant_type, likely_purpose, is_tax_relevant.
    """
    errors = []
    warnings = []

    if not isinstance(data, list):
        return LLMOutputValidationResult(
            is_valid=False,
            risk_level="HIGH",
            errors=["LLM output is not a JSON array"],
        )

    if len(data) != original_count:
        warnings.append(
            f"LLM returned {len(data)} items but input had {original_count} transactions"
        )

    sanitized = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            warnings.append(f"Item {i} is not a dict — skipping")
            continue

        clean = _sanitize_categorizer_item(item, i, errors, warnings)
        sanitized.append(clean)

    level = "HIGH" if errors else ("LOW" if warnings else "SAFE")
    return LLMOutputValidationResult(
        is_valid=len(errors) == 0,
        risk_level=level,
        errors=errors,
        warnings=warnings,
        sanitized_data=sanitized,
    )


def validate_tax_rule_output(data: Any) -> LLMOutputValidationResult:
    """
    Validate Agent 2 (TaxRuleMatcher) output for a single transaction.
    Expects dict with matched_section, deduction_percentage, conditions, confidence.
    """
    errors = []
    warnings = []

    if not isinstance(data, dict):
        return LLMOutputValidationResult(
            is_valid=False,
            risk_level="HIGH",
            errors=["Tax rule output is not a JSON object"],
        )

    # Validate matched_section
    section = str(data.get("matched_section", "NONE")).strip().upper()
    # Normalize common variations
    if section in {"NONE", "", "N/A", "NA", "NOT APPLICABLE"}:
        section = "NONE"
    if section not in VALID_TAX_SECTIONS:
        warnings.append(
            f"Hallucinated tax section '{section}' replaced with 'NONE'"
        )
        logger.warning(f"[GUARDRAIL:llm_output] Hallucinated section '{section}' → 'NONE'")
        section = "NONE"

    # Validate deduction_percentage
    try:
        pct = float(data.get("deduction_percentage", 0))
    except (TypeError, ValueError):
        pct = 0.0
        warnings.append("Invalid deduction_percentage — defaulting to 0")

    if pct < MIN_DEDUCTION_PERCENTAGE or pct > MAX_DEDUCTION_PERCENTAGE:
        warnings.append(
            f"Deduction percentage {pct} out of bounds — clamped to [0, 100]"
        )
        pct = max(MIN_DEDUCTION_PERCENTAGE, min(MAX_DEDUCTION_PERCENTAGE, pct))

    # Validate conditions text
    conditions = str(data.get("conditions", ""))[:500]
    if _has_toxic_content(conditions):
        errors.append("Toxic content detected in conditions field")
        conditions = "[REDACTED]"

    sanitized = {
        "matched_section": section,
        "deduction_percentage": pct,
        "conditions": conditions,
        "confidence": str(data.get("confidence", "LOW")),
    }

    level = "HIGH" if errors else ("LOW" if warnings else "SAFE")
    if warnings:
        logger.info(f"[GUARDRAIL:llm_output] Tax rule warnings: {warnings}")

    return LLMOutputValidationResult(
        is_valid=len(errors) == 0,
        risk_level=level,
        errors=errors,
        warnings=warnings,
        sanitized_data=sanitized,
    )


def validate_deduction_amounts(
    gross_deductible: float,
    transaction_amount: float,
    section: str,
) -> LLMOutputValidationResult:
    """
    Guardrail for deduction calculator: verify amounts are reasonable.
    """
    warnings = []
    errors = []

    if transaction_amount < 0:
        errors.append(f"Negative transaction amount: {transaction_amount}")

    if gross_deductible < 0:
        errors.append(f"Negative deductible amount: {gross_deductible}")

    if transaction_amount > MAX_REASONABLE_AMOUNT:
        warnings.append(
            f"Unusually large transaction amount ₹{transaction_amount:,.0f} — verify data"
        )

    # Deductible should never exceed the transaction amount × 100%
    if gross_deductible > transaction_amount * 1.001:  # 0.1% tolerance for float rounding
        warnings.append(
            f"Gross deductible ₹{gross_deductible:,.0f} exceeds transaction ₹{transaction_amount:,.0f}"
        )
        logger.warning(
            f"[GUARDRAIL:llm_output] Deductible > amount for section {section}: "
            f"deductible=₹{gross_deductible:,.0f} amount=₹{transaction_amount:,.0f}"
        )

    level = "HIGH" if errors else ("LOW" if warnings else "SAFE")
    return LLMOutputValidationResult(
        is_valid=len(errors) == 0,
        risk_level=level,
        errors=errors,
        warnings=warnings,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sanitize_categorizer_item(item: dict, idx: int,
                                errors: list, warnings: list) -> dict:
    """Sanitize a single transaction categorization item."""
    # merchant_type
    merchant_type = str(item.get("merchant_type", "Unknown"))[:200]
    if _has_toxic_content(merchant_type):
        warnings.append(f"Item {idx}: toxic content in merchant_type — cleared")
        merchant_type = "Unknown"

    # likely_purpose
    likely_purpose = str(item.get("likely_purpose", ""))[:500]
    if _has_toxic_content(likely_purpose):
        warnings.append(f"Item {idx}: toxic content in likely_purpose — cleared")
        likely_purpose = ""

    # is_tax_relevant — must be boolean
    raw_relevant = item.get("is_tax_relevant", False)
    if isinstance(raw_relevant, str):
        is_tax_relevant = raw_relevant.lower() in {"true", "yes", "1"}
    else:
        is_tax_relevant = bool(raw_relevant)

    return {
        **item,
        "merchant_type": merchant_type,
        "likely_purpose": likely_purpose,
        "is_tax_relevant": is_tax_relevant,
    }


def _has_toxic_content(text: str) -> bool:
    """Check if text contains XSS, injection, or other toxic patterns."""
    for pattern in TOXIC_CONTENT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False
