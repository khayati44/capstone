from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, field_validator


# ─── Auth Schemas ────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None


# ─── Transaction Schemas ─────────────────────────────────────────────────────

class TransactionBase(BaseModel):
    date: Optional[str] = None
    description: Optional[str] = None
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    balance: Optional[float] = None
    raw_text: Optional[str] = None


class TransactionCreate(TransactionBase):
    upload_id: Optional[int] = None


class TransactionResponse(TransactionBase):
    id: int
    user_id: int
    upload_id: Optional[int]
    merchant_type: Optional[str]
    likely_purpose: Optional[str]
    is_tax_relevant: bool
    matched_section: Optional[str]
    deduction_percentage: Optional[float]
    conditions: Optional[str]
    deductible_amount: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Upload Schemas ───────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    id: int
    filename: str
    status: str
    bank_name: Optional[str]
    transaction_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Analysis Schemas ─────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    upload_id: int


class DeductionLineItem(BaseModel):
    transaction_id: int
    date: Optional[str]
    description: Optional[str]
    amount: float
    section: str
    deduction_percentage: float
    deductible_amount: float
    conditions: Optional[str]


class SectionSummary(BaseModel):
    section: str
    total_deductible: float
    limit: float
    capped_deductible: float
    transaction_count: int


class DeductionReportSchema(BaseModel):
    upload_id: int
    total_gross_deductions: float
    total_capped_deductions: float
    estimated_tax_saved_20_percent: float
    estimated_tax_saved_30_percent: float
    sections_covered: list[str]
    line_items: list[DeductionLineItem]
    section_summaries: list[SectionSummary]


# ─── Query Schemas ────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    sql: str
    result: Any  # Can be list, dict, str, int, etc.
    answer: str
