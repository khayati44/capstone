# 🧾 Smart Tax Deduction Finder

An AI-powered application for Indian salaried employees to upload bank statement PDFs, extract transactions via OCR, and identify all eligible tax deductions using a multi-agent AI pipeline.

## ✨ Features

- **PDF OCR**: Upload bank statements (HDFC, SBI, ICICI) — text extracted via pytesseract + EasyOCR fallback
- **PII Redaction**: Account numbers & sensitive data redacted via Presidio before storage
- **3-Agent AI Pipeline** (LangChain + Groq llama-3.3-70b-versatile):
  - Agent 1: Transaction Categorizer
  - Agent 2: Tax Rule Matcher (RAG-grounded via ChromaDB)
  - Agent 3: Deduction Calculator with section limits
- **RAG Knowledge Base**: Indian Income Tax Act sections embedded in ChromaDB
- **Text-to-SQL**: Ask natural language questions about your transactions
- **Beautiful Streamlit UI**: Multi-page app with charts, tables, CSV export
- **Secure Auth**: JWT + Argon2 password hashing

## 🚀 Quick Start

### Option 1: Local Setup

```bash
# 1. Clone and enter directory
cd tax_deduction_finder

# 2. Run setup (creates tax_agent venv, installs all deps)
bash setup.sh

# 3. Activate venv and configure env
source tax_agent/bin/activate
cp .env.example .env
# Edit .env — add your GROQ_API_KEY

# 4. Initialize RAG knowledge base
python -c "from backend.rag.ingestion import ingest_knowledge_base; ingest_knowledge_base()"

# 5. Start backend
uvicorn backend.main:app --reload --port 8000

# 6. Start frontend (new terminal)
source tax_agent/bin/activate
streamlit run frontend/app.py
```

### Option 2: Docker

```bash
cp .env.example .env
# Edit .env — add GROQ_API_KEY
docker-compose up --build
```

Open: http://localhost:8501

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key (get at console.groq.com) |
| `SECRET_KEY` | JWT secret — change in production |
| `DATABASE_URL` | SQLite path (default: `sqlite:///./tax_deductions.db`) |
| `CHROMA_PERSIST_DIR` | ChromaDB storage directory |

## 📁 Project Structure

```
tax_deduction_finder/
├── backend/          # FastAPI backend
│   ├── agents/       # 3-agent AI pipeline
│   ├── rag/          # ChromaDB RAG pipeline
│   ├── ocr/          # PDF OCR extraction
│   ├── auth/         # JWT + Argon2 auth
│   ├── text_to_sql/  # Natural language → SQL
│   ├── pii/          # PII redaction
│   └── routers/      # API endpoints
├── frontend/         # Streamlit UI
└── tests/            # Pytest tests
```

## 🧪 Running Tests

```bash
source tax_agent/bin/activate
pytest tests/ -v
```

## 📋 API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Get JWT token |
| GET | `/auth/me` | Get current user |
| POST | `/api/upload` | Upload PDF bank statement |
| POST | `/api/analyze` | Run 3-agent analysis |
| GET | `/api/deductions` | Get deduction results |
| POST | `/api/query` | Text-to-SQL natural language |
| GET | `/health` | Health check |
| GET | `/docs` | OpenAPI documentation |

## 💡 Supported Tax Sections

- **80C**: LIC, PPF, ELSS, EPF, tuition fees (max ₹1,50,000)
- **80D**: Health insurance premiums (max ₹25,000 / ₹50,000 senior)
- **80E**: Education loan interest (full amount)
- **80G**: Charitable donations (50%–100%)
- **80GG**: Rent paid (no HRA) — min of 3 conditions
- **24B**: Home loan interest (max ₹2,00,000)
- **Section 37**: Business expenses (professional use)
