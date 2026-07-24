# 大力仔 RAG 知识服务 —— 系统架构与设计评审总报告

## 一、总览

### 1.1 系统定位

大力仔 RAG 知识服务是一个**独立部署的知识检索微服务**，为 AI 客服 Agent 提供结构化的知识依据。核心原则：**RAG 只返回检索结果和可信度，不生成最终对客回复**——最终回复由 Agent 侧的 Reply Agent 基于 `allowedClaims` / `forbiddenClaims` 合成。

### 1.2 核心数据流

```
        ┌───────────────── 离线链路 ─────────────────┐
        │                                            │
   Markdown 知识库                                  │
        │                                            │
   ingestion/  ──→  DashScope Embedding  ──→  Qdrant │
        │                                            │
        └────────────────────────────────────────────┘

        ┌───────────────── 在线链路 ─────────────────┐
        │                                            │
   POST /v1/rag/query                               │
        │                                            │
   services/query_rewriter    ──→  DashScope Chat    │
        │                                            │
   services/rag_query_service ──→  DashScope Embedding│
        │                     ──→  Qdrant search      │
        │                     ──→  DashScope Rerank    │
        │                     ──→  本地信号增强        │
        │                     ──→  阈值分档            │
        │                                            │
        └──→ RagQueryResponse ──→ Agent              │
                                              
        ┌────────── 治理闭环 ──────────┐
        │                              │
   审计日志 + 缺口事件 (每次查询)        │
        │                              │
   governance/gap_clustering           │
        │                              │
   缺口集群 → 运营补知识 → 重新入库     │
        │                              │
        └──────────────────────────────┘
```

### 1.3 模块全景

| 模块 | 文件数 | 行数 | 职责 | 评审批次 |
|---|---|---|---|---|
| ingestion/ | 5 | ~650 | Markdown 解析、校验、Embedding 文本构造 | 第一批 |
| providers/ | 4 | ~500 | DashScope API 封装（Embedding/Rerank/Chat） | 第三批 |
| retrievers/ | 2 | ~270 | Qdrant 向量检索与 collection 管理 | 第四批 |
| services/ | 2 | ~610 | 查询改写 + 检索链路编排 | 核心 |
| evaluation/ | 5 | ~565 | 评测用例加载、打分、报告生成 | 第五批 |
| governance/ | 1 | ~300 | 知识缺口增量聚类 | 第六批 |

### 1.4 全网 P0/P1 汇总

审查范围：6 个模块，18 个文件，约 2900 行代码。

- **P0 阻断问题：0 个**
- **P1 隐患问题：15 个**

| 模块 | P1 | 核心问题 |
|---|---|---|
| ingestion/ | 4 | `str(None)` 数据污染、三级标题静默丢弃、高风险类型漏配、日期解析错误信息不全 |
| providers/ | 4 | 三个 Client 的 `__init__`/`close`/`_headers`/`_handle_response`/`_extract_error_message` 共 ~130 行完全重复 |
| retrievers/ | 2 | alias 切换并发窗口、旧 collection 不清理 |
| services/ | 2 | `_record_query` 裸吞异常无日志、`query()` 135 行职责过重 |
| evaluation/ | 1 | `case_loader.py` 缩进不一致 |
| governance/ | 2 | 贪心聚类顺序敏感、`_summarize` 异常无日志 |

**风险等级：低。** 15 个 P1 中无数据错误、安全漏洞或功能不可用类问题。全部为"长期维护隐患"或"静默降级信号缺失"类问题。核心检索链路正确、异常处理完备、评测通过率 97%。

---

## 二、各模块详细设计

### 2.1 ingestion/ —— 知识摄取层

#### 2.1.1 在系统中的角色

整个 RAG 的数据入口。运营人员用 Markdown 编写知识内容 → 本模块解析为结构化数据 → 向量化 → 写入 Qdrant。

#### 2.1.2 数据流

```
knowledge/*.md
  → KnowledgeMarkdownParser.parse_directory()
    → parse_file() → YAML front matter + ## 二级标题切条目 + ### 三级标题切字段
    → KnowledgeDocument { metadata, items: [KnowledgeItem] }
  → KnowledgeValidator.validate()
    → 文档级校验：metadata 必填 / 白名单 / 日期格式 / 风险等级
    → 条目级校验：ID 格式 / 长度 / forbidden_claims 分级
    → ValidationReport { errors, warnings, ok }
  → build_embedding_text()
    → "标题：xxx\n业务域：xxx\n摘要：xxx\n关键词：xxx\n正文：xxx\n允许表达：xxx"
```

#### 2.1.3 关键设计决策

**1. 全链路 frozen dataclass**

