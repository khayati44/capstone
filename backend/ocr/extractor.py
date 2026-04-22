"""
OCR Pipeline for Bank Statement PDFs.
Supports HDFC, SBI, ICICI formats via pytesseract + EasyOCR fallback.
"""

import io
import re
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not available")

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract/Pillow not available")

try:
    import easyocr
    EASYOCR_AVAILABLE = True
    _easyocr_reader = None
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("easyocr not available")


@dataclass
class ParsedTransaction:
    date: Optional[str] = None
    description: Optional[str] = None
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    balance: Optional[float] = None
    raw_text: Optional[str] = None


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None and EASYOCR_AVAILABLE:
        _easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _easyocr_reader


def _ocr_image_tesseract(image) -> tuple[str, float]:
    """Run pytesseract on a PIL image, return (text, avg_confidence)."""
    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        text = pytesseract.image_to_string(image, config="--psm 6")
        confidences = [int(c) for c in data.get("conf", []) if str(c).isdigit() and int(c) >= 0]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return text, avg_conf
    except Exception as e:
        logger.error(f"Tesseract OCR error: {e}")
        return "", 0.0


def _ocr_image_easyocr(image) -> str:
    """Run EasyOCR on a PIL image, return extracted text."""
    try:
        reader = _get_easyocr_reader()
        if reader is None:
            return ""
        import numpy as np
        img_array = np.array(image)
        results = reader.readtext(img_array, detail=0, paragraph=True)
        return "\n".join(results)
    except Exception as e:
        logger.error(f"EasyOCR error: {e}")
        return ""


def _preprocess_image(image):
    """Apply preprocessing steps to improve OCR: grayscale, median filter, autocontrast."""
    try:
        img = image.convert("L")
        try:
            from PIL import ImageFilter, ImageOps
            img = img.filter(ImageFilter.MedianFilter(size=3))
            img = ImageOps.autocontrast(img)
        except Exception:
            pass
        return img
    except Exception as e:
        logger.debug(f"Image preprocessing failed: {e}")
        return image


def _clean_amount(raw: str) -> float:
    """Parse Indian currency string to float."""
    if not raw:
        return 0.0
    cleaned = re.sub(r"[₹,\s]", "", raw.strip())
    cleaned = re.sub(r"[^\d.]", "", cleaned)
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def _parse_date(raw: str) -> Optional[str]:
    """Try to parse various date formats found in Indian bank statements."""
    date_patterns = [
        r"\d{2}/\d{2}/\d{4}",
        r"\d{2}-\d{2}-\d{4}",
        r"\d{2}\s+\w{3}\s+\d{4}",
        r"\d{1,2}[-\/.][A-Za-z]{3}[-\/.]\ d{2,4}",
        r"\d{1,2}[-\/.][A-Za-z]{3}\s+\d{4}",
        r"\d{4}-\d{2}-\d{2}",
        r"\d{2}\.\d{2}\.\d{4}",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, raw)
        if match:
            return match.group(0)
    return None


def _is_line_start_of_tx(line: str) -> bool:
    """Check if line starts with a date."""
    if not line or len(line.strip()) < 3:
        return False
    s = line.strip()
    if re.match(r"^\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}", s):
        return True
    if re.match(r"^\d{1,2}\s+[A-Za-z]{3,}\s+\d{4}", s):
        return True
    if re.match(r"^\d{1,2}[-\/.][A-Za-z]{3}[-\/.]\ d{2,4}", s):
        return True
    return False


