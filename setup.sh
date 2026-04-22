#!/bin/bash
set -e

echo "======================================"
echo " Smart Tax Deduction Finder - Setup"
echo "======================================"

# Check Python 3.11
if ! command -v python3.11 &>/dev/null; then
    echo "Python 3.11 not found. Please install Python 3.11 first."
    exit 1
fi

echo "[1/6] Creating virtual environment: tax_agent"
python3.11 -m venv tax_agent
source tax_agent/bin/activate

echo "[2/6] Upgrading pip"
pip install --upgrade pip

echo "[3/6] Installing requirements"
pip install -r requirements.txt

echo "[4/6] Downloading spaCy English model (for Presidio)"
python -m spacy download en_core_web_lg

echo "[5/6] Creating .env from .env.example (if not exists)"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  Created .env — please fill in your GROQ_API_KEY"
fi

echo "[6/6] Creating required directories"
mkdir -p uploads chroma_db backend/data

echo ""
echo "======================================"
echo " Setup complete!"
echo " Activate env: source tax_agent/bin/activate"
echo " Start backend: uvicorn backend.main:app --reload --port 8000"
echo " Start frontend: streamlit run frontend/app.py"
echo "======================================"
