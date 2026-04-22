"""
Agent 1 — Transaction Categorizer
Categorizes each transaction with merchant_type, likely_purpose, is_tax_relevant.
Uses Groq LLM (llama-3.3-70b-versatile) with engineered prompts.
"""

import json
import logging
from typing import Any
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    Groq = None
    GROQ_AVAILABLE = False

from backend.config import get_settings
from backend.guardrails.llm_output_validator import validate_categorizer_output
from backend.guardrails.audit_logger import log_llm_output_warning

logger = logging.getLogger(__name__)
settings = get_settings()


CATEGORIZER_SYSTEM_PROMPT = """You are an expert Indian tax consultant and financial analyst. 
Your task is to analyze bank transactions of Indian salaried employees and categorize them 
for income tax deduction purposes.

For each transaction, determine:
1. merchant_type: The type of merchant/payee (e.g., "Insurance Company", "Hospital", "School", 
   "Bank/NBFC", "Charity/NGO", "Mutual Fund/ELSS", "Housing Loan EMI", "Education Loan", 
   "PPF/EPF/NPS", "Rent Payment", "Utility", "Shopping", "Unknown")
2. likely_purpose: What this transaction is likely for (be specific)
3. is_tax_relevant: true/false — whether this transaction MIGHT qualify for any income tax 
   deduction under Indian tax law (Sections 80C, 80D, 80E, 80G, 80GG, 24B, Section 37, etc.)

Common tax-relevant transactions:
- LIC/insurance premium payments → 80C, 80D
- School/college tuition fees → 80C
- PPF/EPF/NPS contributions → 80C
- ELSS mutual fund investments → 80C
- Home loan EMI payments → 24B (interest component)
- Education loan interest → 80E
- Donations to NGOs/charities/PM funds → 80G
- Rent payments (if no HRA) → 80GG
- Health insurance premiums → 80D
- Medical expenses for senior parents → 80D

Return ONLY a valid JSON array with objects containing: date, description, debit_amount, 
credit_amount, balance, raw_text, merchant_type, likely_purpose, is_tax_relevant.
No markdown, no explanation — pure JSON array only."""


CATEGORIZER_USER_TEMPLATE = """Categorize these bank transactions for Indian tax deduction analysis.

Transactions:
{transactions_json}

Return a JSON array with each transaction enriched with merchant_type, likely_purpose, and is_tax_relevant fields.
Preserve all original fields. Return ONLY the JSON array."""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _call_groq(client: Groq, messages: list[dict]) -> str:
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        temperature=0.1,
        max_tokens=4096,
    )
    return response.choices[0].message.content


def _batch_transactions(transactions: list[dict], batch_size: int = 20) -> list[list[dict]]:
    """Split transactions into batches for LLM processing."""
    return [transactions[i:i + batch_size] for i in range(0, len(transactions), batch_size)]


def _heuristic_categorize(tx: dict) -> dict:
    """Simple rule-based categorizer used when LLM is not available.

    Adds `merchant_type`, `likely_purpose`, and `is_tax_relevant`.
    """
    text = " ".join([str(tx.get(k, "")) for k in ("description", "raw_text")]).lower()
    out = dict(tx)
    out.setdefault("merchant_type", "Unknown")
    out.setdefault("likely_purpose", "")
    out.setdefault("is_tax_relevant", False)
    out.setdefault("category", "other")
    
    # Log what we're processing
    logger.info(f"Categorizing: '{text[:100]}'")

    # keyword-driven mapping with expanded patterns
    if any(k in text for k in ["insurance", "lic", "health insur", "premium", "policy", "hdfc life", "icici pru", "max life", "sbi life"]):
        out["merchant_type"] = "Insurance Company"
        out["likely_purpose"] = "Health/Life insurance premium"
        out["is_tax_relevant"] = True
        out["category"] = "insurance"
        logger.info(f"  → Matched INSURANCE")
    elif any(k in text for k in ["provident", "ppf", "epf", "public provident", "pf", "nps", "national pension", "retirement"]):
        out["merchant_type"] = "PPF/EPF/NPS"
        out["likely_purpose"] = "Retirement savings / PPF/EPF contribution"
        out["is_tax_relevant"] = True
        out["category"] = "ppf"
        logger.info(f"  → Matched PPF/EPF/NPS")
    elif any(k in text for k in ["tuition", "school", "college", "education fee", "university", "institute", "academy", "kindergarten"]):
        out["merchant_type"] = "Education/School"
        out["likely_purpose"] = "Tuition fees"
        out["is_tax_relevant"] = True
        out["category"] = "education"
    elif any(k in text for k in ["donation", "donat", "charit", "ngo", "trust", "relief fund", "pm cares", "red cross"]):
        out["merchant_type"] = "Charity/NGO"
        out["likely_purpose"] = "Donation"
        out["is_tax_relevant"] = True
        out["category"] = "donation"
    elif any(k in text for k in ["home loan", "housing loan", "emi", "hdfc home", "sbi home", "icici home", "mortgage"]):
        out["merchant_type"] = "Housing Loan EMI"
        out["likely_purpose"] = "Home loan interest/EMI"
        out["is_tax_relevant"] = True
        out["category"] = "housing loan"
    elif any(k in text for k in ["education loan", "student loan", "study loan"]):
        out["merchant_type"] = "Education Loan"
        out["likely_purpose"] = "Education loan interest"
        out["is_tax_relevant"] = True
        out["category"] = "education"
    elif any(k in text for k in ["elss", "mutual fund", "equity fund", "tax saver", "sip", "systematic investment"]):
        out["merchant_type"] = "Mutual Fund/ELSS"
        out["likely_purpose"] = "ELSS mutual fund investment"
        out["is_tax_relevant"] = True
        out["category"] = "mutual fund"
    elif any(k in text for k in ["tax deducted", "tds", "tax deducted at source"]):
        out["merchant_type"] = "Bank/NBFC"
        out["likely_purpose"] = "TDS / tax line"
        out["is_tax_relevant"] = False
        out["category"] = "tax"

    return out


