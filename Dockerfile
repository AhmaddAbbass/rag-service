FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY rag-service/requirements.txt /app/requirements.txt
COPY nano-graphrag /deps/nano-graphrag
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir --no-deps -e /deps/nano-graphrag

COPY rag-service /app

EXPOSE 8001

CMD ["/bin/sh", "-c", "alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port ${API_PORT:-8001}"]
