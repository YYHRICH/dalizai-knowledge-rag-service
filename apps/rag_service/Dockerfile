FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN python -m pip install --upgrade pip

COPY pyproject.toml README.md ./
COPY apps ./apps
COPY scripts ./scripts
COPY docs ./docs
COPY eval ./eval
COPY knowledge ./knowledge

RUN python -m pip install .

EXPOSE 8100

CMD ["uvicorn", "apps.rag_service.app.main:app", "--host", "0.0.0.0", "--port", "8100"]