def categorize_transactions(transactions: list[dict]) -> list[dict]:
    """
    Agent 1: Categorize transactions using Groq LLM.
    Input: list of raw transaction dicts
    Output: enriched transaction dicts with categorization fields
    """
    if not transactions:
        return []

    # If Groq is not available or API key is not configured, use simple heuristics
    if not GROQ_AVAILABLE:
        logger.warning("Groq SDK not installed — using heuristic categorizer")
        enriched = [_heuristic_categorize(tx) for tx in transactions]
        tax_relevant_count = sum(1 for t in enriched if t.get('is_tax_relevant'))
        logger.info(f"Heuristic categorizer (Groq unavailable): {tax_relevant_count}/{len(enriched)} tax-relevant")
        if tax_relevant_count == 0:
            logger.warning(f"No tax-relevant transactions found. Sample descriptions: {[t.get('description', '')[:50] for t in transactions[:3]]}")
        return enriched

    if not settings.groq_api_key or settings.groq_api_key.startswith("your_groq"):
        enriched = [_heuristic_categorize(tx) for tx in transactions]
        tax_relevant_count = sum(1 for t in enriched if t.get('is_tax_relevant'))
        logger.info(f"Heuristic categorizer (no API key): {tax_relevant_count}/{len(enriched)} tax-relevant")
        if tax_relevant_count == 0:
            logger.warning(f"No tax-relevant transactions found. Sample descriptions: {[t.get('description', '')[:50] for t in transactions[:3]]}")
        return enriched

    client = Groq(api_key=settings.groq_api_key)
    enriched = []
    batches = _batch_transactions(transactions)

    for batch_idx, batch in enumerate(batches):
        logger.info(f"Categorizing batch {batch_idx + 1}/{len(batches)} ({len(batch)} transactions)")

        # Simplify for LLM (avoid huge context)
        simplified = []
        for tx in batch:
            simplified.append({
                "date": tx.get("date", ""),
                "description": tx.get("description", ""),
                "debit_amount": tx.get("debit_amount", 0.0),
                "credit_amount": tx.get("credit_amount", 0.0),
                "balance": tx.get("balance"),
                "raw_text": (tx.get("raw_text") or "")[:100],
            })

        try:
            messages = [
                {"role": "system", "content": CATEGORIZER_SYSTEM_PROMPT},
                {"role": "user", "content": CATEGORIZER_USER_TEMPLATE.format(
                    transactions_json=json.dumps(simplified, indent=2)
                )},
            ]
            response_text = _call_groq(client, messages)

            # Extract JSON from response
            response_text = response_text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            categorized_batch = json.loads(response_text)
            if isinstance(categorized_batch, list):
                # ── Guardrail: Validate LLM output ──────────────────────────────
                val_result = validate_categorizer_output(categorized_batch, len(batch))
                if val_result.warnings:
                    log_llm_output_warning("llm_output_validator", val_result.warnings)
                categorized_batch = val_result.sanitized_data
                # Merge with original data
                for orig, cat in zip(batch, categorized_batch):
                    merged = {**orig, **{
                        "merchant_type": cat.get("merchant_type", "Unknown"),
                        "likely_purpose": cat.get("likely_purpose", ""),
                        "is_tax_relevant": bool(cat.get("is_tax_relevant", False)),
                    }}
                    enriched.append(merged)
            else:
                logger.warning("LLM returned non-list response, using originals")
                for tx in batch:
                    tx.setdefault("merchant_type", "Unknown")
                    tx.setdefault("likely_purpose", "")
                    tx.setdefault("is_tax_relevant", False)
                    enriched.append(tx)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in batch {batch_idx}: {e}")
            for tx in batch:
                tx.setdefault("merchant_type", "Unknown")
                tx.setdefault("likely_purpose", "")
                tx.setdefault("is_tax_relevant", False)
                enriched.append(tx)
        except Exception as e:
            logger.error(f"Groq API error in batch {batch_idx}: {e}")
            for tx in batch:
                tx.setdefault("merchant_type", "Unknown")
                tx.setdefault("likely_purpose", "")
                tx.setdefault("is_tax_relevant", False)
                enriched.append(tx)

    logger.info(f"Categorization complete. Tax-relevant: {sum(1 for t in enriched if t.get('is_tax_relevant'))}")
    return enriched
