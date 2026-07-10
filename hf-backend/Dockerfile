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

COPY . .

# Hugging Face Spaces run the container as a non-root user (uid 1000). Create that
# user, give it a writable home (for model caches) and a writable data dir (FAISS),
# then drop privileges — otherwise startup fails writing to a root-owned /app.
RUN useradd -m -u 1000 user \
    && mkdir -p /app/data \
    && chown -R user:user /app

ENV HOME=/home/user \
    HF_HOME=/home/user/.cache/huggingface \
    VECTOR_STORE_PATH=/app/data/vectorstore

USER user

# Listen on 7860 to match the Space app_port. Redirect stderr→stdout so uvicorn's
# startup logs (and any traceback) are visible in the Space's runtime logs.
EXPOSE 7860

CMD ["sh", "-c", "echo '>>> booting uvicorn on 7860'; uvicorn app.main:app --host 0.0.0.0 --port 7860 --log-level info 2>&1"]
