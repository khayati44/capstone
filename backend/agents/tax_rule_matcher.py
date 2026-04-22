"""
Agent 2 — Tax Rule Matcher
Matches transactions to Indian Income Tax sections using RAG + Groq LLM.
"""

import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    Groq = None
    GROQ_AVAILABLE = False

from backend.config import get_settings
from backend.rag.retriever import get_retriever
from backend.guardrails.llm_output_validator import validate_tax_rule_output
from backend.guardrails.audit_logger import log_llm_output_warning

logger = logging.getLogger(__name__)
settings = get_settings()


# Rule-based mapping from simple categories (from classifier) to tax sections
# Format: category -> (section, deduction_percentage, conditions)
CATEGORY_TO_SECTION = {
    "medical": ("80D", 100.0, "Health insurance premiums for self/family"),
    "insurance": ("80C", 100.0, "Life insurance premiums/principal repayment where applicable"),
    "education": ("80E", 100.0, "Education loan interest or tuition fees (if applicable under 80C)") ,
    "rent": ("80GG", 100.0, "Rent paid when HRA not received; subject to 80GG rules"),
    "internet": ("Section 37", 100.0, "Business/remote-work internet expenses (self-employed)") ,
    "donation": ("80G", 50.0, "Donations to approved funds (50% or 100% depending on fund)") ,
    "other": ("NONE", 0.0, "No standard deduction mapping"),
    "tax": ("NONE", 0.0, "Generic tax line"),
}

# Extra keyword keys to help heuristic categorizer map to sections
CATEGORY_TO_SECTION.update({
    "ppf": ("80C", 100.0, "PPF/EPF/NPS contributions included under 80C"),
    "epf": ("80C", 100.0, "PPF/EPF/NPS contributions included under 80C"),
    "nps": ("80C", 100.0, "PPF/EPF/NPS contributions included under 80C"),
    "housing loan": ("24B", 100.0, "Home loan interest for self-occupied property"),
    "home loan": ("24B", 100.0, "Home loan interest for self-occupied property"),
    "emi": ("24B", 100.0, "Home loan EMI (interest component applies)") ,
    "tuition": ("80C", 100.0, "Tuition fees under 80C where applicable"),
    "mutual": ("80C", 100.0, "ELSS/mutual funds under 80C"),
    "mutual fund": ("80C", 100.0, "ELSS/mutual funds under 80C"),
    "elss": ("80C", 100.0, "ELSS/mutual funds under 80C"),
})


TAX_RULE_SYSTEM_PROMPT = """You are an expert Indian chartered accountant specializing in 
income tax deductions under the Income Tax Act, 1961.

Given a bank transaction and relevant tax law excerpts, determine:
1. matched_section: The most applicable tax section (e.g., "80C", "80D", "80E", "80G", "80GG", "24B", "Section 37", or "NONE")
2. deduction_percentage: Percentage of the transaction amount that is deductible (0-100)
3. conditions: Key conditions that must be met for this deduction to apply
4. confidence: Your confidence level ("HIGH", "MEDIUM", "LOW")

Section reference:
- 80C: Life insurance, PPF, ELSS, EPF, tuition fees, NSC, principal of home loan — max ₹1,50,000
- 80D: Health insurance premiums — max ₹25,000 (₹50,000 for senior citizens)
- 80E: Education loan interest — 100%, no limit
- 80G: Donations to approved funds — 50% or 100% depending on fund
- 80GG: Rent paid when no HRA — least of (₹5000/month, 25% of income, rent - 10% income)
- 24B: Home loan interest — max ₹2,00,000 for self-occupied
- Section 37: Business/professional expenses — 100% if wholly for business
- NONE: No applicable deduction

Return ONLY valid JSON with keys: matched_section, deduction_percentage, conditions, confidence.
No markdown, no explanation."""


