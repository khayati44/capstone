"""
Agent 3 — Deduction Calculator
Calculates exact deductible amounts respecting section limits under Indian Income Tax Act.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Section limits in INR
SECTION_LIMITS = {
    "80C": 150000,       # ₹1,50,000
    "80CCC": 150000,     # Included in 80C aggregate
    "80CCD": 150000,     # NPS — additional ₹50,000 under 80CCD(1B)
    "80D": 25000,        # Health insurance (₹50,000 for senior citizens)
    "80D_SENIOR": 50000,
    "80E": float("inf"), # Education loan interest — no limit
    "80G": float("inf"), # Donations — percentage capped (handled per transaction)
    "80GG": 60000,       # ₹5,000/month = ₹60,000/year
    "24B": 200000,       # ₹2,00,000 home loan interest (self-occupied)
    "24B_LET_OUT": float("inf"),  # Let-out property — no limit
    "Section 37": float("inf"),   # Business expenses
    "NONE": 0,
}

# Aggregate sections (combined limit shared across sub-sections)
AGGREGATE_80C_SECTIONS = {"80C", "80CCC", "80CCD"}


@dataclass
class DeductionLineItem:
    transaction_id: int
    date: Optional[str]
    description: Optional[str]
    amount: float
    section: str
    deduction_percentage: float
    gross_deductible: float
    deductible_amount: float  # After applying limits
    conditions: Optional[str]


@dataclass
class SectionSummary:
    section: str
    total_deductible: float
    limit: float
    capped_deductible: float
    transaction_count: int


@dataclass
class DeductionReport:
    upload_id: int
    total_gross_deductions: float
    total_capped_deductions: float
    estimated_tax_saved_20_percent: float
    estimated_tax_saved_30_percent: float
    sections_covered: list[str]
    line_items: list[DeductionLineItem]
    section_summaries: list[SectionSummary]

    def to_dict(self) -> dict:
        return {
            "upload_id": self.upload_id,
            "total_gross_deductions": round(self.total_gross_deductions, 2),
            "total_capped_deductions": round(self.total_capped_deductions, 2),
            "estimated_tax_saved_20_percent": round(self.estimated_tax_saved_20_percent, 2),
            "estimated_tax_saved_30_percent": round(self.estimated_tax_saved_30_percent, 2),
            "sections_covered": self.sections_covered,
            "line_items": [
                {
                    "transaction_id": li.transaction_id,
                    "date": li.date,
                    "description": li.description,
                    "amount": round(li.amount, 2),
                    "section": li.section,
                    "deduction_percentage": li.deduction_percentage,
                    "gross_deductible": round(li.gross_deductible, 2),
                    "deductible_amount": round(li.deductible_amount, 2),
                    "conditions": li.conditions,
                }
                for li in self.line_items
            ],
            "section_summaries": [
                {
                    "section": ss.section,
                    "total_deductible": round(ss.total_deductible, 2),
                    "limit": ss.limit if ss.limit != float("inf") else -1,
                    "capped_deductible": round(ss.capped_deductible, 2),
                    "transaction_count": ss.transaction_count,
                }
                for ss in self.section_summaries
            ],
        }


def calculate_deductions(transactions: list[dict], upload_id: int) -> DeductionReport:
    """
    Agent 3: Calculate deductible amounts respecting section limits.
    """
    line_items: list[DeductionLineItem] = []
    section_buckets: dict[str, list[float]] = {}

    def _parse_amount(val) -> float:
        try:
            if val is None:
                return 0.0
            s = str(val)
            s = s.replace(',', '').replace('₹', '').strip()
            return float(s) if s != '' else 0.0
        except Exception:
            return 0.0

    for idx, tx in enumerate(transactions):
        section = tx.get("matched_section", "NONE")
        if section == "NONE" or section is None:
            continue

        amount = _parse_amount(tx.get("debit_amount", 0.0))
        if amount <= 0:
            amount = _parse_amount(tx.get("credit_amount", 0.0))
        if amount <= 0:
            continue

        deduction_pct = _parse_amount(tx.get("deduction_percentage", 100.0))
        gross_deductible = amount * (deduction_pct / 100.0)

        if section not in section_buckets:
            section_buckets[section] = []
        section_buckets[section].append(gross_deductible)

        line_items.append(DeductionLineItem(
            transaction_id=tx.get("id", idx),
            date=tx.get("date"),
            description=tx.get("description"),
            amount=amount,
            section=section,
            deduction_percentage=deduction_pct,
            gross_deductible=gross_deductible,
            deductible_amount=gross_deductible,  # Will be adjusted below
            conditions=tx.get("conditions"),
        ))

    # Apply section limits & compute summaries
    section_summaries: list[SectionSummary] = []
    # Track 80C aggregate
    agg_80c_total = sum(
        sum(section_buckets.get(s, []))
        for s in AGGREGATE_80C_SECTIONS
        if s in section_buckets
    )

    for section, amounts in section_buckets.items():
        total = sum(amounts)
        limit = SECTION_LIMITS.get(section, float("inf"))
        count = len(amounts)

        # 80C aggregate cap
        if section in AGGREGATE_80C_SECTIONS:
            capped = min(agg_80c_total, SECTION_LIMITS["80C"])
            # Proportional allocation for each 80C sub-section
            if agg_80c_total > 0:
                capped = min(total, capped * (total / agg_80c_total))
            else:
                capped = 0.0
        else:
            capped = min(total, limit)

        section_summaries.append(SectionSummary(
            section=section,
            total_deductible=total,
            limit=limit,
            capped_deductible=capped,
            transaction_count=count,
        ))

    # Update line item deductible amounts with proportional capping
    section_cap_map: dict[str, float] = {ss.section: ss.capped_deductible for ss in section_summaries}
    section_total_map: dict[str, float] = {ss.section: ss.total_deductible for ss in section_summaries}

    for li in line_items:
        total = section_total_map.get(li.section, 0)
        capped = section_cap_map.get(li.section, 0)
        if total > 0 and capped < total:
            li.deductible_amount = li.gross_deductible * (capped / total)
        else:
            li.deductible_amount = li.gross_deductible

    total_gross = sum(li.gross_deductible for li in line_items)
    total_capped = sum(li.deductible_amount for li in line_items)
    tax_20 = total_capped * 0.20
    tax_30 = total_capped * 0.30
    sections_covered = sorted(set(li.section for li in line_items if li.section != "NONE"))

    logger.info(
        f"DeductionReport: gross=₹{total_gross:,.0f}, capped=₹{total_capped:,.0f}, "
        f"tax_saved_20%=₹{tax_20:,.0f}, sections={sections_covered}"
    )

    return DeductionReport(
        upload_id=upload_id,
        total_gross_deductions=total_gross,
        total_capped_deductions=total_capped,
        estimated_tax_saved_20_percent=tax_20,
        estimated_tax_saved_30_percent=tax_30,
        sections_covered=sections_covered,
        line_items=line_items,
        section_summaries=section_summaries,
    )
