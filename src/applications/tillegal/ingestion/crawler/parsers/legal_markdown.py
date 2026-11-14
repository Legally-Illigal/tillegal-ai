"""Parse normalized legal Markdown into structure, blocks, and retrieval chunks."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from html import unescape
from uuid import UUID

from src.integrations.database.repositories.parsed_document_repository import (
    DocumentBlockWrite,
    DocumentNodeWrite,
    DocumentStructureWrite,
    ParsedDocumentWrite,
    RetrievalChunkWrite,
)

SCHEMA_VERSION = "legal-structure-v1"
PARSER_VERSION = "vbpl-markdown-v7"
DEFAULT_MAX_CHUNK_TOKENS = 480
_SECTION_HEADING = re.compile(
    r"^(?:#{1,6}\s*)?(Chương|Phần|Mục|Tiểu mục)\s+"
    r"([IVXLCDM]+|\d+(?:\.\d+)*)(?:\s*[.:–—-]\s*|\s+)?(.*)$",
    re.IGNORECASE,
)
_ARTICLE_HEADING = re.compile(r"^(?:#{1,6}\s*)?Điều\s+(\d+[a-zA-Z]?)(?:\s*[.:–—-]\s*|\s+)?(.*)$", re.IGNORECASE)
_ARTICLE_INLINE_BODY = re.compile(
    r"^\s*(?P<marker>\*\*|__)(?P<label>Điều\s+\d+[a-zA-Z]?[.:])(?P=marker)\s+(?P<body>\S.*)$",
    re.IGNORECASE | re.DOTALL,
)
_CLAUSE = re.compile(r"^(\d+)\.\s+(.+)$")
_POINT = re.compile(r"^([a-zđ])\)\s*(.*)$", re.IGNORECASE)
_APPENDIX = re.compile(
    r"^PHỤ LỤC(?:\s+(?:[IVXLCDM]+|\d+[a-z]?))?(?:\s*[.:–—-]\s*\S.*)?$", re.IGNORECASE
)
_FORM = re.compile(r"^Mẫu số\s+\d+[a-zA-Z]?(?:[/.-][\w-]+)*(?:\s*[:.–-]\s*.*)?$", re.IGNORECASE)
_ATTACHED_TITLE = re.compile(r"^(?:QUYẾT ĐỊNH|NGHỊ QUYẾT|QUY CHẾ|QUY ĐỊNH)$")
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
    current_point: _NodeContext | None = None
    used_node_ids = {root.node_id}
    current_appendix: _NodeContext | None = None
    current_attachment: _NodeContext | None = None

    groups = _paragraphs(markdown)
    for group_index, group in enumerate(groups):
        rendered_lines = [line for line in group if line.text.strip()]
        if not rendered_lines:
            continue
        if all(line.text.lstrip().startswith("|") for line in rendered_lines):
            block_text = "\n".join(_clean_line(line.text) for line in rendered_lines)
            _append_block(
                blocks,
                block_text,
                (current_point or current_clause or _nearest_context(current_article, current_sections, root)).node_id,
                "table",
                rendered_lines[0].start,
                rendered_lines[-1].end,
            )
            continue

        text = " ".join(line.text.strip() for line in rendered_lines)
        cleaned = _clean_line(text)
        appendix_heading = _APPENDIX.fullmatch(cleaned)
        form_heading = _FORM.fullmatch(cleaned)
        attached_heading = _ATTACHED_TITLE.fullmatch(cleaned) if current_appendix else None
        # A document-type title following an explicit form label belongs to that form.
        previous_index = group_index - 1
        # Masthead tables between a form number and its title do not start a new form.
        while previous_index >= 0 and groups[previous_index][0].text.lstrip().startswith("|"):
            previous_index -= 1
        previous_text = (
            _clean_line(" ".join(line.text for line in groups[previous_index])) if previous_index >= 0 else ""
        )
        if attached_heading and _FORM.fullmatch(previous_text):
            attached_heading = None
        if appendix_heading or form_heading or attached_heading:
            if appendix_heading:
                kind, parent = "appendix", root
            else:
                kind, parent = "attachment", current_appendix or root
            ordinal = 1 + sum(node.parent_node_id == parent.node_id and node.kind == kind for node in nodes)
            node_id = _unique_node_id(f"{kind}-{ordinal}", parent.node_id, used_node_ids)
            block_id = _next_block_id(len(blocks))
            context = _NodeContext(node_id, kind, cleaned, parent.node_id)
            nodes.append(DocumentNodeWrite(
                node_id=node_id, parent_node_id=parent.node_id, kind=kind, label=cleaned,
                scope=cleaned, heading_block_id=block_id, ordinal=ordinal,
            ))
            _append_block(blocks, cleaned, node_id, "heading", rendered_lines[0].start,
                          rendered_lines[-1].end, block_id=block_id)
            if appendix_heading:
                current_appendix = context
                current_attachment = None
            else:
                current_attachment = context
            current_sections = [context]
            current_article = current_clause = current_point = None
            continue
        section_match = _SECTION_HEADING.match(cleaned)
        if section_match is not None:
            section_kind, number, heading = section_match.groups()
            normalized_kind = section_kind.lower()
            if normalized_kind in {"chương", "phần"}:
                parent = current_attachment or current_appendix or root
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
            current_point = None
            continue

        article_match = _ARTICLE_HEADING.match(cleaned)
        if article_match is not None:
            number, heading = article_match.groups()
            source_start = rendered_lines[0].start
            source_end = rendered_lines[-1].end
            inline_body = _ARTICLE_INLINE_BODY.match(markdown[source_start:source_end])
            # A separately bold title is still a heading, not article body text.
            if inline_body is not None and inline_body.group("body").startswith(("**", "__")):
                inline_body = None
            if inline_body is not None:
                heading = ""
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
                inline_body.group("label") if inline_body is not None else label,
                node_id,
                "heading",
                source_start,
                source_start + inline_body.end("label") + len(inline_body.group("marker"))
                if inline_body is not None
                else source_end,
                block_id=block_id,
            )
            if inline_body is not None:
                _append_block(
                    blocks,
                    _clean_line(inline_body.group("body")),
                    node_id,
                    "paragraph",
                    source_start + inline_body.start("body"),
                    source_end,
                )
            current_clause = None
            current_point = None
            continue

        for line in _logical_lines(rendered_lines):
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
                current_point = None
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
                current_point = _NodeContext(point_id, "point", point_label, current_clause.node_id)
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

            owner = (
                current_point or current_clause or current_article
                or (current_sections[-1] if current_sections else root)
            )
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
        cleaned = _clean_line(content)
        if current and (_APPENDIX.fullmatch(cleaned) or _FORM.fullmatch(cleaned)
                        or _ATTACHED_TITLE.fullmatch(cleaned)
                        or _ARTICLE_HEADING.match(cleaned) or _SECTION_HEADING.match(cleaned)
                        or _CLAUSE.match(cleaned) or _POINT.match(cleaned)):
            paragraphs.append(current)
            current = []
        current.append(_SourceLine(content, start, end))
        if _APPENDIX.fullmatch(cleaned) or _FORM.fullmatch(cleaned):
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    return paragraphs


def _logical_lines(lines: list[_SourceLine]) -> list[_SourceLine]:
    """Join soft wraps while retaining explicit list entries and source offsets."""
    result: list[_SourceLine] = []
    for line in lines:
        if result and not re.match(r"^(?:[-*+] |\d+[.)]\s|[a-zđ]\)\s)", _clean_line(line.text), re.IGNORECASE):
            previous = result[-1]
            result[-1] = _SourceLine(previous.text.rstrip() + " " + line.text.strip(), previous.start, line.end)
        else:
            result.append(line)
    return result


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
    groups: list[list[DocumentBlockWrite]] = []
    for block in blocks:
        if block.block_type == "heading" or not block.content.strip():
            groups.append([])
            continue
        if (not groups or not groups[-1] or groups[-1][-1].node_id != block.node_id
                or block.block_type == "table" or groups[-1][-1].block_type == "table"):
            groups.append([block])
        else:
            groups[-1].append(block)
    for group in groups:
        if not group:
            continue
        block = group[0]
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
        if block.block_type == "table":
            chunks.extend(_table_chunks(block, prefix, breadcrumb, token_counter, max_tokens, len(chunks)))
            continue
        context_blocks: list[str] = []
        node = nodes[block.node_id] if block.node_id is not None else None
        if node is not None and node.kind in {"point", "clause"}:
            lead = next((item for item in reversed(blocks[:block.ordinal])
                         if item.node_id == node.parent_node_id and item.block_type != "heading"), None)
            if lead is not None and lead.content.rstrip().endswith(":"):
                contextual_prefix = prefix + lead.content + "\n\n"
                if token_counter(contextual_prefix + group[0].content) <= max_tokens:
                    prefix = contextual_prefix
                    context_blocks = [lead.block_id]
        body = "\n\n".join(item.content for item in group)
        spans: list[tuple[int, int, DocumentBlockWrite]] = []
        offset = 0
        for item in group:
            spans.append((offset, offset + len(item.content), item))
            offset += len(item.content) + 2
        parts = _split_content(prefix, body, token_counter, max_tokens)
        cursor = 0
        for part_index, part in enumerate(parts):
            part_start = body.index(part, cursor)
            part_end = part_start + len(part)
            cursor = part_end
            covered = [(start, end, item) for start, end, item in spans
                       if start < part_end and end > part_start]
            first, last = covered[0][2], covered[-1][2]
            content = f"{prefix}{part}"
            chunk_ordinal = len(chunks)
            chunk_key = f"legal-v2-{block.block_id}-{part_index + 1}"
            chunks.append(
                RetrievalChunkWrite(
                    chunk_key=chunk_key,
                    content=content,
                    content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    node_id=block.node_id,
                    block_id=first.block_id,
                    chunk_type=first.block_type if len(covered) == 1 else "text",
                    ordinal=chunk_ordinal,
                    start_offset=first.start_offset,
                    end_offset=last.end_offset,
                    metadata={
                        "block_ids": [item.block_id for _, _, item in covered],
                        "breadcrumb": breadcrumb,
                        "context_block_ids": context_blocks,
                        "block_spans": [
                            {"block_id": item.block_id, "content_start": max(part_start - start, 0),
                             "content_end": min(part_end, end) - start}
                            for start, end, item in covered
                        ],
                    },
                )
            )
    return chunks


def _table_chunks(
    block: DocumentBlockWrite, prefix: str, breadcrumb: str,
    token_counter: Callable[[str], int], max_tokens: int, ordinal: int,
) -> list[RetrievalChunkWrite]:
    """Render searchable table rows without changing the persisted source block."""
    rows: list[tuple[int, int, list[str]]] = []
    separators: list[int] = []
    offset = 0
    for raw in block.content.splitlines(keepends=True):
        line = raw.strip()
        start, end = offset, offset + len(raw.rstrip("\r\n"))
        offset += len(raw)
        cells = re.split(r"(?<!\\)\|", line)
        if cells and not cells[0].strip():
            cells = cells[1:]
        if cells and not cells[-1].strip():
            cells = cells[:-1]
        if cells and all(re.fullmatch(r":?-+:?", cell.strip()) for cell in cells):
            separators.append(len(rows))
            continue
        cells = [re.sub(r"\s+", " ", unescape(re.sub(
            r"<br\s*/?>", " ", cell, flags=re.IGNORECASE
        )).replace(r"\|", "|")).strip() for cell in cells]
        if any(cells):
            rows.append((start, end, cells))
    if not rows:
        return []
    # A single-row layout (e.g. signatures) is content, never a column header.
    has_header = len(rows) > 1 and 1 in separators and all(rows[0][2])
    if has_header and ("<br" in block.content[:rows[0][1]].lower()
                       or any(len(cell) > 80 for cell in rows[0][2])):
        has_header = False
    headers = rows[0][2] if has_header else []
    result: list[RetrievalChunkWrite] = []
    for row_index, (start, end, cells) in enumerate(rows[1:] if has_header else rows):
        row_prefix = prefix
        if headers:
            row_prefix += "Cột: " + "; ".join(headers) + "\n"
        body = "; ".join(
            f"{headers[index]}: {cell}" if index < len(headers) else f"Cột {index + 1}: {cell}"
            for index, cell in enumerate(cells) if cell
        ) if headers else "\n\n".join(cell for cell in cells if cell)
        for part in _split_content(row_prefix, body, token_counter, max_tokens):
            content = row_prefix + part
            result.append(RetrievalChunkWrite(
                chunk_key=f"legal-v3-{block.block_id}-{len(result) + 1}",
                content=content, content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                node_id=block.node_id, block_id=block.block_id, chunk_type="table",
                ordinal=ordinal + len(result), start_offset=block.start_offset, end_offset=block.end_offset,
                metadata={"block_ids": [block.block_id], "breadcrumb": breadcrumb,
                          "table_row": row_index + (2 if has_header else 1), "table_headers": headers,
                          "block_spans": [{"block_id": block.block_id, "content_start": start,
                                           "content_end": end}],
                          "header_span": [rows[0][0], rows[0][1]] if has_header else None},
            ))
    return result


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

    def split(value: str, level: int = 0) -> list[str]:
        if token_counter(f"{prefix}{value}") <= max_tokens:
            return [value]
        separators = (r"\n+", r"(?<=[.!?;])\s+(?=[A-ZÀ-ỸĐ])", r"\s+")
        if level == len(separators):
            raise ValueError("A single word exceeds the configured maximum chunk token count")
        # Preserve exact substrings so each emitted piece can map back to its blocks.
        boundaries = [0, *(match.end() for match in re.finditer(separators[level], value)), len(value)]
        result: list[str] = []
        pending_start: int | None = None
        pending_end = 0
        for start, end in zip(boundaries, boundaries[1:]):
            unit = value[start:end].strip()
            if not unit:
                continue
            candidate = value[pending_start if pending_start is not None else start:end].strip()
            if token_counter(f"{prefix}{candidate}") <= max_tokens:
                if pending_start is None:
                    pending_start = start
                pending_end = end
                continue
            if pending_start is not None:
                result.append(value[pending_start:pending_end].strip())
                pending_start = None
            if token_counter(f"{prefix}{unit}") > max_tokens:
                result.extend(split(unit, level + 1))
            else:
                pending_start, pending_end = start, end
        if pending_start is not None:
            result.append(value[pending_start:pending_end].strip())
        return result

    return split(content)


def _estimate_tokens(text: str) -> int:
    return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))
