#!/usr/bin/env python3
"""Debug: Show exactly what text is extracted from PDF"""

import io

# Read the uploaded PDF
with open("/app/uploads/user1_sample_bank_statement.pdf", "rb") as f:
    pdf_bytes = f.read()

print("Testing different extraction methods:")
print("=" * 60)

# Try pdfminer
try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    text1 = pdfminer_extract(io.BytesIO(pdf_bytes))
    print(f"\n1. PDFMINER ({len(text1)} chars):")
    print(text1[:800])
except Exception as e:
    print(f"\n1. PDFMINER FAILED: {e}")

# Try PyMuPDF
try:
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text2 = ""
    for page in doc:
        text2 += page.get_text("text") + "\n"
    doc.close()
    print(f"\n2. PyMuPDF ({len(text2)} chars):")
    print(text2[:800])
except Exception as e:
    print(f"\n2. PyMuPDF FAILED: {e}")

# Try PyMuPDF blocks
try:
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text3 = ""
    for page in doc:
        blocks = page.get_text("blocks")
        for block in blocks:
            if len(block) >= 5:  # block[4] is the text
                text3 += block[4] + "\n"
    doc.close()
    print(f"\n3. PyMuPDF BLOCKS ({len(text3)} chars):")
    print(text3[:800])
except Exception as e:
    print(f"\n3. PyMuPDF BLOCKS FAILED: {e}")

# Try PyMuPDF dict
try:
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text4 = ""
    for page in doc:
        text4 += page.get_text("dict")
        text4 = str(text4)
    doc.close()
    print(f"\n4. PyMuPDF DICT ({len(text4)} chars):")
    print(text4[:800])
except Exception as e:
    print(f"\n4. PyMuPDF DICT FAILED: {e}")
