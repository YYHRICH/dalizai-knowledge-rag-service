# 代码模块评审报告

## 1. 评审基本信息

- 评审模块：知识缺口聚类 —— 将相似的"未命中/低置信度"查询自动分组，辅助运营发现知识盲区
- 代码语言：Python 3.11
- 评审范围：`apps/rag_service/app/governance/` 全部 2 个文件（`gap_clustering.py` 288 行、`__init__.py` 空）
- 整体风险等级：**中风险**

## 2. 模块架构学习引导

### 2.1 模块定位与业务价值

本模块解决一个运营痛点：RAG 每天产生大量"搜不到"或"不敢确定"的查询记录，运营不可能逐条看。聚类服务把这些碎片自动分组，生成"最近很多用户在问充电中途停止的问题但知识库没覆盖"这样的摘要，让运营知道该补哪些知识。

在系统中的位置——离线批处理，不参与在线查询链路：

```
RAG 查询（每次 not_found / low_confidence）
    → knowledge_gap_events 表（未聚类状态）
    → [定时/手动执行] GapClusteringService.cluster_unassigned_events()
    → 知识缺口集群（knowledge_gap_clusters 表）
    → 管理后台查看 → 运营决策：补充知识 / 忽略
```

### 2.2 架构分层与职责划分

单文件模块，但内部有三层结构：

| 层 | 组件 | 职责 |
|---|---|---|
| 数据模型 | `GapClusterCandidate`、`GapClusteringResult` | 聚类过程的中间结果和最终统计 |
| 算法核心 | `GapClusteringService` | 增量聚类 + 摘要生成 |
| 依赖接口 | `EmbeddingClient`、`ClusterSummaryClient` Protocol | 解耦 DashScope 依赖 |

### 2.3 核心业务全链路

```
步骤1: 数据准备
   list_unclustered_gap_events(limit=100)
   list_open_gap_clusters()
   合并 seed_texts + event_texts → 一次 Embedding API 调用拿到所有向量

步骤2: 贪心匹配聚类
   for each event:
       _best_group() → 计算与所有已有/新建集群质心的余弦相似度
       if max_similarity >= 0.82:
           归入该集群 → _mean_embedding() 更新质心
       else:
           创建新集群（initial 质心 = 该事件向量）

步骤3: 摘要生成
   for each changed group:
       _build_candidate():
           → 合并 query_examples（新旧拼接，去重，最多5条）
           → 统计 status_breakdown（not_found vs low_confidence 分布）
           → 推测 business_domain_guess / knowledge_type_guess（多数投票）
           → _summarize(): Chat API 生成标题和摘要（失败 → fallback: 第一条查询截断）

步骤4: 持久化
   if not dry_run:
       for candidate:
           upsert_gap_cluster()  → INSERT OR UPDATE 集群
           assign_gap_events_to_cluster() → UPDATE 事件的 cluster_id
```

### 2.4 关键组件与数据模型

**增量聚类的核心——质心更新**：

```python
_mean_embedding([existing_centroid, e1, e2, e3, ...])
  = 所有事件向量的算术平均
```

这不是严格的 k-means（k-means 做完所有分配才更新质心），而是**在线贪心**——每分配一个事件就立即更新质心。好处是后续事件能看到更准确的集群中心，坏处是对事件顺序敏感。

**`_build_candidate` 的多数投票**：

```python
business_domain_guess = _most_common(
    [existing.business_domain_guess] + [event.domain_guess for event in events]
)
```

新旧数据一起投票，已有的 guess 也算一票。这样存量 100 个事件的集群不会被新增 1 个事件就改变猜测结果。

**摘要生成的 fallback 链**：

```
Chat API → JSON 解析 → title/summary
  失败? → fallback_title = examples[0][:40]（截断第一条查询）
           fallback_summary = ";".join(examples[:3])
```

没有 Chat API 也能跑（`summary_client=None` 或 API 异常），降级到规则生成。

### 2.5 设计思想与技术选型

- **增量而非全量**：每次只处理新事件，和已有集群匹配，不重新计算全量。适合定时批处理场景
- **单次 Embedding 调用**：所有 seed + event 文本一次性向量化，避免多次 API 调用
- **贪心匹配 + 即时质心更新**：简单高效，比 k-means 迭代更适合增量场景
- **Protocol 双接口**：Embedding 和 Summary 都通过 Protocol 解耦，测试可独立 mock
- **dry_run 模式**：预览聚类结果不写入，运营可以先看效果再确认执行

### 2.6 模块上手学习路径

