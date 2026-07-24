"""Markdown 知识库解析器。

将 ``knowledge/`` 目录下的 Markdown 文件解析为结构化的 KnowledgeDocument。
解析约定：
- YAML front matter 作为文档级元信息（``---`` 包裹）。
- 一级标题（``#``）作为文档标题。
- 二级标题（``## knowledgeId｜标题``）作为知识条目，用 ``|`` 或 ``｜`` 分隔 ID 和标题。
- 三级标题（``###``）作为条目内的区块（Summary、Content、Keywords 等）。
- Eval Questions 区块为 JSON 数组格式的评测问题列表。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .models import EvalQuestion, KnowledgeDocument, KnowledgeItem, ValidationIssue

# ── 正则表达式 ───────────────────────────────────────────────

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)
"""匹配 YAML front matter：文件开头的 ``---`` 到 ``---`` 之间的内容。"""

KNOWLEDGE_HEADING_RE = re.compile(r"^##\s+([^|｜\s]+)\s*[|｜]\s*(.+?)\s*$", re.M)
"""匹配知识条目标题：``## knowledgeId｜标题``。支持中英文竖线。"""

SECTION_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$", re.M)
"""匹配三级标题：``### Section Name``。"""

DOCUMENT_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)
"""匹配文档一级标题：``# Document Title``。"""

# ── 三级标题的别名映射 ──────────────────────────────────────

SECTION_ALIASES = {
    # Summary
    "summary": "Summary",
    "摘要": "Summary",
    # Content
    "content": "Content",
    "正文": "Content",
    # Allowed Claims
    "allowed claims": "Allowed Claims",
    "允许表达": "Allowed Claims",
    # Forbidden Claims
    "forbidden claims": "Forbidden Claims",
    "禁止表达": "Forbidden Claims",
    # Keywords
    "keywords": "Keywords",
    "关键词": "Keywords",
    # Similar Questions
    "similar questions": "Similar Questions",
    "相似问法": "Similar Questions",
    # Eval Questions
    "eval questions": "Eval Questions",
    "评测问题": "Eval Questions",
}
"""三级标题的中英文别名映射。编辑器可能使用中文或英文标题，此处统一为规范名称。"""


class KnowledgeMarkdownParser:
    """Markdown 知识库解析器。

    负责：
    1. 遍历知识库目录，找到所有 .md 文件。
    2. 解析每个文件：提取 YAML front matter、文档标题、知识条目。
    3. 将三级标题区块映射到 KnowledgeItem 的对应字段。
    4. 解析 Eval Questions 的 JSON 数组。
    """

    def parse_directory(self, base_dir: Path | str) -> tuple[list[KnowledgeDocument], list[ValidationIssue]]:
        """解析整个知识库目录。

        递归查找所有 .md 文件，逐个解析，汇总文档和校验问题。

        Args:
            base_dir: 知识库根目录路径。

        Returns:
            (documents, issues) 元组。
            documents: 成功解析的文档（解析失败的文件不会出现在此列表中）。
            issues: 所有文件的解析和校验问题。
        """
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
        """解析单个 Markdown 文件。

        流程：
        1. 按 UTF-8 with BOM 编码读取。
        2. 提取 YAML front matter。
        3. 提取一级标题作为文档标题。
        4. 遍历二级标题，解析每个知识条目的三级标题区块。

        Args:
            path: Markdown 文件路径。

        Returns:
            (document, issues) 元组。如果 YAML front matter 缺失则 document 为 None。
        """
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
        """解析 YAML front matter 为字典。

        解析失败时记录 error 并返回空字典。
        """
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
        """解析正文中所有知识条目。

        用 ``## knowledgeId｜标题`` 正则匹配所有二级标题，
        每个标题之间的内容作为一个知识条目区块。
        条目区块内再按三级标题解析各字段。
        """
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
        """将知识条目区块按三级标题切分为字段字典。

        每个 ``### 标题`` 之间的内容归入该标题对应的字段。
        标题名称通过 SECTION_ALIASES 映射为规范名。
        """
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
