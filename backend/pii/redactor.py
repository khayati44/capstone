"""
PII Redaction using Microsoft Presidio.
Redacts account numbers, card numbers, phone numbers, emails, etc.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    logger.warning("Presidio not available — PII redaction disabled")


_analyzer: Optional[object] = None
_anonymizer: Optional[object] = None


def _get_engines():
    global _analyzer, _anonymizer
    if _analyzer is None and PRESIDIO_AVAILABLE:
        try:
            _analyzer = AnalyzerEngine()
            _anonymizer = AnonymizerEngine()
        except Exception as e:
            logger.error(f"Failed to initialize Presidio engines: {e}")
    return _analyzer, _anonymizer


def _regex_redact(text: str) -> str:
    """Regex-based fallback PII redaction for Indian banking context."""
    # Account numbers (10-18 digits)
    text = re.sub(r"\b\d{10,18}\b", "[ACCOUNT_REDACTED]", text)
    # Card numbers (16 digits with optional spaces/dashes)
    text = re.sub(r"\b(?:\d[ -]?){15}\d\b", "[CARD_REDACTED]", text)
    # Indian mobile numbers
    text = re.sub(r"\b[6-9]\d{9}\b", "[PHONE_REDACTED]", text)
    # Email addresses
    text = re.sub(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", "[EMAIL_REDACTED]", text)
    # PAN numbers (Indian)
    text = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[PAN_REDACTED]", text)
    # Aadhaar numbers
    text = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[AADHAAR_REDACTED]", text)
    return text


def redact_pii(text: str) -> str:
    """
    Redact PII from text using Presidio + regex fallback.
    Returns redacted text safe for storage.
    """
    if not text:
        return text

    analyzer, anonymizer = _get_engines()

    if analyzer and anonymizer:
        try:
            entities = [
                "CREDIT_CARD", "PHONE_NUMBER", "EMAIL_ADDRESS",
                "IBAN_CODE", "US_BANK_NUMBER", "PERSON",
            ]
            results = analyzer.analyze(text=text, entities=entities, language="en")
            anonymized = anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[CARD_REDACTED]"}),
                    "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE_REDACTED]"}),
                    "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL_REDACTED]"}),
                    "IBAN_CODE": OperatorConfig("replace", {"new_value": "[IBAN_REDACTED]"}),
                    "US_BANK_NUMBER": OperatorConfig("replace", {"new_value": "[ACCOUNT_REDACTED]"}),
                    "PERSON": OperatorConfig("replace", {"new_value": "[NAME_REDACTED]"}),
                },
            )
            text = anonymized.text
        except Exception as e:
            logger.warning(f"Presidio redaction failed, using regex fallback: {e}")

    # Always apply regex for Indian-specific patterns
    text = _regex_redact(text)
    return text