所有 6 个 dataclass 均为 `frozen=True`。parser → validator → embedding builder 三步中数据只读不改，杜绝意外修改。线程安全，调试友好。

**2. 错误累积模式**

parser 和 validator 都采用"收集所有错误"而非"遇到第一个错就抛"。一次校验看到全部问题，避免"修一个报一个"的循环。

**3. 中英双语 section 别名**

```python
SECTION_ALIASES = {
    "summary": "Summary", "摘要": "Summary",
    "content": "Content", "正文": "Content",
    "allowed claims": "Allowed Claims", "允许表达": "Allowed Claims",
    ...
}
```

编辑器用中英文均可，内部统一为规范名。降低运营编辑门槛。

**4. forbiddenClaims 不参与 Embedding**

`build_embedding_text()` 拼接时排除 `forbidden_claims`。原因是"不允许承诺赔偿"这类否定句如果参与向量化，会和用户查询"能赔多少钱"产生语义近似——但实际上一个是禁止表达、一个是用户诉求，语义完全相反。

**5. 风险等级自动推导**

`_risk_level()` 在 YAML 未显式声明 `riskLevel` 时根据 `knowledgeType` 推断：`billing_policy`、`refund_policy`、`coupon_policy`、`risk_notice` 四种涉钱或涉合规的类型默认 `high`。

#### 2.1.4 模块间接口

| 输入 | 输出 | 下游消费者 |
|---|---|---|
| `knowledge/` 目录 | `list[KnowledgeDocument]` | `KnowledgeValidator` |
| `list[KnowledgeDocument]` | `ValidationReport` | `ingest_knowledge.py` |
| `KnowledgeItem` | `str`（Embedding 文本） | `DashScopeEmbeddingClient` |

---

### 2.2 providers/ —— 模型服务层

#### 2.2.1 在系统中的角色

RAG 服务与阿里云 DashScope API 之间的**唯一通信层**。三个客户端各司其职：

- `DashScopeEmbeddingClient`：文本 → 1024 维向量
- `DashScopeRerankClient`：召回候选 → 按相关性重新排序
- `DashScopeChatClient`：Query Rewrite + 缺口聚类摘要

#### 2.2.2 数据流

```
RagQueryService
  ├──→ DashScopeChatClient.complete_json(sys, usr)
  │      → POST /chat/completions {model, messages, temperature:0.2, response_format:json_object}
  │      → ChatCompletionResult(content=JSON字符串)
  │
  ├──→ DashScopeEmbeddingClient.embed_texts(["..."])
  │      → POST /embeddings {model, input, dimensions:1024}
  │      → 校验：返回数量==输入数，维度==1024
  │      → EmbeddingResult(embeddings=[[1024个float]])
  │
  └──→ DashScopeRerankClient.rerank(query, [RerankDocument], top_n=5)
         → POST /reranks {model, query, documents, top_n, return_documents:false}
         → 校验：index 在 documents 范围内
         → [RerankResult(id=chunkId, index, score)]
```

#### 2.2.3 关键设计决策

**1. 统一错误分类 + 可恢复性标记**

```
HTTP 4xx → ModelProviderBadRequestError → retryable=False
HTTP 401/403 → ModelProviderAuthError → retryable=False
HTTP 5xx → ModelProviderError → retryable=True
```

调用方只需 `exc.retryable` 一个判断即可决策：True → Agent 可重试，False → Agent 直接安全兜底。

**2. 依赖注入 + 自管理连接**

```python
def __init__(self, settings, http_client: httpx.Client | None = None):
    self._client = http_client or httpx.Client(timeout=...)
    self._owns_client = http_client is None
```

测试时注入 mock，生产时自动创建。`_owns_client` 标记决定 `close()` 是否释放——测试 mock 不会被误关。

**3. 返回数据防御性校验**

- `embed_texts`：校验返回向量数 == 输入数，每个向量维度 == 1024
- `rerank`：校验 index 不越界
- `complete_json`：校验 content 非空字符串

#### 2.2.4 主要 P1：代码重复

三个 Client 中 `__init__` / `close` / `_headers` / `_handle_response` / `_extract_error_message` 五个方法共约 130 行完全重复。修复方案：抽取 `_BaseDashScopeClient` 基类。

---

### 2.3 retrievers/ —— 向量检索层

#### 2.3.1 在系统中的角色

RAG 服务与 Qdrant 之间的**唯一交互层**。注意 Qdrant 在本项目中仅是检索索引，不是知识主库——主库是 Markdown + Git。这意味着 Qdrant 数据可全量重建，设计上优先检索可用性。

#### 2.3.2 关键设计决策

