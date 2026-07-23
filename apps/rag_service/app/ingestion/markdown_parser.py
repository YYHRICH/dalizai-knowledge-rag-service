from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .models import EvalQuestion, KnowledgeDocument, KnowledgeItem, ValidationIssue

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)
KNOWLEDGE_HEADING_RE = re.compile(r"^##\s+([^|｜\s]+)\s*[|｜]\s*(.+?)\s*$", re.M)
SECTION_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$", re.M)
DOCUMENT_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)

SECTION_ALIASES = {
    "summary": "Summary",
    "摘要": "Summary",
    "content": "Content",
    "正文": "Content",
    "allowed claims": "Allowed Claims",
    "允许表达": "Allowed Claims",
    "forbidden claims": "Forbidden Claims",
    "禁止表达": "Forbidden Claims",
    "keywords": "Keywords",
    "关键词": "Keywords",
    "similar questions": "Similar Questions",
    "相似问法": "Similar Questions",
    "eval questions": "Eval Questions",
    "评测问题": "Eval Questions",
}


class KnowledgeMarkdownParser:
    def parse_directory(self, base_dir: Path | str) -> tuple[list[KnowledgeDocument], list[ValidationIssue]]:
        base_path = Path(base_dir)
        documents: list[KnowledgeDocument] = []
        issues: list[ValidationIssue] = []
        for path in sorted(base_path.rglob("*.md")):
            document, document_issues = self.parse_file(path)
            issues.extend(document_issues)
            if document is not None:
                documents.append(document)
        return documents, issues

    def parse_file(self, path: Path | str) -> tuple[KnowledgeDocument | None, list[ValidationIssue]]:
        file_path = Path(path)
        issues: list[ValidationIssue] = []
        text = file_path.read_text(encoding="utf-8-sig")
        match = FRONT_MATTER_RE.match(text)
        if match is None:
            issues.append(ValidationIssue("error", file_path, "missing YAML front matter"))
            return None, issues

        metadata = self._parse_front_matter(match.group(1), file_path, issues)
        body = text[match.end() :]
        title_match = DOCUMENT_TITLE_RE.search(body)
        document_title = title_match.group(1).strip() if title_match else None
        items = self._parse_items(body, file_path, metadata, issues)
        return KnowledgeDocument(file_path, metadata, document_title, items), issues

    def _parse_front_matter(
        self,
        front_matter: str,
        path: Path,
        issues: list[ValidationIssue],
    ) -> dict[str, Any]:
        try:
            data = yaml.safe_load(front_matter) or {}
        except yaml.YAMLError as exc:
            issues.append(ValidationIssue("error", path, f"invalid YAML front matter: {exc}"))
            return {}
        if not isinstance(data, dict):
            issues.append(ValidationIssue("error", path, "front matter must be a YAML object"))
            return {}
        return data

    def _parse_items(
        self,
        body: str,
        path: Path,
        metadata: dict[str, Any],
        issues: list[ValidationIssue],
    ) -> list[KnowledgeItem]:
        headings = list(KNOWLEDGE_HEADING_RE.finditer(body))
        items: list[KnowledgeItem] = []
        if not headings:
            issues.append(ValidationIssue("error", path, "no knowledge item headings found"))
            return items

        for index, heading in enumerate(headings):
            knowledge_id = heading.group(1).strip()
            title = heading.group(2).strip()
            block_start = heading.end()
            block_end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
            block = body[block_start:block_end]
            sections = self._parse_sections(block)
            eval_questions = self._parse_eval_questions(
                sections.get("Eval Questions", ""),
                path,
                knowledge_id,
                issues,
            )
            items.append(
                KnowledgeItem(
                    knowledge_id=knowledge_id,
                    chunk_id=f"{knowledge_id}#main",
                    title=title,
                    summary=sections.get("Summary", "").strip(),
                    content=sections.get("Content", "").strip(),
                    allowed_claims=self._parse_list_section(sections.get("Allowed Claims", "")),
                    forbidden_claims=self._parse_list_section(sections.get("Forbidden Claims", "")),
                    keywords=self._parse_list_section(sections.get("Keywords", "")),
                    similar_questions=self._parse_list_section(sections.get("Similar Questions", "")),
                    eval_questions=eval_questions,
                    source_path=path,
                    document_metadata=metadata,
                )
            )
        return items

    def _parse_sections(self, block: str) -> dict[str, str]:
        matches = list(SECTION_HEADING_RE.finditer(block))
        sections: dict[str, str] = {}
        for index, match in enumerate(matches):
            raw_name = match.group(1).strip()
            canonical_name = SECTION_ALIASES.get(raw_name.lower(), raw_name)
            section_start = match.end()
            section_end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
            sections[canonical_name] = block[section_start:section_end].strip()
        return sections

    def _parse_list_section(self, text: str) -> list[str]:
        values: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                value = stripped[2:].strip()
                if value:
                    values.append(value)
        return values

    def _parse_eval_questions(
        self,
        text: str,
        path: Path,
        knowledge_id: str,
        issues: list[ValidationIssue],
    ) -> list[EvalQuestion]:
        stripped = text.strip()
        if not stripped:
            return []
        try:
            raw_items = json.loads(stripped)
        except json.JSONDecodeError as exc:
            issues.append(
                ValidationIssue(
                    "error",
                    path,
                    f"Eval Questions must be valid JSON: {exc}",
                    knowledge_id,
                )
            )
            return []
        if not isinstance(raw_items, list):
            issues.append(
                ValidationIssue("error", path, "Eval Questions must be a JSON array", knowledge_id)
            )
            return []

        parsed: list[EvalQuestion] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                issues.append(
                    ValidationIssue("error", path, "Eval Questions items must be objects", knowledge_id)
                )
                continue
            parsed.append(
                EvalQuestion(
                    question=str(raw_item.get("question", "")).strip(),
                    reference_answer=str(raw_item.get("referenceAnswer", "")).strip(),
                    expected_context_ids=list(raw_item.get("expectedContextIds") or []),
                    expected_status=str(raw_item.get("expectedStatus", "")).strip(),
                    expected_claims=list(raw_item.get("expectedClaims") or []),
                    negative_context_ids=list(raw_item.get("negativeContextIds") or []),
                    notes=raw_item.get("notes"),
                )
            )
        return parsed
