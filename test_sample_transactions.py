"""
Test helper: Creates sample transactions to verify categorization works.
Run this to generate test data that should show deductions.
"""

sample_tax_relevant_transactions = [
    {
        "date": "2024-01-15",
        "description": "LIC Premium Payment - Policy 123456",
        "debit_amount": 25000.00,
        "credit_amount": 0,
        "balance": 75000.00,
        "raw_text": "LIC Premium Payment - Policy 123456"
    },
    {
        "date": "2024-02-10",
        "description": "HDFC Life Insurance Premium",
        "debit_amount": 30000.00,
        "credit_amount": 0,
        "balance": 45000.00,
        "raw_text": "HDFC Life Insurance Premium"
    },
    {
        "date": "2024-03-05",
        "description": "PPF Contribution - SBI",
        "debit_amount": 50000.00,
        "credit_amount": 0,
        "balance": -5000.00,
        "raw_text": "PPF Contribution - SBI"
    },
    {
        "date": "2024-04-12",
        "description": "School Tuition Fee - ABC International",
        "debit_amount": 40000.00,
        "credit_amount": 0,
        "balance": -45000.00,
        "raw_text": "School Tuition Fee - ABC International"
    },
    {
        "date": "2024-05-20",
        "description": "Home Loan EMI - HDFC Bank",
        "debit_amount": 35000.00,
        "credit_amount": 0,
        "balance": -80000.00,
        "raw_text": "Home Loan EMI - HDFC Bank"
    },
    {
        "date": "2024-06-08",
        "description": "Donation to PM Cares Fund",
        "debit_amount": 10000.00,
        "credit_amount": 0,
        "balance": -90000.00,
        "raw_text": "Donation to PM Cares Fund"
    },
    {
        "date": "2024-07-15",
        "description": "Health Insurance Premium - Star Health",
        "debit_amount": 15000.00,
        "credit_amount": 0,
        "balance": -105000.00,
        "raw_text": "Health Insurance Premium - Star Health"
    },
    {
        "date": "2024-08-22",
        "description": "NPS Contribution - Tier 1",
        "debit_amount": 20000.00,
        "credit_amount": 0,
        "balance": -125000.00,
        "raw_text": "NPS Contribution - Tier 1"
    },
    {
        "date": "2024-09-10",
        "description": "Education Loan Interest - SBI",
        "debit_amount": 12000.00,
        "credit_amount": 0,
        "balance": -137000.00,
        "raw_text": "Education Loan Interest - SBI"
    },
    {
        "date": "2024-10-05",
        "description": "Mutual Fund ELSS Investment",
        "debit_amount": 25000.00,
        "credit_amount": 0,
        "balance": -162000.00,
        "raw_text": "Mutual Fund ELSS Investment"
    }
]

expected_categorization = {
    "LIC Premium Payment": {
        "category": "insurance",
        "section": "80C",
        "should_be_tax_relevant": True
    },
    "HDFC Life Insurance": {
        "category": "insurance",
        "section": "80C",
        "should_be_tax_relevant": True
    },
    "PPF Contribution": {
        "category": "ppf",
        "section": "80C",
        "should_be_tax_relevant": True
    },
    "School Tuition Fee": {
        "category": "education",
        "section": "80C",
        "should_be_tax_relevant": True
    },
    "Home Loan EMI": {
        "category": "housing loan",
        "section": "24B",
        "should_be_tax_relevant": True
    },
    "Donation to PM Cares": {
        "category": "donation",
        "section": "80G",
        "should_be_tax_relevant": True
    },
    "Health Insurance Premium": {
        "category": "insurance",
        "section": "80D",
        "should_be_tax_relevant": True
    },
    "NPS Contribution": {
        "category": "ppf",
        "section": "80C",
        "should_be_tax_relevant": True
    },
    "Education Loan Interest": {
        "category": "education",
        "section": "80E",
        "should_be_tax_relevant": True
    },
    "Mutual Fund ELSS": {
        "category": "investment",
        "section": "80C",
        "should_be_tax_relevant": True
    }
}

expected_total_deductions = 262000  # Sum of all amounts
expected_capped_80c = 150000  # 80C limit
expected_sections = ["80C", "80D", "80E", "80G", "24B"]

print("Sample Tax-Relevant Transactions")
print("=" * 60)
print(f"Total transactions: {len(sample_tax_relevant_transactions)}")
print(f"Expected deductions (gross): ₹{expected_total_deductions:,}")
print(f"Expected capped deductions: ~₹{expected_total_deductions - (262000 - 150000):,}")
print(f"Expected sections: {', '.join(expected_sections)}")
print("\nIf your PDF has similar descriptions, they SHOULD be categorized!")
