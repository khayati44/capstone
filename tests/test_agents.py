"""
Tests for the 3-agent pipeline — 30 test cases.
"""

import pytest
from unittest.mock import patch, MagicMock


# ══════════════════════════════════════════════════════
# Agent 3 — DeductionCalculator (no external API) — 18 tests
# ══════════════════════════════════════════════════════

def test_calculate_deductions_empty_list():
    """Empty transactions → zero report."""
    from backend.agents.deduction_calculator import calculate_deductions
    report = calculate_deductions([], upload_id=1)
    assert report.total_gross_deductions == 0.0
    assert report.total_capped_deductions == 0.0
    assert report.sections_covered == []
    assert report.line_items == []


def test_calculate_deductions_no_matched_section():
    """Transactions with NONE section contribute nothing."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "Shopping",
         "debit_amount": 5000.0, "credit_amount": 0,
         "matched_section": "NONE", "deduction_percentage": 0.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert report.total_capped_deductions == 0.0


def test_calculate_deductions_80c_single_under_limit():
    """80C below ₹1,50,000 — full amount deductible."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "LIC Premium",
         "debit_amount": 50000.0, "credit_amount": 0,
         "matched_section": "80C", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert report.total_capped_deductions == pytest.approx(50000.0, rel=0.01)


def test_calculate_deductions_80c_cap_enforced():
    """80C aggregate capped at ₹1,50,000."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "LIC Premium",
         "debit_amount": 100000.0, "credit_amount": 0,
         "matched_section": "80C", "deduction_percentage": 100.0, "conditions": ""},
        {"id": 2, "date": "15/04/2024", "description": "PPF Contribution",
         "debit_amount": 80000.0, "credit_amount": 0,
         "matched_section": "80C", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert report.total_capped_deductions <= 150000.0


def test_calculate_deductions_80c_exact_limit():
    """80C exactly at ₹1,50,000 — should not be reduced."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "ELSS SIP",
         "debit_amount": 150000.0, "credit_amount": 0,
         "matched_section": "80C", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert report.total_capped_deductions == pytest.approx(150000.0, rel=0.01)


def test_calculate_deductions_80d_under_limit():
    """80D under ₹25,000 — full amount deductible."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "Health Insurance",
         "debit_amount": 15000.0, "credit_amount": 0,
         "matched_section": "80D", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert report.total_capped_deductions == pytest.approx(15000.0, rel=0.01)


def test_calculate_deductions_80d_cap_enforced():
    """80D capped at ₹25,000."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "Health Insurance",
         "debit_amount": 40000.0, "credit_amount": 0,
         "matched_section": "80D", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert report.total_capped_deductions <= 25000.0


def test_calculate_deductions_80e_no_cap():
    """80E has no upper limit."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "Education Loan Interest",
         "debit_amount": 200000.0, "credit_amount": 0,
         "matched_section": "80E", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert report.total_capped_deductions == pytest.approx(200000.0, rel=0.01)


def test_calculate_deductions_24b_cap_enforced():
    """24B (home loan interest) capped at ₹2,00,000."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "Home Loan Interest",
         "debit_amount": 300000.0, "credit_amount": 0,
         "matched_section": "24B", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert report.total_capped_deductions <= 200000.0


