import json

from apps.rag_service.app.evaluation.case_loader import load_eval_cases_from_jsonl, load_eval_cases_from_knowledge


def test_load_eval_cases_from_jsonl(tmp_path) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "eval_001",
                "query": "怎么扫码充电？",
                "businessDomains": ["charging"],
                "knowledgeTypes": ["faq"],
                "expectedKnowledgeId": "faq_charge_scan_001",
                "expectedStatus": "success",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    cases = load_eval_cases_from_jsonl(path)

    assert len(cases) == 1
    assert cases[0].expected_context_ids == ["faq_charge_scan_001#main"]


def test_load_eval_cases_from_knowledge() -> None:
    cases = load_eval_cases_from_knowledge("knowledge")

    assert cases
    assert any(case.id == "faq_charge_scan_001__eval_01" for case in cases)
    scan_case = next(case for case in cases if case.id == "faq_charge_scan_001__eval_01")
    assert scan_case.business_domains == ["charging"]
    assert scan_case.knowledge_types == ["faq"]
    assert scan_case.expected_context_ids == ["faq_charge_scan_001#main"]