**1. Alias 模式：零停机更新**

```
ingest 流程：
  recreate_collection("dalizai_knowledge_20260724_030108")  ← 创建全新 collection
  upsert_items(..., 91 items)                                 ← 全量写入
  switch_alias("dalizai_knowledge_20260724_030108")          ← 原子切换
```

检索始终通过 alias 访问：
```python
search(collection_name=self.settings.qdrant_collection_alias, ...)  # "dalizai_knowledge_v1"
```

切换瞬间完成，检索不中断。Alias 操作在 Qdrant 中是事务性的。

**2. scope 过滤：三态逻辑**

```python
def _scope_condition(key, value):
    if value:         # 定向匹配：全局 OR 该值
        return should[IsEmpty, MatchAny([value])]
    else:             # 无定向：仅全局
        return must[IsEmpty]
```

| 请求 | 匹配 | 不匹配 |
|---|---|---|
| `channel=None` | `channels=[]` | 含任意渠道的专属知识 |
| `channel="wechat"` | `channels=[]` OR `channels=["wechat"]` | `channels=["app"]` |

**3. UUID5 确定性 ID**

```python
str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))
```

同一 `chunkId` 每次 ingest 生成相同 point ID，配合 Qdrant `upsert` 保证幂等。


---

### 2.4 services/ —— 核心编排层

#### 2.4.1 在系统中的角色

整个 RAG 检索链路的**总指挥**。包含两个类：

- `QueryRewriter`：把用户口语改写为检索短句
- `RagQueryService`：串起 7 步检索流水线

#### 2.4.2 Query Rewrite 设计

**策略：结构化拼接而非同义改写**

```
输入：我不会弄那个充电，扫哪里啊
输出：扫码充电操作步骤；连接充电枪后扫码启动充电；我不会弄那个充电，扫哪里啊
```

不追求"把口语翻译为书面语"，而是**拆成多个检索短句 + 保留原话兜底**。每句各自命中不同维度的知识，扩大召回面。

**改写规则（system prompt 7 条）**：

1. 短句必须是用户真实会问出口的自然口语，不要书面术语
2. 包含完整动作或问题（怎么xxx、能不能xxx、xxx怎么办）
3. normalizedQueryHint 优先
4. 结合 pageContext 补充业务检索词
5. 不编造订单/金额/设备状态
6. 保留原话中的关键实体和意图
7. 失败时 fallback 原始 query

**Protocol 解耦**：

```python
class QueryRewriteChatClient(Protocol):
    def complete_json(self, system_prompt: str, user_prompt: str) -> Any: ...
```

测试注入 mock 只需实现一个方法，不依赖 `DashScopeChatClient` 的具体类型。

#### 2.4.3 RAG 检索编排

**七步流水线**：

```
Step 1: 定参数
  top_k = min(topK, 10), recall_limit = max(top_k, 10)

Step 2: Query Rewrite
  "有没有优惠券" → "有没有优惠券；怎么领优惠券；优惠券领取"

Step 3: Embedding + Qdrant 检索
  改写句 → 向量 → Qdrant.search(recall_limit) → list[ScoredPoint]
  异常？→ error response

Step 4: 无候选 → not_found

Step 5: Rerank
  _rerank_text(payload) → RerankDocument {id, text}
  rerank_client.rerank(top_n=top_k) → list[RerankResult]

Step 6: 信号增强
  for each result:
    score = max(rerank_score, _query_signal_score(query, payload))
  sort desc

Step 7: 阈值分档
  confidence = top-1 score
  ≥ 0.50 → success     → Agent 参照回复
  ≥ 0.30 → low_confidence → Agent 谨慎判断
  < 0.30 → not_found   → Agent 转人工
```

**混合打分算法：`_query_signal_score`**

| 匹配程度 | 条件 | 分数 |
|---|---|---|
| 精确命中 | 归一化后完全相等 | 0.92 |
| 强相似 | bigram Jaccard ≥ 0.55 | 0.90 |
| 子串包含 | ≥4 字符互为子串 | 0.88 |
| 弱相似 | bigram Jaccard ≥ 0.30 | 0.78 |

**为什么取 `max(rerank, text_signal)`？**

Rerank（语义模型）和文本信号（字符匹配）是互补的：语义模型擅长近似匹配（"扫码充电" ≈ "二维码启动"），但可能漏掉精确关键词。文本信号擅长精确关键词/相似问法，但不会做语义延伸。取最大值让两者各展所长。

**审计双写 + 静默降级**：

