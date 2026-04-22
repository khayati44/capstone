"""
Complete end-to-end test of the tax deduction pipeline
Tests: OCR → Categorization → Tax Matching → Deduction Calculation
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_ocr_extraction():
    """Test PDF text extraction"""
    print("=" * 60)
    print("TEST 1: OCR EXTRACTION")
    print("=" * 60)
    
    from backend.ocr.extractor import extract_transactions_from_pdf
    
    # Read the sample PDF
    with open('sample_bank_statement.pdf', 'rb') as f:
        pdf_bytes = f.read()
    
    transactions, full_text, bank_name = extract_transactions_from_pdf(pdf_bytes)
    
    print(f"✓ Extracted {len(transactions)} transactions")
    print(f"✓ Bank: {bank_name}")
    print(f"✓ Text length: {len(full_text)} chars")
    print()
    
    if len(transactions) == 0:
        print("❌ FAIL: No transactions extracted!")
        return None
    
    print("Sample transactions:")
    for i, tx in enumerate(transactions[:3], 1):
        print(f"  {i}. {tx.date} | {tx.description[:50]} | ₹{tx.debit_amount:,.0f}")
    
    print()
    return [
        {
            "id": i,
            "date": tx.date,
            "description": tx.description,
            "debit_amount": tx.debit_amount,
            "credit_amount": tx.credit_amount,
            "balance": tx.balance,
            "raw_text": tx.raw_text
        }
        for i, tx in enumerate(transactions, 1)
    ]


def test_categorization(transactions):
    """Test transaction categorization"""
    print("=" * 60)
    print("TEST 2: CATEGORIZATION")
    print("=" * 60)
    
    from backend.agents.transaction_categorizer import categorize_transactions
    
    categorized = categorize_transactions(transactions)
    
    tax_relevant = [t for t in categorized if t.get('is_tax_relevant')]
    
    print(f"✓ Categorized {len(categorized)} transactions")
    print(f"✓ Tax-relevant: {len(tax_relevant)}")
    print()
    
    if len(tax_relevant) == 0:
        print("❌ FAIL: No tax-relevant transactions found!")
        return None
    
    print("Tax-relevant transactions:")
    for tx in tax_relevant[:5]:
        print(f"  • {tx['description'][:40]:40} → {tx.get('category', 'N/A'):15} (tax_relevant: {tx['is_tax_relevant']})")
    
    print()
    return categorized


def test_tax_matching(transactions):
    """Test tax rule matching"""
    print("=" * 60)
    print("TEST 3: TAX RULE MATCHING")
    print("=" * 60)
    
    from backend.agents.tax_rule_matcher import match_tax_rules
    
    matched = match_tax_rules(transactions)
    
    with_sections = [t for t in matched if t.get('matched_section') and t['matched_section'] != 'NONE']
    
    print(f"✓ Matched {len(with_sections)} transactions to tax sections")
    print()
    
    if len(with_sections) == 0:
        print("❌ FAIL: No transactions matched to sections!")
        return None
    
    sections = {}
    for tx in with_sections:
        section = tx['matched_section']
        sections.setdefault(section, []).append(tx)
    
    print("Matched by section:")
    for section, txs in sections.items():
        total = sum(tx.get('debit_amount', 0) for tx in txs)
        print(f"  {section:10} → {len(txs)} transactions, ₹{total:,.0f}")
    
    print()
    return matched


def test_deduction_calculation(transactions):
    """Test deduction calculation"""
    print("=" * 60)
    print("TEST 4: DEDUCTION CALCULATION")
    print("=" * 60)
    
    from backend.agents.deduction_calculator import calculate_deductions
    
    report = calculate_deductions(transactions, upload_id=1)
    
    print(f"✓ Total Gross Deductions: ₹{report.total_gross_deductions:,.0f}")
    print(f"✓ Total Capped Deductions: ₹{report.total_capped_deductions:,.0f}")
    print(f"✓ Tax Saved @ 20%: ₹{report.estimated_tax_saved_20_percent:,.0f}")
    print(f"✓ Tax Saved @ 30%: ₹{report.estimated_tax_saved_30_percent:,.0f}")
    print(f"✓ Sections: {', '.join(report.sections_covered)}")
    print()
    
    if report.total_capped_deductions == 0:
        print("❌ FAIL: Zero deductions calculated!")
        return None
    
    print("Section summaries:")
    for ss in report.section_summaries:
        print(f"  {ss.section:10} → ₹{ss.total_deductible:>10,.0f} (capped: ₹{ss.capped_deductible:,.0f})")
    
    print()
    print("Line items (first 5):")
    for li in report.line_items[:5]:
        print(f"  {li.date} | {li.description[:35]:35} | {li.section:5} | ₹{li.deductible_amount:,.0f}")
    
    return report


def run_full_test():
    """Run complete pipeline test"""
    print("\n" + "=" * 60)
    print("FULL PIPELINE TEST - Tax Deduction Finder")
    print("=" * 60)
    print()
    
    # Step 1: OCR
    transactions = test_ocr_extraction()
    if not transactions:
        print("\n[FAIL] TEST FAILED: OCR extraction")
        return False
    
    # Step 2: Categorization
    categorized = test_categorization(transactions)
    if not categorized:
        print("\n[FAIL] TEST FAILED: Categorization")
        return False
    
    # Step 3: Tax Matching
    matched = test_tax_matching(categorized)
    if not matched:
        print("\n[FAIL] TEST FAILED: Tax matching")
        return False
    
    # Step 4: Deduction Calculation
    report = test_deduction_calculation(matched)
    if not report:
        print("\n[FAIL] TEST FAILED: Deduction calculation")
        return False
    
    # Final summary
    print("=" * 60)
    print("[PASS] ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("FINAL RESULTS:")
    print(f"  Transactions Processed: {len(transactions)}")
    print(f"  Tax-Relevant Found: {sum(1 for t in categorized if t.get('is_tax_relevant'))}")
    print(f"  Sections Matched: {len(report.sections_covered)}")
    print(f"  Total Deductions: Rs.{report.total_capped_deductions:,.0f}")
    print(f"  Tax Saved @ 20%: Rs.{report.estimated_tax_saved_20_percent:,.0f}")
    print(f"  Tax Saved @ 30%: Rs.{report.estimated_tax_saved_30_percent:,.0f}")
    print()
    print("Expected vs Actual:")
    print(f"  Expected deductions: Rs.2,05,000")
    print(f"  Actual deductions:   Rs.{report.total_capped_deductions:,.0f}")
    
    if abs(report.total_capped_deductions - 205000) < 1000:
        print("  [MATCH]!")
    else:
        print(f"  [DIFF]: Rs.{abs(report.total_capped_deductions - 205000):,.0f}")
    
    print()
    return True


if __name__ == "__main__":
    try:
        success = run_full_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
