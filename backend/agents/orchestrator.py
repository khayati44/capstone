"""
Orchestrator — runs the 3-agent pipeline in sequence:
Agent 1 (TransactionCategorizer) → Agent 2 (TaxRuleMatcher) → Agent 3 (DeductionCalculator)
"""

import json
import logging
from dataclasses import asdict
from typing import Optional

from backend.agents.transaction_categorizer import categorize_transactions
from backend.agents.tax_rule_matcher import match_tax_rules
from backend.agents.deduction_calculator import calculate_deductions, DeductionReport

logger = logging.getLogger(__name__)


def run_pipeline(transactions: list[dict], upload_id: int) -> dict:
    """
    Run the complete 3-agent tax analysis pipeline.

    Args:
        transactions: List of raw transaction dicts from OCR
        upload_id: Database upload record ID

    Returns:
        dict with pipeline results and DeductionReport as JSON-serializable dict
    """
    if not transactions:
        return {
            "status": "error",
            "message": "No transactions provided",
            "report": None,
        }

    logger.info(f"Starting pipeline for upload_id={upload_id} with {len(transactions)} transactions")

    # ── Agent 1: Categorize ──────────────────────────────────────────────────
    logger.info("Agent 1: Transaction Categorizer starting...")
    categorized = categorize_transactions(transactions)
    tax_relevant_count = sum(1 for t in categorized if t.get("is_tax_relevant"))
    logger.info(f"Agent 1 complete. Tax-relevant transactions: {tax_relevant_count}/{len(categorized)}")

    # ── Agent 2: Match Tax Rules ─────────────────────────────────────────────
    logger.info("Agent 2: Tax Rule Matcher starting...")
    matched = match_tax_rules(categorized)
    matched_count = sum(1 for t in matched if t.get("matched_section", "NONE") != "NONE")
    logger.info(f"Agent 2 complete. Matched to tax sections: {matched_count}/{len(matched)}")

    # ── Agent 3: Calculate Deductions ────────────────────────────────────────
    logger.info("Agent 3: Deduction Calculator starting...")
    report: DeductionReport = calculate_deductions(matched, upload_id)
    logger.info(f"Agent 3 complete. Total deductions: ₹{report.total_capped_deductions:,.0f}")

    return {
        "status": "success",
        "transaction_count": len(transactions),
        "tax_relevant_count": tax_relevant_count,
        "matched_count": matched_count,
        "categorized_transactions": matched,
        "report": report.to_dict(),
    }
