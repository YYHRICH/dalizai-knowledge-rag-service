"""Validate knowledge Markdown files before full ingestion.

This is the first ingestion milestone. Later milestones will add embedding, Qdrant
collection creation, smoke evaluation, and alias switching.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate knowledge Markdown files.")
    parser.add_argument(
        "--knowledge-dir",
        default="knowledge",
        help="Knowledge base directory. Defaults to ./knowledge.",
    )
    parser.add_argument(
        "--require-eval-questions",
        action="store_true",
        help="Require Eval Questions for mock/evaluation datasets.",
    )
    return parser


def main() -> int:
    from apps.rag_service.app.ingestion import (
        KnowledgeMarkdownParser,
        KnowledgeValidator,
        ValidationOptions,
    )

    args = build_parser().parse_args()
    knowledge_dir = Path(args.knowledge_dir)
    documents, parser_issues = KnowledgeMarkdownParser().parse_directory(knowledge_dir)
    report = KnowledgeValidator().validate(
        documents,
        parser_issues,
        ValidationOptions(require_eval_questions=args.require_eval_questions),
    )

    print(f"knowledgeDir={knowledge_dir}")
    print(f"documents={len(report.documents)}")
    print(f"items={report.item_count}")
    print(f"errors={len(report.errors)}")
    print(f"warnings={len(report.warnings)}")

    for issue in report.errors:
        prefix = f"ERROR {issue.path}"
        if issue.knowledge_id:
            prefix += f"#{issue.knowledge_id}"
        print(f"{prefix}: {issue.message}")
    for issue in report.warnings:
        prefix = f"WARNING {issue.path}"
        if issue.knowledge_id:
            prefix += f"#{issue.knowledge_id}"
        print(f"{prefix}: {issue.message}")

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
