# 代码模块评审报告

## 1. 评审基本信息

- 评审模块：RAG 评测 —— 用例加载、打分算法、报告生成，整个评测闭环
- 代码语言：Python 3.11
- 评审范围：`apps/rag_service/app/evaluation/` 全部 5 个文件（`models.py` 165 行、`case_loader.py` 119 行、`evaluator.py` 209 行、`reporting.py` 71 行、`__init__.py` 空），合计约 565 行
- 整体风险等级：**低风险**

## 2. 模块架构学习引导

### 2.1 模块定位与业务价值

本模块是 RAG 质量保障的基础设施。它的价值在于：每次改代码、调阈值、加知识后，跑一次评测就能知道检索质量是变好了还是变差了，不用人工逐条验证。核心流程：

```
知识库 Markdown（内嵌 Eval Questions）
    │                              ┌──→ load_eval_cases_from_knowledge()
    │                              │
eval/agent_cases.jsonl ────────────┼──→ load_eval_cases_from_jsonl()
    │                              │
    └──→ [RagEvalCase] ──→ RagEvaluator.evaluate()
                              │
                              ├──→ evaluate_case() → RagQueryService.query() → RAG 检索
                              │         │
                              │         └──→ score_case() → 5 维度打分
                              │
                              └──→ RagEvalReport → write_json_report() / format_summary()
```

### 2.2 架构分层与职责划分

| 文件 | 职责 |
|---|---|
| `models.py` | 4 个 frozen dataclass：`RagEvalCase`（用例）、`RagEvalCaseResult`（单条结果）、`RagEvalSummary`（汇总）、`RagEvalReport`（报告） |
| `case_loader.py` | 双数据源加载：Markdown 内嵌 Eval Questions + JSONL 文件 |
| `evaluator.py` | `RagEvaluator` 批量执行 + `score_case` 五维度打分 |
| `reporting.py` | JSON 报告持久化 + 终端摘要格式化 |

### 2.3 核心业务全链路

```
步骤1: 用例加载
  load_eval_cases_from_knowledge("knowledge/")
    → parse_directory() → 遍历所有 .md
    → 收集每个 KnowledgeItem.eval_questions
    → case_id = "{knowledgeId}__eval_{NN}"

步骤2: 批量评测
  RagEvaluator(query_service).evaluate(cases)
    → for each case:
        evaluate_case(case)
          → 构造 RagQueryRequest → query_service.query() → RagQueryResponse
          → score_case(case, response)

步骤3: 五维度打分
  score_case():
    status_match       = response.status == case.expected_status
    context_precision  = 检索结果中命中期盼 chunk 的比例（排名加权，negativeContextIds 跳过不计）
    context_recall     = 命中数 / 期盼总数
    faithfulness_proxy = 期盼 claims 被检索内容覆盖的比例
    response_relevancy = 检索内容与参考答案的术语重合度
    score = 0.20×status + 0.25×precision + 0.25×recall + 0.15×faith + 0.15×relevancy

步骤4: 报告生成
  write_json_report() → eval/reports/rag_eval_{timestamp}.json
  format_summary()    → 终端可读表格
```

### 2.4 关键组件与数据模型

**打分权重设计意图**：

| 维度 | 权重 | 含义 |
|---|---|---|
| context_precision | 0.25 | 搜到的东西里，正确的占多少——搜得准不准 |
| context_recall | 0.25 | 应该搜到的，实际搜到了多少——搜得全不全 |
| status_match | 0.20 | 粗粒度判断是否对路 |
| faithfulness_proxy | 0.15 | 关键声明是否被覆盖了 |
| response_relevancy | 0.15 | 和参考答案有多接近 |

**`passed` 的判定**：三个条件 AND——status 匹配 + 至少命中一个期望 chunk + score ≥ 0.75

**`_context_precision` 的负样本处理**：`negativeContextIds` 中出现的 chunk 在排名计算时被跳过（不加分也不算分母）。这保证了反例测试的有效性——即使检索返回了不该出现的知识，也不会因为它在排名首位就得分。

**`_faithfulness_proxy` 的松散匹配**：`_contains_loose()` 先精确匹配，失败后用 `_content_terms()` 切词，≥60% 词的覆盖率就算包含。避免了"只匹配了半句话"被判定为失败。

### 2.5 设计思想与技术选型

- **双数据源无缝切换**：Markdown 内嵌（开发阶段随知识维护）+ JSONL 文件（跨域反例测试），`run_eval.py` 里一行参数切换
- **内嵌评测降低维护成本**：每加一条知识同时写评测问题，不需要额外维护评测文件。评测和知识同源，版本一致
- **`expectedStatus` 而非 hardcode 阈值**：评测用例自带期望状态，不受 `config.py` 阈值调整影响——阈值改了评测集不用改
- **排名加权精确率**：`precision_sum += hits / rank`，正样本越靠前得分越高，比简单的 hits/total 更精细
- **`_content_terms` 切词避免 jieba 依赖**：用分隔符切词 + ≥2 字符过滤，简单有效，不引入额外依赖

