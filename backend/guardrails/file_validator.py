"""
Guardrail 1 — File Upload Validator
Enforces strict rules on uploaded PDF files before any processing begins.
Checks: extension, MIME type, magic bytes, file size, malicious filenames.
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# PDF magic bytes (first 4 bytes of every valid PDF)
PDF_MAGIC_BYTES = b"%PDF"

# Dangerous filename patterns (path traversal, null bytes, shell injection)
DANGEROUS_FILENAME_PATTERNS = [
    r"\.\./",          # Path traversal
    r"\.\.\\"  ,       # Windows path traversal
    r"\x00",           # Null byte injection
    r"[;&|`$]",        # Shell injection characters
    r"<|>",            # HTML/XML injection
]

MAX_FILENAME_LENGTH = 255
ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIME_TYPES = {"application/pdf", "application/x-pdf", "binary/octet-stream"}


@dataclass
class FileValidationResult:
    is_valid: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    details: Optional[dict] = None


def validate_upload(
    filename: str,
    content_type: str,
    file_bytes: bytes,
    max_size_bytes: int = 10 * 1024 * 1024,
) -> FileValidationResult:
    """
    Run all file upload guardrails in sequence.
    Returns FileValidationResult — check is_valid before processing.
    """
    checks = [
        _check_filename_safety,
        _check_extension,
        _check_file_size,
        _check_not_empty,
        _check_pdf_magic_bytes,
        _check_not_executable,
    ]

    for check in checks:
        result = check(filename=filename, content_type=content_type,
                       file_bytes=file_bytes, max_size_bytes=max_size_bytes)
        if not result.is_valid:
            logger.warning(
                f"[GUARDRAIL:upload] BLOCKED — {result.error_code} — "
                f"file='{filename}' reason='{result.error_message}'"
            )
            return result

    logger.info(f"[GUARDRAIL:upload] PASSED — file='{filename}' size={len(file_bytes)} bytes")
    return FileValidationResult(is_valid=True)


# ── Individual checks ─────────────────────────────────────────────────────────

def _check_filename_safety(filename: str, **_) -> FileValidationResult:
    """Reject dangerous filenames (path traversal, shell injection, null bytes)."""
    if not filename:
        return FileValidationResult(
            is_valid=False,
            error_code="MISSING_FILENAME",
            error_message="Filename is required",
        )
    if len(filename) > MAX_FILENAME_LENGTH:
        return FileValidationResult(
            is_valid=False,
            error_code="FILENAME_TOO_LONG",
            error_message=f"Filename exceeds {MAX_FILENAME_LENGTH} characters",
        )
    for pattern in DANGEROUS_FILENAME_PATTERNS:
        if re.search(pattern, filename):
            return FileValidationResult(
                is_valid=False,
                error_code="DANGEROUS_FILENAME",
                error_message="Filename contains potentially dangerous characters",
                details={"pattern_matched": pattern},
            )
    return FileValidationResult(is_valid=True)


def _check_extension(filename: str, **_) -> FileValidationResult:
    """Only .pdf extension is permitted."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return FileValidationResult(
            is_valid=False,
            error_code="INVALID_EXTENSION",
            error_message=f"Only PDF files accepted. Got: '{ext or 'no extension'}'",
            details={"received_extension": ext},
        )
    return FileValidationResult(is_valid=True)


def _check_file_size(file_bytes: bytes, max_size_bytes: int, **_) -> FileValidationResult:
    """Enforce maximum file size limit."""
    size = len(file_bytes)
    if size > max_size_bytes:
        return FileValidationResult(
            is_valid=False,
            error_code="FILE_TOO_LARGE",
            error_message=f"File size {size / (1024*1024):.1f}MB exceeds limit of {max_size_bytes / (1024*1024):.0f}MB",
            details={"size_bytes": size, "limit_bytes": max_size_bytes},
        )
    return FileValidationResult(is_valid=True)


def _check_not_empty(file_bytes: bytes, **_) -> FileValidationResult:
    """Reject empty or near-empty files."""
    if len(file_bytes) < 100:
        return FileValidationResult(
            is_valid=False,
            error_code="FILE_EMPTY",
            error_message="File appears to be empty or corrupted (< 100 bytes)",
            details={"size_bytes": len(file_bytes)},
        )
    return FileValidationResult(is_valid=True)


def _check_pdf_magic_bytes(file_bytes: bytes, **_) -> FileValidationResult:
    """Verify PDF magic bytes (%PDF) — prevents disguised non-PDF files."""
    if not file_bytes.startswith(PDF_MAGIC_BYTES):
        actual = file_bytes[:8].hex()
        return FileValidationResult(
            is_valid=False,
            error_code="INVALID_PDF_MAGIC_BYTES",
            error_message="File does not appear to be a valid PDF (magic bytes check failed)",
            details={"expected_hex": PDF_MAGIC_BYTES.hex(), "got_hex": actual},
        )
    return FileValidationResult(is_valid=True)


def _check_not_executable(file_bytes: bytes, filename: str, **_) -> FileValidationResult:
    """Detect common executable/script magic bytes to block malware uploads."""
    EXECUTABLE_SIGNATURES = {
        b"MZ":              "Windows PE executable",
        b"\x7fELF":         "Linux ELF executable",
        b"\xca\xfe\xba\xbe": "macOS Mach-O executable",
        b"PK\x03\x04":      "ZIP archive (possible macro-enabled Office file)",
        b"<html":           "HTML file",
        b"<HTML":           "HTML file",
        b"#!/":             "Shell script",
        b"\xff\xfe":        "UTF-16 encoded file (suspicious)",
    }
    for sig, description in EXECUTABLE_SIGNATURES.items():
        if file_bytes.startswith(sig):
            return FileValidationResult(
                is_valid=False,
                error_code="EXECUTABLE_CONTENT_DETECTED",
                error_message=f"File content matches '{description}' — not a PDF",
                details={"detected_type": description, "filename": filename},
            )
    return FileValidationResult(is_valid=True)