TAX_RULE_USER_TEMPLATE = """Transaction details:
Date: {date}
Description: {description}
Amount: ₹{amount}
Merchant Type: {merchant_type}
Likely Purpose: {likely_purpose}

Relevant tax law excerpts from knowledge base:
{rag_context}

Based on this information, what tax section applies to this transaction?
Return JSON: {{matched_section, deduction_percentage, conditions, confidence}}"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _call_groq(client: Groq, messages: list[dict]) -> str:
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        temperature=0.05,
        max_tokens=512,
    )
    return response.choices[0].message.content


def match_tax_rules(transactions: list[dict]) -> list[dict]:
    """
    Agent 2: Match each tax-relevant transaction to Indian tax sections.
    Uses RAG for grounding + Groq LLM for final decision.
    """
    if not transactions:
        return []

    # Check if Groq is available
    use_llm = GROQ_AVAILABLE and settings.groq_api_key and not settings.groq_api_key.startswith("your_groq")
    
    if not use_llm:
        if not GROQ_AVAILABLE:
            logger.warning("Groq SDK not available — using rule-based tax matching only")
        else:
            logger.warning("Groq API key not configured — using rule-based tax matching only")
    
    client = Groq(api_key=settings.groq_api_key) if use_llm else None
    retriever = get_retriever()
    results = []

    # Only process tax-relevant transactions through LLM
    for tx in transactions:
        if not tx.get("is_tax_relevant", False):
            tx["matched_section"] = "NONE"
            tx["deduction_percentage"] = 0.0
            tx["conditions"] = ""
            tx["confidence"] = "HIGH"
            results.append(tx)
            continue

        # Rule-based shortcut: if classifier provided a high-confidence category,
        # map it directly to a tax section without calling the LLM.
        category = tx.get("category") or tx.get("merchant_type") or tx.get("likely_purpose")
        if category:
            cat_key = str(category).strip().lower()
            # Try exact key then substring matches (to handle values like 'Insurance Company')
            matched = None
            if cat_key in CATEGORY_TO_SECTION:
                matched = cat_key
            else:
                for k in CATEGORY_TO_SECTION.keys():
                    if k in cat_key:
                        matched = k
                        break
            # also try likely_purpose keywords
            if not matched:
                lp = str(tx.get("likely_purpose", "")).lower()
                for k in CATEGORY_TO_SECTION.keys():
                    if k in lp:
                        matched = k
                        break

            if matched:
                sec, pct, cond = CATEGORY_TO_SECTION[matched]
                tx["matched_section"] = sec
                tx["deduction_percentage"] = pct
                tx["conditions"] = cond
                tx["confidence"] = "HIGH"
                results.append(tx)
                continue

        # If LLM is not available, apply a fallback rule-based match
        if not use_llm:
            # Try to map by merchant_type or likely_purpose keywords
            tx["matched_section"] = "NONE"
            tx["deduction_percentage"] = 0.0
            tx["conditions"] = "LLM not available; requires manual review"
            tx["confidence"] = "LOW"
            results.append(tx)
            continue

        # Build query for RAG
        query = f"{tx.get('description', '')} {tx.get('merchant_type', '')} {tx.get('likely_purpose', '')}"
        rag_chunks = retriever.query(query, k=3)
        rag_context = "\n---\n".join(rag_chunks) if rag_chunks else "No specific context found."

        amount = tx.get("debit_amount", 0.0) or tx.get("credit_amount", 0.0)

        try:
            messages = [
                {"role": "system", "content": TAX_RULE_SYSTEM_PROMPT},
                {"role": "user", "content": TAX_RULE_USER_TEMPLATE.format(
                    date=tx.get("date", "Unknown"),
                    description=tx.get("description", "")[:200],
                    amount=f"{amount:,.2f}",
                    merchant_type=tx.get("merchant_type", "Unknown"),
                    likely_purpose=tx.get("likely_purpose", ""),
                    rag_context=rag_context[:1500],
                )},
            ]
            response_text = _call_groq(client, messages).strip()

            # Strip markdown if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            match_data = json.loads(response_text)
            # ── Guardrail: Validate LLM output ────────────────────────────────
            val_result = validate_tax_rule_output(match_data)
            if val_result.warnings:
                log_llm_output_warning("llm_output_validator", val_result.warnings)
            match_data = val_result.sanitized_data
            tx["matched_section"] = match_data.get("matched_section", "NONE")
            tx["deduction_percentage"] = float(match_data.get("deduction_percentage", 0))
            tx["conditions"] = match_data.get("conditions", "")
            tx["confidence"] = match_data.get("confidence", "LOW")

        except Exception as e:
            logger.error(f"Tax rule matching failed for '{tx.get('description')}': {e}")
            tx["matched_section"] = "NONE"
            tx["deduction_percentage"] = 0.0
            tx["conditions"] = ""
            tx["confidence"] = "LOW"

        results.append(tx)

    matched = sum(1 for t in results if t.get("matched_section") != "NONE")
    logger.info(f"Tax rule matching complete. Matched: {matched}/{len(results)}")
    return results