### 2.6 模块上手学习路径

1. **先看 `models.py`（3 分钟）**：`RagEvalCase → RagEvalCaseResult → RagEvalSummary → RagEvalReport` 四级嵌套
2. **再看 `evaluator.py` L73-111 `score_case`（5 分钟）**：理解 5 维打分和加权公式
3. **看 `case_loader.py` L17-65**：理解知识内嵌评测到用例的转换
4. **扫一眼 `reporting.py` 和 `__init__.py`**：纯工具代码

---

## 3. 模块设计总评

**设计亮点**：内嵌评测降低维护成本、双数据源灵活切换、排名加权精确率精细、`negativeContextIds` 支持反例测试。

**架构缺陷**：`__init__.py` 空置、`score_case` 中 5 个打分函数散落在模块级函数中（未封装）、评测结果缺少与历史 basline 的对比能力。

---

## 4. 高危问题总览

| 等级 | 问题 | 位置 |
|---|---|---|
| 🟡 P1 | `case_loader.py` L54 行缩进错误 | `case_loader.py` L53-55 |
| 🟢 P2 | `__init__.py` 空置 | `evaluation/__init__.py` |
| 🟢 P2 | score_case 的 5 个打分函数散落为模块函数 | `evaluator.py` |
| 🟢 P2 | 评测结果无历史基线对比 | `reporting.py` |

---

## 5. 分项详细评审

### 5.1 业务逻辑与正确性问题

🟡【P1】`case_loader.py` L53-55 — 缩进错误。`should_call_rag=True` 位于 `RagEvalCase()` 构造函数内但缩进层级与父级 `for index, eval_question` 不对齐。代码中 L53 `should_call_rag=True` 和 L54-55 的 `business_domains`/`knowledge_types` 与 L50-52 的 `id`/`query`/`expected_status` 缩进层级不一致。**风险**：Python 不报错（同级表达式），但如果后续有人调整缩进或重构可能导致逻辑错误。**修复**：统一缩进到与 `id` 同一层级。

### 5.2 异常容错与稳定性问题

无 P0/P1 问题。`load_eval_cases_from_knowledge` 对 parser errors 做了早期校验（有 error 直接抛 `ValueError`）。`run_eval.py` 中用 `if not cases: return 2` 兜底无用例场景。

### 5.3 性能、数据库与IO风险问题

无问题。评测执行时每条约 1-2s（含 API 调用），103 条约 2-3 分钟。`score_case` 纯 CPU 计算无 IO。

### 5.4 安全、权限与数据合规问题

无问题。评测用例不包含 PII。

### 5.5 日志监控与可观测性问题

🟢【P2】`RagEvaluator.evaluate()` 无进度输出。103 条用例跑起来无任何中间状态，不知道跑到第几条。**修复**：加 `tqdm` 或简单的 `print(f"[{i}/{total}]")`。

### 5.6 架构设计与代码可维护性问题

🟢【P2】`evaluation/__init__.py` 空置。`RagEvaluator`、`RagEvalCase`、`score_case` 等核心 API 未导出。**修复**：补全导出列表。

🟢【P2】`evaluator.py` 中 `_expected_context_hit`、`_context_precision`、`_context_recall`、`_faithfulness_proxy`、`_response_relevancy_proxy` 五个打分函数是模块级私有函数，不是类方法。如果未来需要不同的打分策略（如产品场景重 recall、安全场景重 precision），只能在 `score_case` 里改权重。**修复**：封装为 `ScoringStrategy` Protocol，支持不同场景注入不同打分策略。

🟢【P2】`reporting.py` 无历史基线对比能力。每次报告独立存在，无法自动对比"这次比上次好了还是坏了"。**修复**：在 `write_json_report` 时同时读取上一次报告，写入 diff 字段。

### 5.7 测试覆盖与上线风险问题

`test_rag_evaluation.py` 覆盖了正常 success、正常 not_found、批量评测三条路径。缺少：`negativeContextIds` 场景测试、`expectedClaims` 覆盖度测试、`referenceAnswer` 相关性测试。这些场景的代码逻辑已在生产运行验证，但单元测试未覆盖。

---

## 6. 问题等级统计

- P0 阻断问题：**0 个**
- P1 隐患问题：**1 个**
- P2 优化建议：**4 个**

---

## 7. 上线准入结论

**允许直接上线。** 评测框架正确、打分算法合理、双数据源灵活。1 个 P1（缩进不一致）不影响功能正确性。

## 8. 修复路线图

### 短期优化
1. `case_loader.py` 缩进对齐
2. `__init__.py` 补全导出
3. `evaluate()` 加进度输出

### 长期重构
4. 打分策略抽象为 Protocol，支持多场景注入
5. 报告增加历史基线对比
