"""Convert VBPL body HTML into Markdown while preserving legal-document structure."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser


def clean_legal_markdown(markdown: str) -> str:
    """Remove administrative layout blocks, retaining attached legal documents."""
    groups = re.split(r"\n\s*\n", markdown.replace("\r\n", "\n").strip())

    def plain(value: str) -> str:
        value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
        value = re.sub(r"<[^>]+>", "", value)
        return re.sub(r"[ \t]+", " ", unescape(re.sub(r"[*_#`|]", "", value))).strip()

    title = re.compile(r"^(?:NGHỊ QUYẾT|QUYẾT ĐỊNH|NGHỊ ĐỊNH|THÔNG TƯ|LUẬT|PHÁP LỆNH|QUY CHẾ|QUY ĐỊNH)$")
    boundary = re.compile(r"^(?:Điều\s+\d|Chương\s+|Phần\s+|Mục\s+|PHỤ LỤC\b)", re.IGNORECASE)
    footer = re.compile(
        r"^(?:Nơi nhận\s*:|(?:TM|KT|TL|TUQ)\s*\.|CHỦ TỊCH$|PHÓ CHỦ TỊCH$|"
        r"BỘ TRƯỞNG$|THỨ TRƯỞNG$|THỦ TƯỚNG$|PHÓ THỦ TƯỚNG$|CHỦ TỊCH QUỐC HỘI$)",
        re.IGNORECASE,
    )
    texts = [plain(group) for group in groups]
    # Only trim a leading administrative region when a standalone document title exists.
    first_title = next((i for i, value in enumerate(texts) if title.fullmatch(value)), None)
    start = 0
    if first_title is not None and not any(
        boundary.match(value) or value.startswith("Căn cứ ") for value in texts[:first_title]
    ) and any(
        re.search(r"CỘNG HÒA|Độc lập\s*[-–]|\bSố\s*:", value, re.IGNORECASE)
        for value in texts[:first_title]
    ):
        start = first_title
    result: list[str] = []
    in_footer = False
    for index in range(start, len(groups)):
        group, value = groups[index], texts[index]
        first_line = value.splitlines()[0] if value else ""
        resumes = title.fullmatch(first_line) is not None or boundary.match(first_line) is not None
        if resumes:
            in_footer = False
        if (
            value == value.upper()
            and re.match(r"^(?:ỦY BAN NHÂN DÂN|HỘI ĐỒNG NHÂN DÂN)\b", value)
            and index + 1 < len(texts)
            and texts[index + 1].startswith("Căn cứ ")
        ):
            continue
        # Tables may contain both a signature and the next attachment's masthead.
        is_table = group.lstrip().startswith("|")
        if is_table and not re.sub(r"[\s|:\-]", "", value):
            continue
        if not resumes and re.search(r"CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", value, re.IGNORECASE):
            if is_table or first_line.upper() == "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM":
                continue
        if footer.match(first_line):
            in_footer = True
        if in_footer:
            continue
        result.append(group.strip())
    # Word-exported titles can use separate paragraphs for visual wrapping.
    # Join only the bold subtitle immediately following a document-type title.
    subtitle = 1
    if result and title.fullmatch(plain(result[0])):
        while subtitle + 1 < len(result):
            left, right = result[subtitle], result[subtitle + 1]
            fully_bold = r"(?:\s*\*\*[^*]+\*\*\s*)+"
            if (not re.fullmatch(fully_bold, left) or not re.fullmatch(fully_bold, right)
                    or boundary.match(plain(right)) or title.fullmatch(plain(right))):
                break
            result[subtitle:subtitle + 2] = [left + " " + right]
    cleaned = "\n\n".join(result).strip()
    if not cleaned:
        raise ValueError("Administrative cleanup produced empty legal Markdown")
    return cleaned + "\n"


_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
_SKIP_TAGS = {"head", "script", "style", "template"}
_BLOCK_TAGS = {
    "article",
    "blockquote",
    "div",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "ol",
    "p",
    "section",
    "table",
    "ul",
}


@dataclass
class _Element:
    tag: str
    attributes: dict[str, str]
    children: list[str | _Element] = field(default_factory=list)


class _DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Element("document", {})
        self._stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = _Element(tag.lower(), {key.lower(): value for key, value in attrs if value is not None})
        self._stack[-1].children.append(element)
        if element.tag not in _VOID_TAGS:
            self._stack.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == tag:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if data:
            self._stack[-1].children.append(data)


def convert_html_to_markdown(content: bytes | str) -> str:
    """Convert one HTML document to Markdown, retaining paragraphs, emphasis, lists, and tables."""
    html = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    parser = _DocumentParser()
    parser.feed(html)
    parser.close()

    body = _find_element(parser.root, "body") or parser.root
    blocks = _render_blocks(body)
    markdown = re.sub(r"\n{3,}", "\n\n", "\n\n".join(block for block in blocks if block.strip())).strip()
    if not markdown:
        raise ValueError("VBPL body HTML produced empty Markdown")
    return f"{markdown}\n"


def _find_element(element: _Element, tag: str) -> _Element | None:
    if element.tag == tag:
        return element
    for child in element.children:
        if isinstance(child, _Element):
            found = _find_element(child, tag)
            if found is not None:
                return found
    return None


def _render_blocks(element: _Element) -> list[str]:
    blocks: list[str] = []
    inline_parts: list[str] = []

    def flush_inline() -> None:
        text = _normalize_inline("".join(inline_parts))
        if text:
            blocks.append(text)
        inline_parts.clear()

    for child in element.children:
        if isinstance(child, str):
            inline_parts.append(child)
            continue
        if child.tag in _SKIP_TAGS:
            continue
        if child.tag in _BLOCK_TAGS:
            flush_inline()
            if child.tag == "table":
                table = _render_table(child)
                if table:
                    blocks.append(table)
            elif child.tag in {"ol", "ul"}:
                list_markdown = "\n".join(_render_list(child))
                if list_markdown:
                    blocks.append(list_markdown)
            elif child.tag == "hr":
                blocks.append("---")
            elif child.tag == "li":
                text = _normalize_inline(_inline_content(child))
                if text:
                    blocks.append(f"- {text}")
            elif child.tag == "blockquote":
                quoted = _render_blocks(child)
                blocks.extend("\n".join(f"> {line}" for line in block.splitlines()) for block in quoted)
            elif child.tag.startswith("h") and len(child.tag) == 2:
                text = _normalize_inline(_inline_content(child))
                if text:
                    blocks.append(f"{'#' * int(child.tag[1])} {text}")
            elif child.tag == "p":
                text = _normalize_inline(_inline_content(child))
                if text:
                    blocks.append(text)
            else:
                blocks.extend(_render_blocks(child))
            continue
        inline_parts.append(_inline_element(child))

    flush_inline()
    return blocks


def _inline_content(element: _Element) -> str:
    parts: list[str] = []
    for child in element.children:
        rendered = child if isinstance(child, str) else _inline_element(child)
        if not rendered:
            continue
        if parts and _needs_inline_space(parts[-1], rendered):
            parts.append(" ")
        parts.append(rendered)
    return "".join(parts)


def _inline_element(element: _Element) -> str:
    if element.tag in _SKIP_TAGS:
        return ""
    if element.tag == "br":
        return "\n"
    content = _inline_content(element)
    if element.tag in {"b", "strong"} and content.strip():
        if "*" in content:
            return f"<strong>{content.strip()}</strong>"
        return f"**{content.strip()}**"
    if element.tag in {"em", "i"} and content.strip():
        if "*" in content:
            return f"<em>{content.strip()}</em>"
        return f"*{content.strip()}*"
    if element.tag == "a":
        href = element.attributes.get("href")
        if href and content.strip():
            return f"[{content.strip()}]({href})"
    if element.tag in {"sup", "sub"} and content.strip():
        return f"<{element.tag}>{content.strip()}</{element.tag}>"
    if element.tag == "img":
        alt = element.attributes.get("alt", "").strip()
        return f" {alt} " if alt else ""
    return content


def _render_list(element: _Element, depth: int = 0) -> list[str]:
    ordered = element.tag == "ol"
    marker = "1." if ordered else "-"
    blocks: list[str] = []
    index = 0
    for child in element.children:
        if not isinstance(child, _Element):
            continue
        if child.tag == "li":
            index += 1
            text_parts: list[str] = []
            nested_lists: list[_Element] = []
            for item_child in child.children:
                if isinstance(item_child, _Element) and item_child.tag in {"ol", "ul"}:
                    nested_lists.append(item_child)
                elif isinstance(item_child, _Element) and item_child.tag in _BLOCK_TAGS:
                    text_parts.extend(_render_blocks(item_child))
                else:
                    text_parts.append(item_child if isinstance(item_child, str) else _inline_element(item_child))
            text = _normalize_inline(" ".join(part for part in text_parts if part.strip()))
            list_marker = f"{index}." if ordered else marker
            if text:
                blocks.append(f"{'  ' * depth}{list_marker} {text}")
            for nested in nested_lists:
                blocks.extend(_render_list(nested, depth + 1))
    return blocks


def _render_table(element: _Element) -> str:
    rows = _table_rows(element)
    rendered_rows: list[list[str]] = []
    for row in rows:
        cells = _table_cells(row)
        if cells:
            rendered_rows.append([_table_cell_text(cell) for cell in cells])
    if not rendered_rows:
        return ""

    column_count = max(map(len, rendered_rows))
    lines: list[str] = []
    for index, row in enumerate(rendered_rows):
        padded = row + [""] * (column_count - len(row))
        lines.append("| " + " | ".join(_escape_table_cell(cell) for cell in padded) + " |")
        if index == 0:
            lines.append("| " + " | ".join("---" for _ in range(column_count)) + " |")
    return "\n".join(lines)


def _table_rows(element: _Element) -> list[_Element]:
    rows: list[_Element] = []

    def visit(parent: _Element) -> None:
        for child in parent.children:
            if not isinstance(child, _Element) or child.tag == "table":
                continue
            if child.tag == "tr":
                rows.append(child)
            else:
                visit(child)

    visit(element)
    return rows


def _table_cells(row: _Element) -> list[_Element]:
    cells: list[_Element] = []

    def visit(parent: _Element) -> None:
        for child in parent.children:
            if not isinstance(child, _Element) or child.tag == "table":
                continue
            if child.tag in {"td", "th"}:
                cells.append(child)
            else:
                visit(child)

    visit(row)
    return cells


def _table_cell_text(cell: _Element) -> str:
    parts: list[str] = []

    def visit(element: _Element) -> None:
        for child in element.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag == "br":
                parts.append("\n")
            elif child.tag in _SKIP_TAGS:
                continue
            elif child.tag == "table":
                parts.append(_normalize_inline(_inline_content(child)))
            elif child.tag in {"p", "div"}:
                if parts and not parts[-1].endswith("\n"):
                    parts.append("\n")
                parts.append(_inline_content(child))
                parts.append("\n")
            elif child.tag in _BLOCK_TAGS:
                visit(child)
            else:
                parts.append(_inline_element(child))

    visit(cell)
    return _normalize_inline("\n".join(line for line in "".join(parts).splitlines() if line.strip()))


def _escape_table_cell(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", "<br>")


def _normalize_inline(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"[ \t\f\v]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    value = re.sub(r"\n{2,}", "\n", value)
    return value.strip()


def _needs_inline_space(previous: str, current: str) -> bool:
    previous_text = re.sub(r"</?[^>]+>|[*_~`]", "", previous)
    current_text = re.sub(r"</?[^>]+>|[*_~`]", "", current)
    return bool(previous_text and current_text and previous_text[-1].isalnum() and current_text[0].isalnum())
