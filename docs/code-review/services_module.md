# 代码模块评审报告

## 1. 评审基本信息

- 评审模块：RAG 核心编排 —— Query Rewrite + 检索链路编排，整个 RAG 服务的大脑
- 代码语言：Python 3.11
- 评审范围：`apps/rag_service/app/services/` 全部 3 个文件（`__init__.py` 为空、`query_rewriter.py` 146 行、`rag_query_service.py` 466 行）
- 整体风险等级：**低风险**

## 2. 模块架构学习引导

### 2.1 模块定位与业务价值

本模块是 RAG 检索链路的**总指挥**。它负责两件事：
- **Query Rewrite**（`query_rewriter.py`）：把用户口语查询改写为检索友好的短句
- **检索编排**（`rag_query_service.py`）：串起 Rewrite → Embedding → Qdrant → Rerank → 信号增强 → 阈值分档 → 审计记录七步

在整个系统中的位置——它是上游 Agent API 和下游模型服务/Qdrant 之间的唯一调度层：

```
POST /v1/rag/query → routes.py
        ↓
   RagQueryService.query()          ← 本模块
        ├── QueryRewriter.rewrite() → DashScopeChatClient  → Chat API
        ├── EmbeddingClient         → DashScope Embedding API
        ├── QdrantKnowledgeStore    → Qdrant
        ├── RerankClient            → DashScope Rerank API
        ├── _query_signal_score     → 本地文本信号
        └── MetadataRepository      → SQLite
```

### 2.2 架构分层与职责划分

| 文件 | 职责 | 行数 |
|---|---|---|
| `query_rewriter.py` | LLM 查询改写 + fallback 兜底 | 146 |
| `rag_query_service.py` | 完整检索链路编排 + 打分 + 分档 + 审计 | 466 |
| `__init__.py` | 空（模块未导出公共 API） | 0 |

`QueryRewriter` 通过 `Protocol` 解耦客户端依赖，`RagQueryService` 在 `__init__` 中组装所有依赖，每个请求构造新实例不做单例。

### 2.3 核心业务全链路

```
POST /v1/rag/query {query: "有没有优惠券", filters: ...}

步骤1: Query Rewrite
  QueryRewriter.rewrite(request)
    → _system_prompt() + _user_prompt(request) → Chat API
    → 返回 JSON {"queryRewrite": "有没有优惠券；怎么领优惠券；优惠券领取"}
    → _parse_rewrite() → 容错处理（数组→分号、截断300字）
    → "有没有优惠券；怎么领优惠券；优惠券领取"

步骤2: Embedding + 向量检索
  embedding_client.embed_texts([rewrite]) → [1024维向量]
  qdrant.search(vector, filters, limit=10) → list[ScoredPoint]

步骤3: Rerank
  _rerank_text(payload) → "标题：xxx\n关键词：xxx\n..."
  rerank_client.rerank(query, docs, top_n=5) → [RerankResult]

步骤4: 信号增强
  for each rerank result:
    score = max(rerank_score, _query_signal_score(query, payload))
  sort desc

步骤5: 阈值分档
  confidence = ranked_points[0][1]
  ≥ 0.50 → success     → answerable=true, 返回 items + allowedClaims
  ≥ 0.30 → low_confidence → answerable=false, 返回 items + fallback
  < 0.30 → not_found   → items=[], Agent 不要编造

步骤6: 审计记录
  _record_query() → audit_logs（每次必写）+ gap_events（not_found/low_confidence时）
  写入失败 silent return，不阻塞查询响应
```

### 2.4 关键组件与数据模型

**`QueryRewriter`**：
- Protocol `QueryRewriteChatClient`：解耦 DashScope 依赖，测试注入 mock
- `fallback_on_error=True`：改写失败退原始 query
- `_system_prompt`：7 条改写规则，强调口语化、反书面化
- `_parse_rewrite`：4 层容错（数组→字符串、分号统一、去空、截断）

**`RagQueryService`**：
- `query()`：七步编排方法，每步有 `# ── Step ──` 行内标注
- `_response()` / `_error_response()`：两类响应构造，通过 `**kwargs` 消除重复
- `_query_signal_score()`：5 级字符匹配阶梯（精确→子串→bigram Jaccard）
- `_record_query()`：审计双写 + try/except 静默降级
- `_rerank_text()`：拼接标题/摘要/关键词/相似问法/正文/允许表达

### 2.5 设计思想与技术选型

- **Protocol 而非 ABC**：`QueryRewriteChatClient` 用 `typing.Protocol` 定义接口，任何有 `complete_json` 方法的对象都能注入
- **服务可用性优先**：改写失败 fallback 原 query、审计写入失败 silent return——辅助功能绝不拖垮核心链路
- **`max(rerank, text_signal)`**：语义匹配和关键词匹配取最大值而非加权平均，两种信号互补
- **`_response` 用 `**kwargs`**：三个状态共享同一构造逻辑，消除重复代码
- **每请求新建实例**：`RagQueryService` 不做单例，无状态污染

