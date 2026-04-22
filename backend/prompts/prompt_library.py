"""
Prompt Engineering Templates for Tax Deduction Analysis
Demonstrates various prompt engineering techniques for capstone project
"""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Structured prompt template with metadata"""
    name: str
    description: str
    template: str
    technique: str  # e.g., "few-shot", "chain-of-thought", "role-playing"
    examples: List[str] = None


class TaxPromptLibrary:
    """
    Centralized prompt library demonstrating prompt engineering best practices.
    Techniques: Few-shot learning, Chain-of-thought, Role-playing, Structured output
    """
    
    # ═══ TECHNIQUE 1: Few-Shot Learning ═══════════════════════════════════════
    CATEGORIZE_FEW_SHOT = PromptTemplate(
        name="Transaction Categorization (Few-Shot)",
        description="Uses few-shot examples to teach LLM transaction categorization",
        technique="few-shot-learning",
        template="""You are a financial transaction categorizer. Analyze the transaction and categorize it.

EXAMPLES:
Input: "LIC Premium Payment - Policy 123456"
Output: {{"category": "Insurance Premium", "merchant_type": "Life Insurance Company", "likely_purpose": "Life Insurance Premium", "is_tax_relevant": true}}

Input: "Amazon Order 12345 - Books"
Output: {{"category": "Shopping", "merchant_type": "E-commerce", "likely_purpose": "Personal Shopping", "is_tax_relevant": false}}

Input: "Public Provident Fund Deposit"
Output: {{"category": "Investment", "merchant_type": "Government Savings Scheme", "likely_purpose": "PPF Investment", "is_tax_relevant": true}}

Input: "Swiggy Food Delivery"
Output: {{"category": "Food & Dining", "merchant_type": "Food Delivery", "likely_purpose": "Personal Expense", "is_tax_relevant": false}}

NOW CATEGORIZE THIS TRANSACTION:
Description: "{transaction_description}"
Amount: ₹{amount}

Respond ONLY with JSON in the same format as examples above."""
    )
    
    # ═══ TECHNIQUE 2: Chain-of-Thought ════════════════════════════════════════
    TAX_MATCHING_COT = PromptTemplate(
        name="Tax Section Matching (Chain-of-Thought)",
        description="Uses step-by-step reasoning to match transactions to tax sections",
        technique="chain-of-thought",
        template="""You are a tax expert analyzing transactions for Indian Income Tax deductions.

TASK: Determine which tax section applies to this transaction.

TRANSACTION:
- Description: {description}
- Category: {category}
- Merchant Type: {merchant_type}
- Amount: ₹{amount}

AVAILABLE TAX SECTIONS:
- Section 80C: Life insurance, PPF, ELSS, home loan principal (Limit: ₹1,50,000)
- Section 80D: Health insurance premiums (Limit: ₹25,000/₹50,000)
- Section 80E: Education loan interest (No limit)
- Section 80G: Donations to registered charities (50% or 100%)
- Section 24B: Home loan interest (Limit: ₹2,00,000)

REASONING STEPS:
1. First, identify the transaction type
2. Then, check if it matches any tax section criteria
3. Finally, determine the applicable section and deduction amount

Think through each step:
Step 1: This transaction is...
Step 2: Checking tax sections...
Step 3: Conclusion...

FINAL ANSWER (JSON format):
{{"section": "80X", "deductible_amount": X, "reasoning": "brief explanation"}}"""
    )
    
    # ═══ TECHNIQUE 3: Role-Playing ════════════════════════════════════════════
    CALCULATION_ROLEPLAY = PromptTemplate(
        name="Deduction Calculation (Role-Playing)",
        description="LLM acts as a certified tax consultant",
        technique="role-playing",
        template="""You are a Certified Chartered Accountant (CA) with 15 years of experience in Indian Income Tax.

CLIENT SCENARIO:
The client has the following tax-deductible transactions:
{transactions_list}

YOUR TASK AS A CA:
1. Review each transaction against current IT Act provisions
2. Apply section-wise limits (80C: ₹1.5L, 80D: ₹25K/50K, etc.)
3. Calculate total deductions and tax savings
4. Provide professional advice

ANALYSIS FORMAT:
═══════════════════════════════════════
SECTION-WISE BREAKDOWN:
[List each section with transactions]

TOTAL DEDUCTIONS: ₹X
TAX SAVINGS (20% slab): ₹Y
TAX SAVINGS (30% slab): ₹Z

PROFESSIONAL ADVICE:
[Your recommendations]
═══════════════════════════════════════

Provide your expert analysis now."""
    )
    
    # ═══ TECHNIQUE 4: Structured Output ═══════════════════════════════════════
    QUERY_TO_SQL = PromptTemplate(
        name="Natural Language to SQL (Structured Output)",
        description="Converts natural language to SQL with strict output format",
        technique="structured-output",
        template="""You are a SQL expert. Convert natural language questions to SQL queries.

