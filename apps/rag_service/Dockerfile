# ── 生产阶段 ────────────────────────────────────────────────
FROM python:3.11-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 使用阿里云 PyPI 镜像，避免公司网络 SSL 证书问题
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip config set global.trusted-host mirrors.aliyun.com

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

# ── 测试阶段 ────────────────────────────────────────────────
FROM production AS test

# 安装开发依赖（pytest / ruff 等）
RUN python -m pip install -e ".[dev]"

# 默认跑全量测试。运行时可通过 volume 挂载 .env 获取 DASHSCOPE_API_KEY 等
CMD ["python", "-m", "pytest", "apps/rag_service/tests/", "-v"]
