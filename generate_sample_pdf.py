"""
Generate a sample bank statement PDF with tax-relevant transactions.
Run: python generate_sample_pdf.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from datetime import datetime

# Sample transactions with tax-relevant items
transactions = [
    ["2024-01-15", "LIC Premium Payment - Policy 123456", "25,000.00", "", "75,000.00"],
    ["2024-02-10", "HDFC Life Insurance Premium - Annual", "30,000.00", "", "45,000.00"],
    ["2024-03-05", "PPF Contribution - SBI Account", "50,000.00", "", "-5,000.00"],
    ["2024-04-12", "School Tuition Fee - ABC International School", "40,000.00", "", "-45,000.00"],
    ["2024-05-20", "Home Loan EMI - HDFC Bank", "35,000.00", "", "-80,000.00"],
    ["2024-06-08", "Donation to PM Cares Fund", "10,000.00", "", "-90,000.00"],
    ["2024-07-15", "Health Insurance Premium - Star Health", "15,000.00", "", "-105,000.00"],
    ["2024-08-22", "NPS Contribution - Tier 1 Account", "20,000.00", "", "-125,000.00"],
    ["2024-09-10", "Education Loan Interest - SBI", "12,000.00", "", "-137,000.00"],
    ["2024-10-05", "ELSS Mutual Fund Investment - SIP", "25,000.00", "", "-162,000.00"],
]

def create_bank_statement_pdf(filename="sample_bank_statement.pdf"):
    """Create a realistic bank statement PDF"""
    
    # Create PDF
    doc = SimpleDocTemplate(filename, pagesize=A4, 
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#003366'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Bank header
    elements.append(Paragraph("SAMPLE BANK", title_style))
    elements.append(Paragraph("Account Statement", styles['Heading2']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Account info
    account_info = [
        ["Account Holder:", "John Doe"],
        ["Account Number:", "XXXX-XXXX-1234"],
        ["Statement Period:", "01-Jan-2024 to 31-Oct-2024"],
        ["Branch:", "Mumbai Main Branch"],
    ]
    
    info_table = Table(account_info, colWidths=[2*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Transaction table header
    elements.append(Paragraph("Transaction Details", styles['Heading3']))
    elements.append(Spacer(1, 0.1*inch))
    
    # Prepare transaction data
    data = [["Date", "Description", "Debit (₹)", "Credit (₹)", "Balance (₹)"]]
    data.extend(transactions)
    
    # Create table
    col_widths = [1.2*inch, 3.2*inch, 1.0*inch, 1.0*inch, 1.2*inch]
    transaction_table = Table(data, colWidths=col_widths, repeatRows=1)
    
    # Style the table
    transaction_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Date
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Description
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),  # Amounts
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#003366')),
        
        # Alternating rows
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        
        # Padding
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    elements.append(transaction_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Summary
    summary_data = [
        ["Total Debits:", "₹2,62,000.00"],
        ["Total Credits:", "₹0.00"],
        ["Closing Balance:", "₹-1,62,000.00"],
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer note
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER
    )
    
    elements.append(Paragraph(
        "This is a computer-generated statement and does not require a signature.<br/>"
        "For queries, contact: support@samplebank.com | 1800-XXX-XXXX",
        footer_style
    ))
    
    # Build PDF
    doc.build(elements)
    print(f"✅ PDF generated: {filename}")
    print(f"\nExpected tax deductions:")
    print(f"  - LIC Premium: ₹25,000 (80C)")
    print(f"  - HDFC Life: ₹30,000 (80C)")
    print(f"  - PPF: ₹50,000 (80C)")
    print(f"  - Tuition: ₹40,000 (80C)")
    print(f"  - Home Loan: ₹35,000 (24B)")
    print(f"  - Donation: ₹10,000 (80G)")
    print(f"  - Health Ins: ₹15,000 (80D)")
    print(f"  - NPS: ₹20,000 (80C)")
    print(f"  - Education Loan: ₹12,000 (80E)")
    print(f"  - ELSS: ₹25,000 (80C)")
    print(f"\n  Total: ₹2,62,000")
    print(f"  After 80C limit (₹1,50,000): ~₹2,05,000")
    print(f"  Tax saved @ 20%: ₹41,000")
    print(f"  Tax saved @ 30%: ₹61,500")

if __name__ == "__main__":
    try:
        create_bank_statement_pdf("sample_bank_statement.pdf")
    except ImportError:
        print("❌ reportlab not installed. Installing...")
        import subprocess
        subprocess.check_call(["pip", "install", "reportlab"])
        print("✅ reportlab installed. Running again...")
        create_bank_statement_pdf("sample_bank_statement.pdf")