1. **先看数据结构** L37-62：`GapClusterCandidate` 和 `GapClusteringResult`
2. **看 `cluster_unassigned_events` L95-183**：核心算法，顺着 4 个步骤读
3. **看 `_build_candidate` L191-228**：理解集群属性怎么从新旧数据合并
4. **扫 `_cosine_similarity`、`_mean_embedding`、`_dedupe`、`_most_common`**：纯工具函数

---

## 3. 模块设计总评

**设计亮点**：增量贪心匹配 + 即时质心更新适合批处理、单次 Embedding 调用高效、dry_run 预览机制贴心、摘要 fallback 健壮。

**架构缺陷**：贪心匹配对事件顺序敏感——不同顺序可能产生不同聚类结果。`_best_group` 在 group 数量增长时线性退化。

---

## 4. 高危问题总览

| 等级 | 问题 | 位置 |
|---|---|---|
| 🟡 P1 | 贪心聚类对事件顺序敏感 | `gap_clustering.py` L135-152 |
| 🟡 P1 | `_summarize` 异常静默无日志 | `gap_clustering.py` L252-256 |
| 🟢 P2 | `_best_group` 每次 O(n) 遍历 | `gap_clustering.py` L185-189 |
| 🟢 P2 | `groups + new_groups` 循环内拼接 | `gap_clustering.py` L136 |
| 🟢 P2 | `__init__.py` 空置 | `governance/__init__.py` |

---

## 5. 分项详细评审

### 5.1 业务逻辑与正确性问题

🟡【P1】L135-152 — 贪心聚类对事件顺序敏感。 `list_unclustered_gap_events` 按 `created_at ASC` 排序，稳定但语义上未必最优——先来的事件可能创建了一个"不够精准"的集群，后续更匹配的事件本应合并但阈值刚好差一点。**风险**：同一批事件在不同时间点执行聚类（比如只处理了前 50 条 vs 全量 100 条），集群划分可能不同。**修复**：在 `_best_group` 返回所有超过阈值的 group 而非只取最高分，再按次高分打破平局；或两趟扫描（第一趟建群、第二趟重新分配）。

### 5.2 异常容错与稳定性问题

🟡【P1】L252-256 — `_summarize` 的 `except (ModelProviderError, json.JSONDecodeError, TypeError, ValueError): return fallback` 无日志。Chat API 调用失败时静默退回截断标题，运营看到的集群标题全是 `examples[0][:40]`，无法判断是 API 坏了还是数据本来就这样。**修复**：加 `logging.warning(f"Cluster summary failed: {exc}")`。

### 5.3 性能、数据库与IO风险问题

🟢【P2】L185-189 — `_best_group` 对每个事件遍历全部 group。100 个事件 × 50 个 group = 5000 次余弦相似度计算，每次 O(1024)。总量不大但 O(n*m) 增长。如果累积几百个 open 集群，会变慢。**修复**：当 group 数量超过阈值时用向量近似最近邻（如 faiss）加速，当前规模不需要。

🟢【P2】L136 — `groups + new_groups` 在循环体内每次迭代都创建新列表。100 个事件 = 100 次列表拼接。**修复**：用 `itertools.chain(groups, new_groups)` 或维护一个 `all_groups` 引用。

### 5.4 安全、权限与数据合规问题

无问题。聚类的输入 `query_masked` 已经过 PII 脱敏。

### 5.5 日志监控与可观测性问题

🟢【P2】`cluster_unassigned_events` 无进度日志。长时间运行时（limit 很大）无法知道进度。**修复**：加 `logging.info(f"Clustering {len(events)} events...")`。

### 5.6 架构设计与代码可维护性问题

🟢【P2】`governance/__init__.py` 空置。**修复**：导出 `GapClusteringService`、`GapClusterCandidate`、`GapClusteringResult`。

### 5.7 测试覆盖与上线风险问题

`test_gap_clustering.py` 覆盖了正常聚类和 dry_run 两个场景。缺少：Embedding API 异常场景、Chat API 异常场景、空 events 边界、大量 group 下性能退化测试。

---

## 6. 问题等级统计

- P0 阻断问题：**0 个**
- P1 隐患问题：**2 个**
- P2 优化建议：**4 个**

---

## 7. 上线准入结论

**允许直接上线。** 聚类算法正确，增量设计适合批处理场景。2 个 P1（顺序敏感性、摘要异常无日志）在离线批处理场景下影响有限——人工执行时集群划分的微小差异不影响运营决策。

## 8. 修复路线图

### 短期优化
1. `_summarize` 异常加日志
2. `cluster_unassigned_events` 加进度日志
3. `__init__.py` 补全导出

### 长期重构
4. `_best_group` 改为两趟扫描减少顺序敏感
5. `groups + new_groups` 改为 iterator 避免循环内拼接