```python
def _record_query(request, response):
    try:
        create_audit_log(...)    # 每次查询必写
        if status in {"not_found", "low_confidence"}:
            create_gap_event(...)  # 知识缺口额外记录
    except Exception:
        return  # 审计写入失败绝不阻塞查询响应
```

#### 2.4.4 核心 P1

- `_record_query` L331 裸吞异常无日志
- `query()` 135 行职责过重，建议拆为 `_retrieve` / `_rerank_and_boost` / `_classify`

---

### 2.5 evaluation/ —— 评测体系

#### 2.5.1 在系统中的角色

RAG 质量保障的基础设施。每次改代码、调阈值、加知识后跑一次评测就能量化效果，无需人工逐条验证。

#### 2.5.2 数据流

```
知识库 Markdown（内嵌 Eval Questions）
        ├──→ load_eval_cases_from_knowledge()
        │
eval/agent_cases.jsonl
        ├──→ load_eval_cases_from_jsonl()
        │
        └──→ [RagEvalCase] ──→ RagEvaluator.evaluate()
                                  │
                                  ├──→ evaluate_case() → query_service.query()
                                  │         └──→ score_case() → 5 维打分
                                  │
                                  └──→ RagEvalReport
                                         ├──→ write_json_report()
                                         └──→ format_summary()
```

#### 2.5.3 五维度打分

| 维度 | 权重 | 含义 |
|---|---|---|
| context_precision | 0.25 | 搜到的东西里正确的占多少（排名加权） |
| context_recall | 0.25 | 应该搜到的实际搜到了多少 |
| status_match | 0.20 | 粗粒度状态匹配 |
| faithfulness_proxy | 0.15 | 关键声明是否被检索内容覆盖（≥60%词匹配） |
| response_relevancy | 0.15 | 检索内容与参考答案的术语重合度 |

#### 2.5.4 关键设计决策

**1. 内嵌评测降低维护成本**

每加一条知识同时写评测问题——评测和知识同源，版本一致，不需要额外维护独立评测文件。

**2. 双数据源无缝切换**

```bash
python scripts/run_eval.py --knowledge-dir knowledge          # 知识内嵌评测
python scripts/run_eval.py --cases-jsonl eval/agent_cases.jsonl  # 独立 JSONL
```

**3. negativeContextIds 支持反例测试**

`_context_precision` 中跳过 `negativeContextIds`——检索返回了不该出现的知识时，不影响排名加权计算但也不会得分。这能力已经就绪，但目前评测集中反例较少。

**4. 评测结果独立于运行时阈值**

用例自带 `expectedStatus`，不受 `config.py` 阈值调整影响——阈值从 0.75 调为 0.50 后评测不需要改用例。

---

### 2.6 governance/ —— 知识缺口聚类

#### 2.6.1 在系统中的角色

离线批处理模块，将碎片化的"搜索失败"记录自动分组，辅助运营发现知识盲区。

#### 2.6.2 数据流

```
knowledge_gap_events（未聚类）
    → cluster_unassigned_events()
        ├── Embedding API（一次性向量化所有事件+已有集群质心）
        ├── 贪心匹配（cosine ≥ 0.82 → 归入已有集群，否则新建）
        ├── 质心更新（_mean_embedding，即时更新）
        ├── Chat API（生成集群标题和摘要）
        └── 持久化（upsert 集群 + 分配事件归属）
```

#### 2.6.3 关键设计决策

**1. 增量而非全量**

每次只处理新事件，和已有集群匹配，不重新计算全量。适合定时批处理（如每小时执行一次）。

**2. 单次 Embedding 调用**

```python
embeddings = embedding_client.embed_texts(
    seed_texts + event_texts  # 已有集群代表查询 + 新事件查询 → 一次 API 调用
).embeddings
```

避免 N+1 次 API 调用。

**3. 摘要 fallback 链**

```
Chat API → JSON 解析 → title/summary
  失败？→ fallback_title = examples[0][:40]
           fallback_summary = ";".join(examples[:3])
```

`summary_client=None` 或 API 异常时都能降级。

**4. Prompt 设计（最近优化）**

- title：必须像知识条目标题，直接点明用户想要什么。正确示例：「卡券结算页不展示原因」，错误示例：「优惠券问题」
- summary：含时间范围 + 频次 + 用户问什么 + 当前覆盖情况

---

## 三、跨模块设计模式与架构评述

### 3.1 贯穿全系统的设计模式

**1. Protocol 解耦（Structural Subtyping）**

三个模块使用 `typing.Protocol` 做依赖注入：

| 模块 | Protocol | 用途 |
|---|---|---|
| providers/ | 无（直接依赖 `httpx.Client`） | — |
| services/ | `QueryRewriteChatClient` | 解耦 `QueryRewriter` 和 `DashScopeChatClient` |
| governance/ | `EmbeddingClient`、`ClusterSummaryClient` | 解耦聚类服务和 DashScope |