def _parse_transactions_from_text(text: str, bank_name: str) -> list[ParsedTransaction]:
    """Parse transactions from extracted text with improved multi-date splitting."""
    transactions = []
    
    logger.info(f"Parsing text with {len(text)} characters, {len(text.splitlines())} lines")
    
    # Step 1: split text into lines
    raw_lines = [l.rstrip() for l in text.splitlines()]
    
    # Log first few lines for debugging
    logger.info(f"First 5 lines: {raw_lines[:5]}")
    
    # Step 2: Enhanced date pattern that matches our generated PDF format
    date_split_re = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,}[''`]?\s*\d{4})")
    all_date_matches = list(date_split_re.finditer(text))
    
    logger.info(f"Found {len(all_date_matches)} date matches in text")
    
    # Step 3: Try to detect if this is a table-based format
    # Look for multiple amounts on the same line (typical of bank statements)
    table_format = False
    multiline_table = False
    
    # Check if dates and descriptions are on separate lines (multi-line table)
    date_lines = [i for i, line in enumerate(raw_lines) if date_split_re.search(line)]
    if len(date_lines) >= 3:
        # Check if there are lines between dates (descriptions/amounts)
        if date_lines[0] + 1 < date_lines[1]:
            multiline_table = True
            logger.info("Detected multi-line table format")
    
    if multiline_table:
        # Parse multi-line format: each transaction spans multiple lines
        # Format: Date\nDescription\nAmounts
        lines = []
        i = 0
        while i < len(raw_lines):
            line = raw_lines[i].strip()
            if not line or re.search(r"(date|description|debit|credit|balance|particulars|transaction|total|closing)", line, re.IGNORECASE):
                i += 1
                continue
            
            # Check if this line has a date
            if date_split_re.search(line):
                # Combine this line with next 1-2 lines
                combined = line
                for j in range(1, 3):
                    if i + j < len(raw_lines):
                        next_line = raw_lines[i + j].strip()
                        if next_line and not date_split_re.search(next_line):
                            combined += " " + next_line
                        else:
                            break
                lines.append(combined)
                i += max(j, 1)
            else:
                i += 1
    elif table_format:
        logger.info("Detected table-based format, using line-by-line parsing")
        lines = raw_lines
    elif len(raw_lines) == 1 and len(all_date_matches) > 3:
        # Split by dates globally
        lines = []
        for i, m in enumerate(all_date_matches):
            start = m.start()
            end = all_date_matches[i + 1].start() if i + 1 < len(all_date_matches) else len(text)
            part = text[start:end].strip()
            if part:
                lines.append(part)
    else:
        # Normal line merging
        lines = []
        current = ""
        for l in raw_lines:
            if not l:
                continue
            if _is_line_start_of_tx(l):
                if current:
                    lines.append(current)
                current = l.strip()
            else:
                if current:
                    current = f"{current} {l.strip()}"
                else:
                    current = l.strip()
        if current:
            lines.append(current)
    
    # Step 3: Parse each line
    parsed_set = set()
    
    for line in lines:
        # Skip header lines
        if re.search(r"(date|description|debit|credit|balance|particulars|transaction)", line, re.IGNORECASE):
            continue
        if not line.strip() or len(line.strip()) < 5:
            continue
            
        parts = []
        matches = list(date_split_re.finditer(line))
        if len(matches) <= 1:
            parts = [line]
        else:
            for i, m in enumerate(matches):
                start = m.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
                part = line[start:end].strip()
                if part:
                    parts.append(part)
        
        for part in parts:
            date_str = _parse_date(part) or ""
            if not date_str:
                # If no date found, skip this part
                continue
            
            # Remove date from the line to get the rest
            remainder = part.replace(date_str, "", 1).strip()
            
            # Find amounts - handle formats with spaces: "25,000.00" or "25, 000.00" or "30 , 000.00"
            # First normalize: remove spaces around commas and between digits
            normalized = re.sub(r'(\d)\s+,\s*(\d)', r'\1,\2', remainder)  # "30 , 000" -> "30,000"
            normalized = re.sub(r'(\d)\s+(\d)', r'\1\2', normalized)  # "30 000" -> "30000"
            
            # Now extract amounts with pattern
            amount_pattern = r"(?:Rs\.\s*|₹\s*)?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
            amounts = re.findall(amount_pattern, normalized)
            
            # Clean and validate amounts
            valid_amounts = []
            for amt in amounts:
                clean_val = _clean_amount(amt)
                # Skip if it looks like a year or is too small
                if 1900 <= clean_val <= 2100:
                    continue
                if clean_val > 0:
                    valid_amounts.append(clean_val)
            
            # Extract description - everything before the first amount
            desc = remainder
            if amounts:
                # Find position of first amount in the remainder
                first_amt_pos = remainder.find(amounts[0])
                if first_amt_pos > 0:
                    desc = remainder[:first_amt_pos].strip()
            
            # Clean up description
            desc = re.sub(r"\s+", " ", desc).strip()
            desc = desc.replace("-", " ").strip()
            
            # Parse amounts based on count
            debit = credit = balance = 0.0
            
            if len(valid_amounts) >= 1:
                debit = valid_amounts[0]  # First amount is usually debit
            if len(valid_amounts) >= 2:
                balance = valid_amounts[-1]  # Last amount is usually balance
            if len(valid_amounts) >= 3:
                credit = valid_amounts[1]  # Middle amount might be credit
                balance = valid_amounts[2]
            
            # Require minimum data: date and at least one amount
            if not date_str or (debit == 0 and credit == 0):
                logger.debug(f"Skipping invalid transaction: date={date_str}, debit={debit}, credit={credit}")
                continue
            
            # Use a reasonable description
            if not desc or len(desc) < 2:
                desc = remainder[:100]  # Fallback to remainder
                
            tx = ParsedTransaction(
                date=date_str,
                description=desc,
                debit_amount=debit,
                credit_amount=credit,
                balance=balance,
                raw_text=part,
            )
            
            sig = f"{tx.date}_{(tx.description or '')[:40]}_{tx.debit_amount}_{tx.credit_amount}"
            if sig not in parsed_set:
                parsed_set.add(sig)
                transactions.append(tx)
                logger.info(f"✓ Parsed TX: {date_str} | {desc[:40]} | ₹{debit}")
    
    logger.info(f"Parsing complete: {len(transactions)} transactions extracted")
    return transactions


def extract_transactions_from_pdf(pdf_bytes: bytes) -> tuple[list[ParsedTransaction], str, str]:
    """Main entry point for PDF extraction."""
    transactions = []
    extracted_text = ""
    
    # Try PyMuPDF FIRST with blocks method (better for tables)
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            # Use blocks method for better table extraction
            blocks = page.get_text("blocks")
            for block in blocks:
                if len(block) >= 5:  # block[4] contains the text
                    extracted_text += block[4] + "\n"
        doc.close()
        logger.info(f"PyMuPDF extraction succeeded ({len(extracted_text)} chars)")
    except Exception as e:
        logger.warning(f"PyMuPDF extraction failed: {e}")
    
    # Try pdfminer fallback
    if not extracted_text or len(extracted_text) < 50:
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract
            extracted_text = pdfminer_extract(io.BytesIO(pdf_bytes))
            logger.info(f"pdfminer extraction succeeded ({len(extracted_text)} chars)")
        except Exception as e:
            logger.warning(f"pdfminer extraction failed: {e}")
    
    # Parse transactions from text
    if extracted_text and len(extracted_text) > 50:
        transactions = _parse_transactions_from_text(extracted_text, "SBI")
        logger.info(f"Parsed {len(transactions)} transactions from text extraction")
        
        # Log sample transactions for debugging
        for i, tx in enumerate(transactions[:3]):
            logger.info(f"  TX{i+1}: date={tx.date}, desc='{tx.description[:50] if tx.description else 'N/A'}', debit={tx.debit_amount}")
    
    # Image-based OCR fallback
    if not transactions and PDF2IMAGE_AVAILABLE and TESSERACT_AVAILABLE:
        logger.info("Attempting image-based OCR extraction...")
        try:
            images = convert_from_bytes(pdf_bytes, dpi=300)
            all_ocr_text = ""
            for i, img in enumerate(images):
                preprocessed = _preprocess_image(img)
                text, conf = _ocr_image_tesseract(preprocessed)
                logger.info(f"Page {i+1} OCR confidence: {conf:.2f}%")
                
                if conf < 60 and EASYOCR_AVAILABLE:
                    logger.info(f"Low confidence, trying EasyOCR for page {i+1}")
                    text2 = _ocr_image_easyocr(preprocessed)
                    if len(text2) > len(text):
                        text = text2
                
                all_ocr_text += text + "\n"
            
            if all_ocr_text:
                transactions = _parse_transactions_from_text(all_ocr_text, "SBI")
                extracted_text = all_ocr_text
                logger.info(f"Parsed {len(transactions)} transactions from OCR")
        except Exception as e:
            logger.error(f"Image-based OCR failed: {e}")
    
    logger.info(f"Final: extracted {len(transactions)} transactions")
    return transactions, extracted_text or "", "SBI"