DATABASE SCHEMA:
Table: transactions
- id (INTEGER)
- upload_id (INTEGER)
- date (TEXT)
- description (TEXT)
- debit_amount (REAL)
- credit_amount (REAL)
- balance (REAL)
- category (TEXT)
- merchant_type (TEXT)
- is_tax_relevant (BOOLEAN)
- tax_section (TEXT)

QUESTION: {user_question}

RULES:
1. Only use SELECT queries (no INSERT/UPDATE/DELETE)
2. Use proper WHERE clauses for filtering
3. Include aggregations (SUM, COUNT, AVG) when appropriate
4. Format monetary values with 2 decimal places

OUTPUT FORMAT (JSON):
{{
    "sql": "SELECT ...",
    "explanation": "This query finds...",
    "expected_result": "A table showing..."
}}

Generate the SQL query now:"""
    )
    
    # ═══ TECHNIQUE 5: Constrained Generation ══════════════════════════════════
    PII_REDACTION = PromptTemplate(
        name="PII Detection & Redaction (Constrained)",
        description="Detects PII with strict confidence scoring",
        technique="constrained-generation",
        template="""You are a PII (Personally Identifiable Information) detection system.

TEXT TO ANALYZE:
{text}

DETECT THE FOLLOWING PII TYPES:
- PERSON_NAME (names of individuals)
- PHONE_NUMBER (10-digit mobile, landline with STD)
- EMAIL (email addresses)
- PAN_NUMBER (Indian PAN format: ABCDE1234F)
- AADHAAR_NUMBER (12-digit UID)
- BANK_ACCOUNT (account numbers)
- ADDRESS (physical addresses)

OUTPUT CONSTRAINTS:
1. Confidence score must be 0.0 to 1.0
2. Start and end positions must be integers
3. Type must be from the list above
4. Redacted text must use XXX for PII

REQUIRED JSON FORMAT:
{{
    "entities": [
        {{"type": "PERSON_NAME", "value": "John Doe", "start": 0, "end": 8, "confidence": 0.95}},
        ...
    ],
    "redacted_text": "Text with PII replaced by XXX",
    "summary": {{"total_entities": N, "types_found": ["TYPE1", ...]}}
}}

Analyze and respond:"""
    )
    
    @classmethod
    def get_prompt(cls, name: str, **kwargs) -> str:
        """Get a prompt template filled with provided kwargs"""
        prompts = {
            "categorize": cls.CATEGORIZE_FEW_SHOT,
            "tax_matching": cls.TAX_MATCHING_COT,
            "calculation": cls.CALCULATION_ROLEPLAY,
            "query_to_sql": cls.QUERY_TO_SQL,
            "pii_detection": cls.PII_REDACTION,
        }
        
        template = prompts.get(name)
        if not template:
            raise ValueError(f"Prompt '{name}' not found")
        
        return template.template.format(**kwargs)
    
    @classmethod
    def list_prompts(cls) -> List[Dict]:
        """List all available prompts with metadata"""
        return [
            {
                "name": cls.CATEGORIZE_FEW_SHOT.name,
                "technique": cls.CATEGORIZE_FEW_SHOT.technique,
                "description": cls.CATEGORIZE_FEW_SHOT.description
            },
            {
                "name": cls.TAX_MATCHING_COT.name,
                "technique": cls.TAX_MATCHING_COT.technique,
                "description": cls.TAX_MATCHING_COT.description
            },
            {
                "name": cls.CALCULATION_ROLEPLAY.name,
                "technique": cls.CALCULATION_ROLEPLAY.technique,
                "description": cls.CALCULATION_ROLEPLAY.description
            },
            {
                "name": cls.QUERY_TO_SQL.name,
                "technique": cls.QUERY_TO_SQL.technique,
                "description": cls.QUERY_TO_SQL.description
            },
            {
                "name": cls.PII_REDACTION.name,
                "technique": cls.PII_REDACTION.technique,
                "description": cls.PII_REDACTION.description
            },
        ]


# ═══ USAGE EXAMPLES ═══════════════════════════════════════════════════════════

def example_usage():
    """Demonstrate prompt engineering techniques"""
    
    # Example 1: Few-shot categorization
    categorize_prompt = TaxPromptLibrary.get_prompt(
        "categorize",
        transaction_description="HDFC Life Insurance Premium",
        amount="15000"
    )
    print("FEW-SHOT PROMPT:")
    print(categorize_prompt)
    print("\n" + "="*80 + "\n")
    
    # Example 2: Chain-of-thought matching
    cot_prompt = TaxPromptLibrary.get_prompt(
        "tax_matching",
        description="PPF Deposit via SBI",
        category="Investment",
        merchant_type="Government Savings",
        amount="20000"
    )
    print("CHAIN-OF-THOUGHT PROMPT:")
    print(cot_prompt)
    print("\n" + "="*80 + "\n")
    
    # Example 3: List all prompts
    print("AVAILABLE PROMPT TEMPLATES:")
    for prompt_info in TaxPromptLibrary.list_prompts():
        print(f"- {prompt_info['name']} ({prompt_info['technique']})")
        print(f"  {prompt_info['description']}")


if __name__ == "__main__":
    example_usage()
