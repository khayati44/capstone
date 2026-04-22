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
    
    # Step 1: split text into lines
    raw_lines = [l.rstrip() for l in text.splitlines()]
    
    # Step 2: Check if we have a single concatenated line with many dates
    date_split_re = re.compile(r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,}[''`]?\s*\d{4})")
    all_date_matches = list(date_split_re.finditer(text))
    
    if len(raw_lines) == 1 and len(all_date_matches) > 3:
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
            desc = re.sub(date_split_re, "", part).strip()
            amt_tokens = re.findall(r"[\d,]+(?:\.\d+)?", part)
            debit = credit = balance = 0.0
            drcr = None
            m_drcr = re.search(r"\b(DR|CR|DEBIT|CREDIT)\b", part, flags=re.IGNORECASE)
            if m_drcr:
                drcr = m_drcr.group(1).upper()
            
            if len(amt_tokens) == 1:
                val = _clean_amount(amt_tokens[0])
                if drcr == "CR" or re.search(r"CREDIT", part, flags=re.IGNORECASE):
                    credit = val
                else:
                    debit = val
            elif len(amt_tokens) == 2:
                debit = _clean_amount(amt_tokens[0])
                balance = _clean_amount(amt_tokens[1])
            elif len(amt_tokens) >= 3:
                debit = _clean_amount(amt_tokens[0])
                credit = _clean_amount(amt_tokens[1])
                balance = _clean_amount(amt_tokens[2])
            
            tx = ParsedTransaction(
                date=date_str,
                description=desc or part,
                debit_amount=debit,
                credit_amount=credit,
                balance=balance,
                raw_text=part,
            )
            
            sig = f"{tx.date}_{(tx.description or '')[:40]}_{tx.debit_amount}_{tx.credit_amount}"
            if sig not in parsed_set:
                parsed_set.add(sig)
                transactions.append(tx)
    
    return transactions


def extract_transactions_from_pdf(pdf_bytes: bytes) -> tuple[list[ParsedTransaction], str, str]:
    """Main entry point for PDF extraction."""
    transactions = []
    extracted_text = ""
    
    # Try pdfminer first
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        extracted_text = pdfminer_extract(io.BytesIO(pdf_bytes))
        logger.info("pdfminer extraction succeeded")
    except Exception as e:
        logger.warning(f"pdfminer extraction failed: {e}")
    
    # Try PyMuPDF fallback
    if not extracted_text or len(extracted_text) < 50:
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                extracted_text += page.get_text("text") + "\n"
            doc.close()
            logger.info("PyMuPDF extraction succeeded")
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")
    
    # Parse transactions from text
    if extracted_text and len(extracted_text) > 50:
        transactions = _parse_transactions_from_text(extracted_text, "SBI")
        logger.info(f"Parsed {len(transactions)} transactions from text extraction")
    
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
