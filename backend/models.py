from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    uploads: Mapped[list["UploadRecord"]] = relationship("UploadRecord", back_populates="user")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="user")


class UploadRecord(Base):
    __tablename__ = "upload_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)
    bank_name: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="processing")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    raw_text: Mapped[str] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="uploads")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="upload")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    upload_id: Mapped[int] = mapped_column(Integer, ForeignKey("upload_records.id"), nullable=True)
    date: Mapped[str] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    debit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    credit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    balance: Mapped[float] = mapped_column(Float, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=True)

    # Categorization fields
    merchant_type: Mapped[str] = mapped_column(String(200), nullable=True)
    likely_purpose: Mapped[str] = mapped_column(String(500), nullable=True)
    is_tax_relevant: Mapped[bool] = mapped_column(Boolean, default=False)

    # Tax matching fields
    matched_section: Mapped[str] = mapped_column(String(50), nullable=True)
    deduction_percentage: Mapped[float] = mapped_column(Float, nullable=True)
    conditions: Mapped[str] = mapped_column(Text, nullable=True)
    deductible_amount: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="transactions")
    upload: Mapped["UploadRecord"] = relationship("UploadRecord", back_populates="transactions")


class DeductionReport(Base):
    __tablename__ = "deduction_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    upload_id: Mapped[int] = mapped_column(Integer, ForeignKey("upload_records.id"), nullable=True)
    total_deductions: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_tax_saved_20: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_tax_saved_30: Mapped[float] = mapped_column(Float, default=0.0)
    sections_covered: Mapped[str] = mapped_column(String(500), nullable=True)
    report_json: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
