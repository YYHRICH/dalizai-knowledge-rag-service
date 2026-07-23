"""Run RAG retrieval evaluation."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run RAG retrieval evaluation.")
    parser.add_argument(
        "--knowledge-dir",
        default="knowledge",
        help="Knowledge directory used to load Markdown Eval Questions.",
    )
    parser.add_argument(
        "--cases-jsonl",
        default=None,
        help="Optional JSONL eval cases. If omitted, load cases from Markdown Eval Questions.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of eval cases.")
    parser.add_argument(
        "--output",
        default=None,
        help="JSON report path. Defaults to eval/reports/rag_eval_<timestamp>.json.",
    )
    parser.add_argument(
        "--include-not-called",
        action="store_true",
        help="Include cases where shouldCallRag=false. Defaults to skip them for RAG retrieval eval.",
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        default=0.75,
        help="Exit with code 1 if meanScore is below this threshold.",
    )
    return parser


def timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def main() -> int:
    from apps.rag_service.app.core.config import settings
    from apps.rag_service.app.evaluation.case_loader import (
        load_eval_cases_from_jsonl,
        load_eval_cases_from_knowledge,
    )
    from apps.rag_service.app.evaluation.evaluator import RagEvaluator
    from apps.rag_service.app.evaluation.reporting import format_summary, write_json_report
    from apps.rag_service.app.services.rag_query_service import RagQueryService

    load_dotenv(PROJECT_ROOT / ".env")
    args = build_parser().parse_args()
    if args.cases_jsonl:
        cases = load_eval_cases_from_jsonl(PROJECT_ROOT / args.cases_jsonl)
        case_source = args.cases_jsonl
    else:
        cases = load_eval_cases_from_knowledge(PROJECT_ROOT / args.knowledge_dir)
        case_source = args.knowledge_dir
    skipped_not_called = 0
    if not args.include_not_called:
        before = len(cases)
        cases = [case for case in cases if case.should_call_rag and case.expected_status != "not_called"]
        skipped_not_called = before - len(cases)
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        print(f"caseSource={case_source}")
        print("total=0")
        print("status=no_cases")
        return 2

    report = RagEvaluator(RagQueryService(settings)).evaluate(cases)
    output = Path(args.output) if args.output else PROJECT_ROOT / "eval" / "reports" / f"rag_eval_{timestamp()}.json"
    write_json_report(report, output)

    print(f"caseSource={case_source}")
    print(f"skippedNotCalled={skipped_not_called}")
    print(f"report={output}")
    print(format_summary(report))
    if report.summary.mean_score < args.fail_under:
        print(f"status=failed threshold={args.fail_under:.4f}")
        return 1
    print("status=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
