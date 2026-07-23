from pathlib import Path

from apps.rag_service.app.ingestion import (
    KnowledgeMarkdownParser,
    KnowledgeValidator,
    ValidationOptions,
)

ROOT = Path(__file__).resolve().parents[3]


def validate_directory(path: Path, require_eval_questions: bool = False):
    documents, parser_issues = KnowledgeMarkdownParser().parse_directory(path)
    return KnowledgeValidator().validate(
        documents,
        parser_issues,
        ValidationOptions(require_eval_questions=require_eval_questions),
    )


def test_mock_knowledge_dataset_is_valid() -> None:
    report = validate_directory(ROOT / "knowledge", require_eval_questions=True)

    assert report.ok, [issue.message for issue in report.errors]
    assert len(report.documents) == 12
    assert report.item_count == 24
    assert not report.warnings

    items = [item for document in report.documents for item in document.items]
    knowledge_ids = {item.knowledge_id for item in items}
    assert "faq_charge_scan_001" in knowledge_ids
    assert "coupon_stack_001" in knowledge_ids
    assert "handoff_unanswerable_001" in knowledge_ids

    scan_item = next(item for item in items if item.knowledge_id == "faq_charge_scan_001")
    assert scan_item.chunk_id == "faq_charge_scan_001#main"
    assert scan_item.business_domain == "charging"
    assert scan_item.knowledge_type == "faq"
    assert len(scan_item.eval_questions) == 2
    assert scan_item.eval_questions[0].expected_context_ids == ["faq_charge_scan_001#main"]


def test_parser_accepts_english_pipe_and_chinese_section_names(tmp_path: Path) -> None:
    knowledge_file = tmp_path / "faq.md"
    knowledge_file.write_text(
        """
---
docId: doc_test_faq_v1
docTitle: 测试 FAQ
businessDomain: general
knowledgeType: faq
riskLevel: low
status: active
ownerTeam: 测试团队
effectiveFrom: 2026-07-23T00:00:00+08:00
updatedAt: 2026-07-23T00:00:00+08:00
reviewDueAt: 2026-09-21T00:00:00+08:00
---

# 测试 FAQ

## faq_test_case_001 | 测试问题

### 摘要
测试摘要。

### 正文
测试正文。

### 允许表达
- 可以这样回答。

### 禁止表达
- 不要这样回答。

### 关键词
- 测试
- 问题

### 相似问法
- 怎么测试？
- 如何测试？
""".lstrip(),
        encoding="utf-8",
    )

    report = validate_directory(tmp_path)

    assert report.ok, [issue.message for issue in report.errors]
    item = report.documents[0].items[0]
    assert item.knowledge_id == "faq_test_case_001"
    assert item.title == "测试问题"
    assert item.summary == "测试摘要。"
    assert item.allowed_claims == ["可以这样回答。"]


def test_validator_rejects_duplicate_knowledge_id(tmp_path: Path) -> None:
    file_a = tmp_path / "a.md"
    file_b = tmp_path / "b.md"
    content = """
---
docId: {doc_id}
docTitle: 测试
businessDomain: general
knowledgeType: faq
riskLevel: low
status: active
ownerTeam: 测试团队
effectiveFrom: 2026-07-23T00:00:00+08:00
updatedAt: 2026-07-23T00:00:00+08:00
reviewDueAt: 2026-09-21T00:00:00+08:00
---

# 测试

## faq_duplicate_001｜重复问题

### Summary
摘要。

### Content
正文。

### Allowed Claims
- 可以回答。

### Forbidden Claims
- 不要回答。

### Keywords
- 重复
- 测试

### Similar Questions
- 重复吗？
- 一样吗？
"""
    file_a.write_text(content.format(doc_id="doc_a").lstrip(), encoding="utf-8")
    file_b.write_text(content.format(doc_id="doc_b").lstrip(), encoding="utf-8")

    report = validate_directory(tmp_path)

    assert not report.ok
    assert any("duplicate knowledgeId" in issue.message for issue in report.errors)


def test_validator_rejects_high_risk_without_forbidden_claims(tmp_path: Path) -> None:
    knowledge_file = tmp_path / "coupon_policy.md"
    knowledge_file.write_text(
        """
---
docId: doc_coupon_policy_test_v1
docTitle: 卡券规则
businessDomain: coupon
knowledgeType: coupon_policy
riskLevel: high
status: active
ownerTeam: 用户运营
effectiveFrom: 2026-07-23T00:00:00+08:00
updatedAt: 2026-07-23T00:00:00+08:00
reviewDueAt: 2026-08-07T00:00:00+08:00
---

# 卡券规则

## coupon_missing_forbidden_001｜高风险缺少禁止表达

### Summary
高风险摘要。

### Content
高风险正文。

### Allowed Claims
- 可以表达的内容。

### Keywords
- 卡券
- 测试
""".lstrip(),
        encoding="utf-8",
    )

    report = validate_directory(tmp_path)

    assert not report.ok
    assert any("requires Forbidden Claims" in issue.message for issue in report.errors)
