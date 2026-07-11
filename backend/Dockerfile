FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for some scientific / parsing wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Hugging Face Spaces run the container as a non-root user (uid 1000). Create that
# user now (before baking model caches) so the caches can live in its home and be
# owned correctly, then drop privileges later.
RUN useradd -m -u 1000 user

ENV HOME=/home/user \
    HF_HOME=/home/user/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/home/user/.cache/huggingface \
    HF_HUB_DISABLE_TELEMETRY=1 \
    VECTOR_STORE_PATH=/app/data/vectorstore

# Pre-download the embedding + reranker models at BUILD time so they are baked into
# the image layer. Without this, the first /documents/ingest (or /chat) request on a
# fresh container downloads ~200MB of model weights lazily, which on free-tier
# cpu-basic exceeds the HF Spaces ~60s request-proxy timeout and drops the connection.
# Baking them in means startup warmup only loads from local disk (fast).
# Keep these ARG defaults in sync with app defaults and the Space's EMBEDDING_MODEL /
# RERANKER_MODEL secrets.
ARG EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
ARG RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RUN EMBEDDING_MODEL="${EMBEDDING_MODEL}" RERANKER_MODEL="${RERANKER_MODEL}" \
    python -c "import os; from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer(os.environ['EMBEDDING_MODEL']); CrossEncoder(os.environ['RERANKER_MODEL'])"

COPY . .

# Give the runtime user ownership of the app dir (writable data dir for FAISS) and
# the baked model cache in its home.
RUN mkdir -p /app/data \
    && chown -R user:user /app /home/user

USER user

# Listen on 7860 to match the Space app_port. Redirect stderr→stdout so uvicorn's
# startup logs (and any traceback) are visible in the Space's runtime logs.
EXPOSE 7860

CMD ["sh", "-c", "echo '>>> booting uvicorn on 7860'; uvicorn app.main:app --host 0.0.0.0 --port 7860 --log-level info 2>&1"]
