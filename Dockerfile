# ---------- Stage 1: Build dependencies ----------
FROM python:3.10.13-slim-bullseye AS builder

# Install build tools safely
RUN rm -rf /var/lib/apt/lists/* && \
    apt-get clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy minimal backend requirements to avoid deep dependency resolution in image build
COPY requirements.backend.txt ./requirements.backend.txt

# Build wheels from trimmed backend requirements. If wheel build fails due to
# resolver complexity, we fall back to installing at runtime from the trimmed
# requirements file (see runtime stage below).
RUN pip install --upgrade pip && \
    (pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.backend.txt || echo "wheel build failed, will install at runtime")


# ---------- Stage 2: Runtime ----------
FROM python:3.10.13-slim-bullseye

# Install runtime dependencies
RUN rm -rf /var/lib/apt/lists/* && \
    apt-get clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        poppler-utils \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create user
RUN useradd -m -u 1000 appuser

# Copy dependencies
COPY --from=builder /build/wheels /wheels
COPY requirements.backend.txt ./requirements.backend.txt

RUN pip install --upgrade pip && \
    if [ -d /wheels ] && [ "$(ls -A /wheels)" ]; then \
        pip install --no-cache-dir /wheels/* ; \
    else \
        pip install --no-cache-dir -r requirements.backend.txt ; \
    fi && \
    rm -rf /wheels

# Install spaCy and a compact English model at build time so Presidio
# does not try to download a large model at runtime (avoids SSL/runtime issues).
RUN pip install --no-cache-dir "spacy>=3.5" && \
    python -m spacy validate || true && \
    python -m spacy download en_core_web_sm || true

# Copy app
COPY backend ./backend
COPY setup.sh .

# Fix permissions
RUN mkdir -p /app/uploads /app/chroma_db /app/backend/data/faiss_index && \
    chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]