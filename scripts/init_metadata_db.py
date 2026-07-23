"""Initialize the RAG metadata SQLite database."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize RAG metadata SQLite database.")
    parser.add_argument(
        "--db-url",
        default=None,
        help="SQLite DB URL. Defaults to RAG_METADATA_DB_URL or sqlite:///data/rag_service.db.",
    )
    return parser


def main() -> int:
    from apps.rag_service.app.storage import MetadataRepository, SqliteDatabase

    load_dotenv(PROJECT_ROOT / ".env")
    args = build_parser().parse_args()
    db_url = args.db_url or os.getenv("RAG_METADATA_DB_URL") or "sqlite:///data/rag_service.db"
    repository = MetadataRepository(SqliteDatabase(db_url))
    repository.initialize()
    print(f"metadataDb={db_url}")
    print("status=initialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
