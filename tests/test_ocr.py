"""
Tests for OCR pipeline — 22 test cases.
"""

import pytest
from unittest.mock import patch, MagicMock


# ══════════════════════════════════════════════════════
# _clean_amount — 7 tests
# ══════════════════════════════════════════════════════

def test_clean_amount_basic():
    from backend.ocr.extractor import _clean_amount
    assert _clean_amount("1000.00") == 1000.0


def test_clean_amount_with_rupee_symbol():
    from backend.ocr.extractor import _clean_amount
    assert _clean_amount("₹1,50,000") == 150000.0


def test_clean_amount_with_commas():
    from backend.ocr.extractor import _clean_amount
    assert _clean_amount("10,500.50") == 10500.50


def test_clean_amount_empty_string():
    from backend.ocr.extractor import _clean_amount
    assert _clean_amount("") == 0.0


def test_clean_amount_non_numeric():
    from backend.ocr.extractor import _clean_amount
    assert _clean_amount("abc") == 0.0


def test_clean_amount_spaces_and_commas():
    from backend.ocr.extractor import _clean_amount
    assert _clean_amount("  75,000  ") == 75000.0


def test_clean_amount_decimal_only():
    from backend.ocr.extractor import _clean_amount
    assert _clean_amount("500.75") == pytest.approx(500.75)


# ══════════════════════════════════════════════════════
# _detect_bank_format — 6 tests
# ══════════════════════════════════════════════════════

def test_detect_bank_hdfc():
    from backend.ocr.extractor import _detect_bank_format
    assert _detect_bank_format("HDFC BANK STATEMENT") == "HDFC"


def test_detect_bank_sbi_full():
    from backend.ocr.extractor import _detect_bank_format
    assert _detect_bank_format("STATE BANK OF INDIA") == "SBI"


def test_detect_bank_sbi_abbreviation():
    from backend.ocr.extractor import _detect_bank_format
    assert _detect_bank_format("SBI NETBANKING") == "SBI"


def test_detect_bank_icici():
    from backend.ocr.extractor import _detect_bank_format
    assert _detect_bank_format("ICICI BANK LIMITED") == "ICICI"


def test_detect_bank_axis():
    from backend.ocr.extractor import _detect_bank_format
    assert _detect_bank_format("AXIS BANK STATEMENT") == "AXIS"


def test_detect_bank_unknown():
    from backend.ocr.extractor import _detect_bank_format
    assert _detect_bank_format("SOME RANDOM TEXT WITH NO BANK") == "UNKNOWN"


# ══════════════════════════════════════════════════════
# _parse_date — 5 tests
# ══════════════════════════════════════════════════════

def test_parse_date_dd_mm_yyyy_slash():
    from backend.ocr.extractor import _parse_date
    assert _parse_date("Transaction on 01/04/2024") == "01/04/2024"


def test_parse_date_dd_mm_yyyy_dash():
    from backend.ocr.extractor import _parse_date
    assert _parse_date("15-06-2024 NEFT") == "15-06-2024"


def test_parse_date_dd_dot_mm_dot_yyyy():
    from backend.ocr.extractor import _parse_date
    assert _parse_date("Payment 21.03.2024") == "21.03.2024"


def test_parse_date_no_date_in_text():
    from backend.ocr.extractor import _parse_date
    assert _parse_date("no date here at all") is None


def test_parse_date_empty_string():
    from backend.ocr.extractor import _parse_date
    assert _parse_date("") is None


# ══════════════════════════════════════════════════════
# _parse_transactions_from_text — 4 tests
# ══════════════════════════════════════════════════════

def test_parse_transactions_empty_text():
    from backend.ocr.extractor import _parse_transactions_from_text
    assert _parse_transactions_from_text("", "HDFC") == []


def test_parse_transactions_returns_parsed_transaction_type():
    from backend.ocr.extractor import _parse_transactions_from_text, ParsedTransaction
    sample = "01/04/2024 TEST PAYMENT 1000.00 Dr 50000.00"
    txns = _parse_transactions_from_text(sample, "HDFC")
    for t in txns:
        assert isinstance(t, ParsedTransaction)


def test_parse_transactions_amounts_non_negative():
    from backend.ocr.extractor import _parse_transactions_from_text
    sample = (
        "01/04/2024 LIC INSURANCE 25000.00 Dr 125000.00\n"
        "15/04/2024 HDFC HEALTH 8500.00 Dr 116500.00"
    )
    txns = _parse_transactions_from_text(sample, "HDFC")
    for t in txns:
        assert t.debit_amount >= 0
        assert t.credit_amount >= 0


def test_parse_transactions_no_duplicate_signatures():
    from backend.ocr.extractor import _parse_transactions_from_text
    # Same line repeated — deduplication should kick in
    sample = (
        "01/04/2024 LIC PREMIUM PAYMENT 25000.00 Dr 125000.00\n"
        "01/04/2024 LIC PREMIUM PAYMENT 25000.00 Dr 125000.00"
    )
    txns = _parse_transactions_from_text(sample, "HDFC")
    sigs = [(t.date, t.description, t.debit_amount) for t in txns]
    assert len(sigs) == len(set(sigs))