### 2.6 模块上手学习路径

1. **先看 `query_rewriter.py` L46-72**：`rewrite()` 三步走（调 API → 解析 → fallback）
2. **看 `rag_query_service.py` L94-228**：`query()` 七步编排，顺 Step 标注读
3. **看 `_query_signal_score` L351-401**：5 级匹配阶梯算法
4. **看 `_record_query` L270-333**：审计双写 + 静默降级设计
5. **扫一眼 `_rerank_text`、`_item_response`、`_knowledge_version`**：纯数据映射

---

## 3. 模块设计总评

**设计亮点**：七步编排链清晰、`max()` 混合打分务实、审计静默降级稳健、`Protocol` 解耦优雅。

**架构缺陷**：`query()` 方法 135 行承担了太多职责（参数确定/检索/rerank/打分/分档/响应构造），拆分后可读性更好。`__init__.py` 空置——模块公开 API 未声明。

---

## 4. 高危问题总览

| 等级 | 问题 | 位置 |
|---|---|---|
| 🟡 P1 | `_record_query` 裸吞异常无日志 | `rag_query_service.py` L331 |
| 🟡 P1 | `query()` 方法 135 行，职责过重 | `rag_query_service.py` L94-228 |
| 🟢 P2 | `_query_signal_score` 魔法数字 | `rag_query_service.py` L351-401 |
| 🟢 P2 | `__init__.py` 空置 | `services/__init__.py` |
| 🟢 P2 | `query_rewriter.py` 无改写质量监控 | `query_rewriter.py` L67-71 |

---

## 5. 分项详细评审

### 5.1 业务逻辑与正确性问题

无 P0 问题。检索链路的 Step 顺序和异常处理分支完整：Embedding 失败 → error、Rerank 失败 → error、无候选 → not_found、rerank 结果无法关联 → not_found。所有异常路径有兜底。

### 5.2 异常容错与稳定性问题

🟡【P1】`rag_query_service.py` L331 — `_record_query` 的 `except Exception: return` 裸吞异常无日志。审计/缺口写入失败不会被感知。**修复**：加 `logging.getLogger(__name__).exception("audit write failed")` 后 return。

🟢【P2】`query_rewriter.py` L67-71 — fallback 发生时无日志，改写成功率不可观测。**修复**：catch 块中加 `logging.warning(f"rewrite failed, fallback: {exc}")`。

### 5.3 性能、数据库与IO风险问题

无问题。每请求创建实例后用完即弃，无连接泄漏。`with_vectors=False` 减少 Qdrant 网络传输。

### 5.4 安全、权限与数据合规问题

无问题。`sessionId`/`userId` 经 SHA-256 + salt 哈希后存储，`query` 经 PII 脱敏。`rag_service_api_key` 作为 salt。

### 5.5 日志监控与可观测性问题

🟢【P2】`RagQueryService` 内部无业务日志。当前依赖调用方（routes.py）和评测脚本的 print 输出。检索延迟、改写成功率、信号增强触发率等无埋点。**修复**：关键步骤加 `logging.debug`，并暴露 metrics 端点。

### 5.6 架构设计与代码可维护性问题

🟡【P1】`rag_query_service.py` L94-228 — `query()` 135 行承担 7 个不同关注点。**修复**：拆为 `_retrieve()`（Step 1-4）、`_rerank_and_boost()`（Step 5-6）、`_classify()`（Step 7）三个子方法。

🟢【P2】`rag_query_service.py` L351-401 — 魔法数字（0.92/0.88/0.90/0.78/0.55/0.30/4）散布在 `_query_signal_score` 中。**修复**：抽取为模块级常量或进 Settings。

🟢【P2】`services/__init__.py` 空置，`QueryRewriter` 和 `RagQueryService` 未导出。外部只能 `from apps.rag_service.app.services.rag_query_service import RagQueryService` 绕过封装。**修复**：补全 `__init__.py` 导出列表。

### 5.7 测试覆盖与上线风险问题

`test_query_rewriter.py` 覆盖了正常改写、数组输出、invalid JSON fallback、fallback 关闭时抛异常——覆盖充分。`test_rag_query_service.py` 覆盖了正常查询、无结果、信号增强命中、信号增强不误匹配——覆盖充分。缺少：改写 prompt 变更后的回归测试、信号增强边界（极短/极长 query）测试。

---

## 6. 问题等级统计

- P0 阻断问题：**0 个**
- P1 隐患问题：**2 个**
- P2 优化建议：**4 个**

---

## 7. 上线准入结论

**允许直接上线。** 核心编排逻辑正确，异常处理和降级策略务实。2 个 P1（审计日志裸吞异常、query() 方法过长）不影响线上稳定性。

## 8. 修复路线图

### 短期优化
1. `_record_query` 增加异常日志
2. `query_rewriter` fallback 增加 warning 日志
3. `services/__init__.py` 补全导出

### 长期重构
4. `query()` 拆分为 3 个子方法
5. `_query_signal_score` 魔法数字抽取为常量
6. 增加改写质量监控埋点