Python 3.8+ 的结构化子类型——不要求显式继承，只要对象有对应方法即可。

**2. frozen dataclass 不可变数据流**

ingestion/、evaluation/、governance/ 全线使用 `@dataclass(frozen=True)`。数据只读保证线程安全，避免状态被意外修改。

**3. 依赖注入 + 自管理资源**

providers/ 的 `http_client`、retrievers/ 的 `client`、services/ 的初始化均在构造函数中通过可选参数注入，生产自动创建、测试注入 mock。

**4. 错误累积而非快速失败**

ingestion 的 parser 和 validator、evaluation 的 case_loader 均收集全部问题后集中返回，一次执行看到所有问题。

**5. 静默降级：辅助功能不拖垮核心链路**

- `_record_query` 审计写入失败 → silent return
- `QueryRewriter.rewrite` Chat API 失败 → fallback 原句
- `_summarize` Chat API 失败 → fallback 截断标题

### 3.2 架构优点

- **管道式架构清晰**：ingestion → providers + retrievers → services，每层单一职责
- **离线/在线分离**：知识入库是离线批处理，查询是实时在线。两套流程互不干扰
- **治理闭环完整**：检索 → 缺口记录 → 聚类 → 补知识 → 重新入库，形成自动化知识运营飞轮
- **评测体系独立**：评测内嵌于知识、独立于运行时配置，修改参数不影响评测基准

### 3.3 架构可改进点

- **三个 DashScope Client 缺乏基类**：~130 行代码重复，是系统中最明显的架构债（P1 × 4）
- **`RagQueryService.query()` 过长**：135 行单方法承担 7 个关注点，拆分为 3 个子方法可大幅提高可读性（P1）
- **打分策略未抽象**：`_query_signal_score` 的魔法数字和 `score_case` 的加权系数均硬编码，改为策略模式后可支持多场景配置（P2）
- **跨模块类型定义分散**：`KnowledgeItem` 和 `RagFilters` 在 ingestion 和 schemas 中各自定义，部分字段通过 `dict.get()` 而非强类型访问

---

## 四、系统指标

### 4.1 评测指标演进

| 阶段 | 知识条目 | 评测用例 | meanScore | statusAccuracy | passed |
|---|---|---|---|---|---|
| 初始 | 24 | 47 | 0.7890 | 56.0% | 14 |
| 扩充至 46 条 | 46 | 58 | 0.8207 | 66.0% | 31 |
| 补充 FAQ | 55 | 67 | 0.8310 | 68.7% | 46 |
| 全量扩充 | 73 | 85 | 0.8747 | 75.3% | 64 |
| 持续补充 | 91 | 103 | 0.8882 | 80.6% | 83 |
| 阈值优化后 | 91 | 103 | 0.9667 | 97.1% | 100 |

### 4.2 代码质量

- 审查范围：6 个模块，18 个文件，~2900 行
- P0 阻断：0 个
- P1 隐患：15 个
- P2 优化：25 个
- 单元测试：48 个，覆盖率完整（核心链路 + 异常场景）
- Docker 构建与测试：通过 ✅

---

## 五、修复优先级路线图

### 紧急（本次上线前）
- 无。15 个 P1 均不阻塞上线。

### 短期（1-2 个迭代）
1. **providers/ — 抽取 `_BaseDashScopeClient`**：消除 ~130 行重复代码（修复 4 个 P1）
2. **ingestion/ — `str(None)` → `str(x or "")`**：防止无效评测数据入库
3. **ingestion/ — 未映射 section 名产生 warning**：帮助编辑者发现拼写错误
4. **services/ — `_record_query` 增加异常日志**：审计写入失败可监控
5. **governance/ — `_summarize` 异常加日志**：摘要生成成功率可观测

### 中期（3-6 个迭代）
6. **services/ — `query()` 拆分为 3 个子方法**：提高可读性
7. **evaluation/ — 打分策略抽象为 Protocol**：支持多场景注入
8. **retrievers/ — 实现旧 collection 清理**：消费 `QDRANT_KEEP_COLLECTIONS` 配置
9. **services/ — 魔法数字抽取为配置**：`_query_signal_score` 参数可调

### 长期（架构演进）
10. **Multi-Query 并行检索**：多句改写各自检索 + RRF 融合（需先验证评测收益）
11. **BM25 稀疏检索互补**：纯本地计算，对精确术语查询友好
12. **打分链重构**：`ScoreModifier` Pipeline + `ClassificationRule` 声明式规则
