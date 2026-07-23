from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from apps.rag_service.app.evaluation.models import RagEvalReport


def report_to_dict(report: RagEvalReport) -> dict:
    return {
        "summary": asdict(report.summary),
        "results": [
            {
                "id": result.case.id,
                "query": result.case.query,
                "expectedStatus": result.case.expected_status,
                "actualStatus": result.response.status,
                "expectedContextIds": result.case.expected_context_ids,
                "retrievedContextIds": result.retrieved_context_ids,
                "retrievedKnowledgeIds": result.retrieved_knowledge_ids,
                "statusMatch": result.status_match,
                "expectedContextHit": result.expected_context_hit,
                "contextPrecision": result.context_precision,
                "contextRecall": result.context_recall,
                "faithfulnessProxy": result.faithfulness_proxy,
                "responseRelevancyProxy": result.response_relevancy_proxy,
                "score": result.score,
                "passed": result.passed,
                "confidence": result.response.confidence,
                "latencyMs": result.response.latencyMs,
            }
            for result in report.results
        ],
    }


def write_json_report(report: RagEvalReport, path: Path | str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report_to_dict(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def format_summary(report: RagEvalReport) -> str:
    summary = report.summary
    return "\n".join(
        [
            f"total={summary.total}",
            f"passed={summary.passed}",
            f"failed={summary.failed}",
            f"statusAccuracy={summary.status_accuracy:.4f}",
            f"expectedContextHitRate={summary.expected_context_hit_rate:.4f}",
            f"contextPrecision={summary.context_precision:.4f}",
            f"contextRecall={summary.context_recall:.4f}",
            f"faithfulnessProxy={summary.faithfulness_proxy:.4f}",
            f"responseRelevancyProxy={summary.response_relevancy_proxy:.4f}",
            f"meanScore={summary.mean_score:.4f}",
        ]
    )
