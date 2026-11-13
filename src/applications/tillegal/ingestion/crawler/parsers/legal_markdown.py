"""Parse normalized legal Markdown into structure, blocks, and retrieval chunks."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from src.integrations.database.repositories.parsed_document_repository import (
    DocumentBlockWrite,
    DocumentNodeWrite,
    DocumentStructureWrite,
    ParsedDocumentWrite,
    RetrievalChunkWrite,
)

SCHEMA_VERSION = "legal-structure-v1"
PARSER_VERSION = "vbpl-markdown-v1"
DEFAULT_MAX_CHUNK_TOKENS = 480
_SECTION_HEADING = re.compile(
    r"^(?:#{1,6}\s*)?(Chương|Phần|Mục|Tiểu mục)\s+"
    r"([IVXLCDM]+|\d+(?:\.\d+)*)(?:\s*[.:–—-]\s*|\s+)?(.*)$",
    re.IGNORECASE,
)
_ARTICLE_HEADING = re.compile(r"^(?:#{1,6}\s*)?Điều\s+(\d+[a-zA-Z]?)(?:\s*[.:–—-]\s*|\s+)?(.*)$", re.IGNORECASE)
_CLAUSE = re.compile(r"^(\d+)\.\s+(.+)$")
_POINT = re.compile(r"^([a-zđ])\)\s*(.*)$", re.IGNORECASE)
_INLINE_MARKDOWN = re.compile(r"\[([^\]]+)\]\([^)]+\)|\*\*|__|~~|`|\*|_")


@dataclass(frozen=True)
class _SourceLine:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class _NodeContext:
    node_id: str
    kind: str
    label: str | None
    parent_node_id: str | None


def parse_legal_markdown(
    markdown: str,
    *,
    source_document_id: UUID,
    title: str,
    token_counter: Callable[[str], int] | None = None,
    max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
) -> ParsedDocumentWrite:
    """Create persisted structure and chunks using legal boundaries and breadcrumb context."""
    if not markdown.strip():
        raise ValueError("Cannot parse empty VBPL Markdown")
    if not title.strip():
        raise ValueError("VBPL document title must not be blank")
    if max_chunk_tokens < 16:
        raise ValueError("max_chunk_tokens must be at least 16")

    count_tokens = token_counter or _estimate_tokens
    nodes: list[DocumentNodeWrite] = []
    blocks: list[DocumentBlockWrite] = []
    root = _NodeContext("document", "document", title.strip(), None)
    nodes.append(DocumentNodeWrite(node_id=root.node_id, kind=root.kind, label=root.label))
    current_sections: list[_NodeContext] = []
    current_article: _NodeContext | None = None
    current_clause: _NodeContext | None = None
    used_node_ids = {root.node_id}

    for group in _paragraphs(markdown):
        rendered_lines = [line for line in group if line.text.strip()]
        if not rendered_lines:
            continue
        if all(line.text.lstrip().startswith("|") for line in rendered_lines):
            block_text = "\n".join(_clean_line(line.text) for line in rendered_lines)
            _append_block(
                blocks,
                block_text,
                _nearest_context(current_article, current_sections, root).node_id,
                "table",
                rendered_lines[0].start,
                rendered_lines[-1].end,
            )
            continue

        text = " ".join(line.text.strip() for line in rendered_lines)
        cleaned = _clean_line(text)
        section_match = _SECTION_HEADING.match(cleaned)
        if section_match is not None:
            section_kind, number, heading = section_match.groups()
            normalized_kind = section_kind.lower()
            if normalized_kind in {"chương", "phần"}:
                parent = root
                current_sections = []
                node_kind = "chapter" if normalized_kind == "chương" else "part"
            else:
                depth = 2 if normalized_kind == "tiểu mục" else 1
                parent = current_sections[min(depth - 1, len(current_sections) - 1)] if current_sections else root
                current_sections = current_sections[:depth]
                node_kind = "subsection" if depth == 2 else "section"
            label = _make_label(_normalized_section_kind(normalized_kind), number, heading)
            node_id = _unique_node_id(
                _slug(f"{node_kind}-{number}"),
                parent.node_id,
                used_node_ids,
            )
            sibling_ordinal = 1 + sum(
                node.parent_node_id == parent.node_id and node.kind == node_kind for node in nodes
            )
            block_id = _next_block_id(len(blocks))
            context = _NodeContext(node_id, node_kind, label, parent.node_id)
            nodes.append(
                DocumentNodeWrite(
                    node_id=node_id,
                    parent_node_id=parent.node_id,
                    kind=node_kind,
                    label=label,
                    scope=label,
                    heading_block_id=block_id,
                    ordinal=sibling_ordinal,
                )
            )
            _append_block(
                blocks,
                label,
                node_id,
                "heading",
                rendered_lines[0].start,
                rendered_lines[-1].end,
                block_id=block_id,
            )
            current_sections.append(context)
            current_article = None
            current_clause = None
            continue

        article_match = _ARTICLE_HEADING.match(cleaned)
        if article_match is not None:
            number, heading = article_match.groups()
            parent = current_sections[-1] if current_sections else root
            label = f"Điều {number}: {heading.strip()}" if heading.strip() else f"Điều {number}"
            node_id = _unique_node_id(
                _slug(f"article-{number}"),
                parent.node_id,
                used_node_ids,
            )
            block_id = _next_block_id(len(blocks))
            current_article = _NodeContext(node_id, "article", label, parent.node_id)
            sibling_ordinal = 1 + sum(
                node.parent_node_id == parent.node_id and node.kind == "article" for node in nodes
            )
            nodes.append(
                DocumentNodeWrite(
                    node_id=node_id,
                    parent_node_id=parent.node_id,
                    kind="article",
                    label=label,
                    scope=label,
                    heading_block_id=block_id,
                    ordinal=sibling_ordinal,
                )
            )
            _append_block(
                blocks,
                label,
                node_id,
                "heading",
                rendered_lines[0].start,
                rendered_lines[-1].end,
                block_id=block_id,
            )
            current_clause = None
            continue

        for line in rendered_lines:
            cleaned_line = _clean_line(line.text)
            if not cleaned_line:
                continue
            clause_match = _CLAUSE.match(cleaned_line)
            point_match = _POINT.match(cleaned_line)
            if clause_match is not None and current_article is not None:
                number, body = clause_match.groups()
                clause_id = _unique_node_id(
                    _slug(f"clause-{number}"),
                    current_article.node_id,
                    used_node_ids,
                )
                clause_label = f"Khoản {number}"
                current_clause = _NodeContext(clause_id, "clause", clause_label, current_article.node_id)
                nodes.append(
                    DocumentNodeWrite(
                        node_id=clause_id,
                        parent_node_id=current_article.node_id,
                        kind="clause",
                        label=clause_label,
                        scope=current_article.label,
                        ordinal=int(number),
                    )
                )
                _append_block(blocks, f"{number}. {body}", clause_id, "clause", line.start, line.end)
                continue
            if point_match is not None and current_clause is not None:
                marker, body = point_match.groups()
                point_id = _unique_node_id(
                    _slug(f"point-{marker}"),
                    current_clause.node_id,
                    used_node_ids,
                )
                point_label = f"Điểm {marker.lower()}"
                nodes.append(
                    DocumentNodeWrite(
                        node_id=point_id,
                        parent_node_id=current_clause.node_id,
                        kind="point",
                        label=point_label,
                        scope=current_article.label if current_article else None,
                        ordinal="abcdđefghijklmnopqrstuvwxyz".index(marker.lower()),
                    )
                )
                _append_block(blocks, f"{marker.lower()}) {body}".strip(), point_id, "point", line.start, line.end)
                continue

            owner = current_clause or current_article or (current_sections[-1] if current_sections else root)
            block_type = "list_item" if re.match(r"^(?:[-*+]|\d+[.)])\s+", cleaned_line) else "paragraph"
            _append_block(blocks, cleaned_line, owner.node_id, block_type, line.start, line.end)

    node_by_id = {node.node_id: node for node in nodes}
    chunks = _make_chunks(
        blocks,
        node_by_id,
        title.strip(),
        count_tokens,
        max_chunk_tokens,
    )
    issues: list[dict[str, object]] = []
    if not any(node.kind == "article" for node in nodes):
        issues.append({"code": "no_articles_detected", "message": "No Điều headings were recognized."})
    if not chunks:
        raise ValueError("VBPL Markdown did not contain searchable text blocks")

    return ParsedDocumentWrite(
        structure=DocumentStructureWrite(
            source_document_id=source_document_id,
            schema_version=SCHEMA_VERSION,
            parser_version=PARSER_VERSION,
            content_sha256=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            max_chars=len(markdown),
            issues=issues,
        ),
        nodes=tuple(nodes),
        blocks=tuple(blocks),
        chunks=tuple(chunks),
    )


def _paragraphs(markdown: str) -> list[list[_SourceLine]]:
    paragraphs: list[list[_SourceLine]] = []
    current: list[_SourceLine] = []
    offset = 0
    for raw_line in markdown.splitlines(keepends=True):
        content = raw_line.rstrip("\r\n")
        start = offset
        end = start + len(content)
        offset += len(raw_line)
        if not content.strip():
            if current:
                paragraphs.append(current)
                current = []
            continue
        current.append(_SourceLine(content, start, end))
    if current:
        paragraphs.append(current)
    return paragraphs


def _clean_line(value: str) -> str:
    value = re.sub(r"^\s*#{1,6}\s*", "", value).strip()
    value = re.sub(r"\s+#+\s*$", "", value)
    value = _INLINE_MARKDOWN.sub(lambda match: match.group(1) or "", value)
    return re.sub(r"\s+", " ", value).strip()


def _make_label(kind: str, number: str, heading: str) -> str:
    label = f"{kind.title()} {number}"
    return f"{label}. {heading.strip()}" if heading.strip() else label


def _normalized_section_kind(value: str) -> str:
    return {
        "chương": "Chương",
        "phần": "Phần",
        "mục": "Mục",
        "tiểu mục": "Tiểu mục",
    }[value]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower().replace("đ", "dd")).strip("-")
    return slug or "node"


def _unique_node_id(
    base: str,
    parent_node_id: str | None,
    used_node_ids: set[str],
) -> str:
    qualified_base = base if parent_node_id in {None, "document"} else f"{parent_node_id}-{base}"
    node_id = qualified_base
    suffix = 2
    while node_id in used_node_ids:
        node_id = f"{qualified_base}-{suffix}"
        suffix += 1
    used_node_ids.add(node_id)
    return node_id


def _next_block_id(ordinal: int) -> str:
    return f"block-{ordinal + 1:06d}"


def _append_block(
    blocks: list[DocumentBlockWrite],
    content: str,
    node_id: str,
    block_type: str,
    start_offset: int,
    end_offset: int,
    *,
    block_id: str | None = None,
) -> None:
    blocks.append(
        DocumentBlockWrite(
            block_id=block_id or _next_block_id(len(blocks)),
            node_id=node_id,
            block_type=block_type,
            content=content,
            ordinal=len(blocks),
            start_offset=start_offset,
            end_offset=end_offset,
        )
    )


def _nearest_context(
    article: _NodeContext | None,
    sections: list[_NodeContext],
    root: _NodeContext,
) -> _NodeContext:
    return article or (sections[-1] if sections else root)


def _make_chunks(
    blocks: list[DocumentBlockWrite],
    nodes: dict[str, DocumentNodeWrite],
    title: str,
    token_counter: Callable[[str], int],
    max_tokens: int,
) -> list[RetrievalChunkWrite]:
    chunks: list[RetrievalChunkWrite] = []
    for block in blocks:
        if block.block_type == "heading" or not block.content.strip():
            continue
        path: list[str] = []
        node_id: str | None = block.node_id
        while node_id is not None:
            node = nodes[node_id]
            if node.kind not in {"document"} and node.label:
                path.append(node.label)
            node_id = node.parent_node_id
        path.reverse()
        breadcrumb = " > ".join([title, *path])
        prefix = f"{breadcrumb} > "
        parts = _split_content(prefix, block.content, token_counter, max_tokens)
        for part_index, part in enumerate(parts):
            content = f"{prefix}{part}"
            chunk_ordinal = len(chunks)
            chunk_key = f"legal-v1-{block.block_id}-{part_index + 1}"
            chunks.append(
                RetrievalChunkWrite(
                    chunk_key=chunk_key,
                    content=content,
                    content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    node_id=block.node_id,
                    block_id=block.block_id,
                    chunk_type=block.block_type,
                    ordinal=chunk_ordinal,
                    start_offset=block.start_offset,
                    end_offset=block.end_offset,
                    metadata={"block_ids": [block.block_id], "breadcrumb": breadcrumb},
                )
            )
    return chunks


def _split_content(
    prefix: str,
    content: str,
    token_counter: Callable[[str], int],
    max_tokens: int,
) -> list[str]:
    if token_counter(f"{prefix}{content}") <= max_tokens:
        return [content]
    if token_counter(prefix.rstrip()) >= max_tokens:
        raise ValueError("Legal breadcrumb exceeds the configured maximum chunk token count")

    words = re.findall(r"\S+\s*", content)
    parts: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current}{word}"
        if current and token_counter(f"{prefix}{candidate}") > max_tokens:
            parts.append(current.strip())
            current = word
            if token_counter(f"{prefix}{current}") > max_tokens:
                raise ValueError("A single word exceeds the configured maximum chunk token count")
        else:
            current = candidate
    if current.strip():
        parts.append(current.strip())
    return parts


def _estimate_tokens(text: str) -> int:
    return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))
