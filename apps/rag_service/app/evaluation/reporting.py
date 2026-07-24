"""评测报告生成工具。

将评测结果序列化为 JSON 文件或终端可读的摘要文本。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from apps.rag_service.app.evaluation.models import RagEvalReport


def report_to_dict(report: RagEvalReport) -> dict:
    """将评测报告转为可序列化的字典。"""
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
    """将评测报告写入 JSON 文件。自动创建父目录。"""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report_to_dict(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def format_summary(report: RagEvalReport) -> str:
    """格式化为终端可读的评测摘要文本。"""
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
