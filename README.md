# Dalizai Knowledge RAG Service

独立知识 RAG 服务，第一版服务于 `dalizai-agent-service` 的 `faq_knowledge_mcp`，但按多 Agent 复用设计。

## 第一版定位

- RAG 只返回知识依据、候选片段、允许表达和禁止表达。
- 最终对客回复由 Reply Agent 生成。
- 订单金额、余额、退款进度、设备实时状态等业务真值走业务 MCP。
- 知识源第一版使用 Markdown，向量库使用 Qdrant。
- 第一版默认通过 DashScope 云 API 提供 embedding 和 rerank。

## 本地准备

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

模型选型默认使用 DashScope：

```text
EMBEDDING_MODEL=qwen3.7-text-embedding
RERANK_MODEL=qwen3-rerank
```

你需要在 `.env` 中配置 `DASHSCOPE_API_KEY`。

Qdrant：

```powershell
docker compose up qdrant
```

## 目录

- `apps/rag_service`: RAG API 服务
- `apps/model_service`: 可选本地模型服务预留，第一版默认使用 DashScope
- `knowledge`: Markdown 知识库
- `eval`: 检索评测集
- `docs`: 接口、架构、知识格式文档
- `scripts`: 入库、复核、评测脚本