def test_calculate_deductions_80g_partial_percentage():
    """80G at 50% deduction — half of amount should be deductible."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "NGO Donation",
         "debit_amount": 10000.0, "credit_amount": 0,
         "matched_section": "80G", "deduction_percentage": 50.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert report.total_capped_deductions == pytest.approx(5000.0, rel=0.01)


def test_calculate_deductions_multiple_sections():
    """Multiple sections should each be capped independently."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "LIC Premium",
         "debit_amount": 50000.0, "credit_amount": 0,
         "matched_section": "80C", "deduction_percentage": 100.0, "conditions": ""},
        {"id": 2, "date": "01/04/2024", "description": "Health Ins",
         "debit_amount": 15000.0, "credit_amount": 0,
         "matched_section": "80D", "deduction_percentage": 100.0, "conditions": ""},
        {"id": 3, "date": "01/04/2024", "description": "Edu Loan Interest",
         "debit_amount": 30000.0, "credit_amount": 0,
         "matched_section": "80E", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert len(report.sections_covered) == 3
    assert "80C" in report.sections_covered
    assert "80D" in report.sections_covered
    assert "80E" in report.sections_covered


def test_calculate_deductions_tax_savings_20_percent():
    """Tax saved at 20% slab = 20% of capped deductions."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "LIC Premium",
         "debit_amount": 50000.0, "credit_amount": 0,
         "matched_section": "80C", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert report.estimated_tax_saved_20_percent == pytest.approx(
        report.total_capped_deductions * 0.20, rel=0.01
    )


def test_calculate_deductions_tax_savings_30_percent():
    """Tax saved at 30% slab = 30% of capped deductions."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "LIC Premium",
         "debit_amount": 50000.0, "credit_amount": 0,
         "matched_section": "80C", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert report.estimated_tax_saved_30_percent == pytest.approx(
        report.total_capped_deductions * 0.30, rel=0.01
    )


def test_deduction_report_to_dict_structure():
    """Report.to_dict() must have all required top-level keys."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "LIC",
         "debit_amount": 25000.0, "credit_amount": 0,
         "matched_section": "80C", "deduction_percentage": 100.0, "conditions": ""},
    ]
    d = calculate_deductions(transactions, upload_id=42).to_dict()
    for key in ["upload_id", "total_gross_deductions", "total_capped_deductions",
                "estimated_tax_saved_20_percent", "estimated_tax_saved_30_percent",
                "sections_covered", "line_items", "section_summaries"]:
        assert key in d, f"Missing key: {key}"


def test_deduction_report_upload_id_preserved():
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "PPF",
         "debit_amount": 10000.0, "credit_amount": 0,
         "matched_section": "80C", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=99)
    assert report.upload_id == 99
    assert report.to_dict()["upload_id"] == 99


def test_deduction_report_zero_amount_skipped():
    """Transactions with zero debit AND zero credit are skipped."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "Zero Tx",
         "debit_amount": 0.0, "credit_amount": 0.0,
         "matched_section": "80C", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert report.total_capped_deductions == 0.0


def test_deduction_section_summaries_count():
    """Section summaries should have one entry per unique matched section."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "LIC",
         "debit_amount": 20000.0, "credit_amount": 0,
         "matched_section": "80C", "deduction_percentage": 100.0, "conditions": ""},
        {"id": 2, "date": "15/04/2024", "description": "Health Ins",
         "debit_amount": 10000.0, "credit_amount": 0,
         "matched_section": "80D", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    sections_in_summary = [s.section for s in report.section_summaries]
    assert "80C" in sections_in_summary
    assert "80D" in sections_in_summary


def test_calculate_deductions_credit_amount_fallback():
    """If debit_amount is 0, credit_amount should be used."""
    from backend.agents.deduction_calculator import calculate_deductions
    transactions = [
        {"id": 1, "date": "01/04/2024", "description": "Refund to PPF",
         "debit_amount": 0.0, "credit_amount": 50000.0,
         "matched_section": "80C", "deduction_percentage": 100.0, "conditions": ""},
    ]
    report = calculate_deductions(transactions, upload_id=1)
    assert report.total_capped_deductions > 0


# ══════════════════════════════════════════════════════
# Orchestrator — 3 tests
# ══════════════════════════════════════════════════════

def test_orchestrator_empty_transactions():
    """Empty transactions → error status."""
    from backend.agents.orchestrator import run_pipeline
    result = run_pipeline([], upload_id=1)
    assert result["status"] == "error"


def test_orchestrator_returns_required_keys_on_error():
    from backend.agents.orchestrator import run_pipeline
    result = run_pipeline([], upload_id=5)
    assert "status" in result
    assert "message" in result
    assert "report" in result


def test_orchestrator_upload_id_passed_through():
    """upload_id should be in report on success (mocked agents)."""
    import json
    with patch("backend.agents.orchestrator.categorize_transactions") as mock_cat, \
         patch("backend.agents.orchestrator.match_tax_rules") as mock_match, \
         patch("backend.agents.orchestrator.calculate_deductions") as mock_calc:

        tx = [{"id": 1, "date": "01/04/2024", "description": "LIC",
               "debit_amount": 25000.0, "credit_amount": 0,
               "matched_section": "80C", "deduction_percentage": 100.0,
               "merchant_type": "Insurance", "likely_purpose": "LIC",
               "is_tax_relevant": True, "conditions": ""}]
        mock_cat.return_value = tx
        mock_match.return_value = tx

        from backend.agents.deduction_calculator import DeductionReport
        fake_report = DeductionReport(
            upload_id=7,
            total_gross_deductions=25000.0,
            total_capped_deductions=25000.0,
            estimated_tax_saved_20_percent=5000.0,
            estimated_tax_saved_30_percent=7500.0,
            sections_covered=["80C"],
            line_items=[],
            section_summaries=[],
        )
        mock_calc.return_value = fake_report

        from backend.agents.orchestrator import run_pipeline
        result = run_pipeline(tx, upload_id=7)
        assert result["status"] == "success"
        assert result["report"]["upload_id"] == 7


# ══════════════════════════════════════════════════════
# Agent 1 — TransactionCategorizer (mocked Groq) — 5 tests
# ══════════════════════════════════════════════════════

@patch("backend.agents.transaction_categorizer.Groq")
def test_categorize_transactions_tax_relevant_flag(mock_groq_cls):
    """Test Agent 1 sets is_tax_relevant correctly."""
    import json
    from backend.agents.transaction_categorizer import categorize_transactions

    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps([{
        "date": "01/04/2024", "description": "LIC PREMIUM",
        "debit_amount": 25000.0, "credit_amount": 0, "balance": None,
        "raw_text": "LIC PREMIUM",
        "merchant_type": "Insurance Company",
        "likely_purpose": "Life Insurance Premium",
        "is_tax_relevant": True,
    }])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_groq_cls.return_value = mock_client

    result = categorize_transactions([{
        "date": "01/04/2024", "description": "LIC PREMIUM",
        "debit_amount": 25000.0, "credit_amount": 0, "balance": None, "raw_text": "",
    }])
    assert len(result) == 1
    assert result[0]["is_tax_relevant"] is True
    assert result[0]["merchant_type"] == "Insurance Company"


@patch("backend.agents.transaction_categorizer.Groq")
def test_categorize_transactions_not_tax_relevant(mock_groq_cls):
    """Shopping transaction should not be tax relevant."""
    import json
    from backend.agents.transaction_categorizer import categorize_transactions

    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps([{
        "date": "01/04/2024", "description": "AMAZON SHOPPING",
        "debit_amount": 3500.0, "credit_amount": 0, "balance": None,
        "raw_text": "AMAZON SHOPPING",
        "merchant_type": "E-Commerce",
        "likely_purpose": "Online Shopping",
        "is_tax_relevant": False,
    }])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_groq_cls.return_value = mock_client

    result = categorize_transactions([{
        "date": "01/04/2024", "description": "AMAZON SHOPPING",
        "debit_amount": 3500.0, "credit_amount": 0, "balance": None, "raw_text": "",
    }])
    assert result[0]["is_tax_relevant"] is False


@patch("backend.agents.transaction_categorizer.Groq")
def test_categorize_transactions_empty_list(mock_groq_cls):
    """Empty input should return empty list without calling Groq."""
    from backend.agents.transaction_categorizer import categorize_transactions
    result = categorize_transactions([])
    assert result == []
    mock_groq_cls.assert_not_called()


@patch("backend.agents.transaction_categorizer.Groq")
def test_categorize_transactions_preserves_original_fields(mock_groq_cls):
    """Original transaction fields must be preserved in output."""
    import json
    from backend.agents.transaction_categorizer import categorize_transactions

    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps([{
        "date": "15/05/2024", "description": "PPF DEPOSIT",
        "debit_amount": 10000.0, "credit_amount": 0, "balance": 90000.0,
        "raw_text": "PPF DEPOSIT",
        "merchant_type": "Government Savings",
        "likely_purpose": "PPF Contribution",
        "is_tax_relevant": True,
    }])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_groq_cls.return_value = mock_client

    orig = {"date": "15/05/2024", "description": "PPF DEPOSIT",
            "debit_amount": 10000.0, "credit_amount": 0,
            "balance": 90000.0, "raw_text": "PPF DEPOSIT"}
    result = categorize_transactions([orig])
    assert result[0]["date"] == "15/05/2024"
    assert result[0]["debit_amount"] == 10000.0


@patch("backend.agents.transaction_categorizer.Groq")
def test_categorize_transactions_json_parse_error_fallback(mock_groq_cls):
    """If LLM returns invalid JSON, original transactions should still be returned."""
    from backend.agents.transaction_categorizer import categorize_transactions

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "This is NOT valid JSON at all!!"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_groq_cls.return_value = mock_client

    transactions = [{
        "date": "01/04/2024", "description": "LIC PREMIUM",
        "debit_amount": 25000.0, "credit_amount": 0, "balance": None, "raw_text": "",
    }]
    result = categorize_transactions(transactions)
    # Should not crash and should return the transaction with default values
    assert len(result) == 1
    assert "merchant_type" in result[0]
    assert "is_tax_relevant" in result[0]


# ══════════════════════════════════════════════════════
# Auth service — 4 tests (pure logic, no API)
# ══════════════════════════════════════════════════════

def test_password_hash_and_verify():
    """Argon2 hash + verify should work correctly."""
    from backend.auth.service import hash_password, verify_password
    plain = "MySecurePass123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True


def test_wrong_password_does_not_verify():
    from backend.auth.service import hash_password, verify_password
    hashed = hash_password("correct_password")
    assert verify_password("wrong_password", hashed) is False


def test_jwt_create_and_decode():
    from backend.auth.service import create_access_token, decode_access_token
    token = create_access_token({"sub": "42", "email": "test@example.com"})
    data = decode_access_token(token)
    assert data is not None
    assert data.user_id == 42
    assert data.email == "test@example.com"


def test_jwt_invalid_token_returns_none():
    from backend.auth.service import decode_access_token
    result = decode_access_token("this.is.not.a.valid.jwt")
    assert result is None
