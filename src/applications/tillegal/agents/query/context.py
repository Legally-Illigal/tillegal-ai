"""Literal span parsing for user-supplied legal references and temporal roles."""

import re
from datetime import date

from src.applications.tillegal.agents.query.schemas import LegalReference, TemporalContext

DOCUMENT = re.compile(r"\b\d+/(?:19|20)\d{2}/(?=[A-Za-zĐđ])[\wĐđ-]+\b")
PROVISION = re.compile(r"\b(?P<kind>điều|khoản|điểm)\s+(?:\d+[a-zđ]?|[a-zđ])\b", re.I)
STATUTE = re.compile(
    r"\b(?:bộ luật|luật|nghị định|thông tư)\s+(?!(?:áp dụng|tại|vào|năm)\b)"
    r"[^\d\n.;?!/]{1,65}?\s+(?:năm\s+)?(?:19|20)\d{2}\b",
    re.I,
)
CALENDAR = re.compile(r"(?<![\w/])(?:\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})(?![\w/])")
YEAR = re.compile(r"(?<![\w/])(?:19|20)\d{2}(?![\w/])")
DURATION = re.compile(r"\b\d+\s*(?:ngày|tháng|năm|tuổi|giờ)\b", re.I)
RELATIVE = re.compile(r"hiện nay|hiện hành|thời điểm đó|khi đó|trước đây|năm tới|năm trước", re.I)
CUES = {
    "publication_date": r"ban hành|công bố|thông qua",
    "effective_date": r"có hiệu lực|hiệu lực từ|hiệu lực ngày",
    "applicability_date": r"áp dụng|quy định tại|pháp luật tại|tra cứu tại",
    "event_date": r"ký|mua|nhận|nghỉ|sinh|đến hạn|diễn ra|giao dịch",
    "historical_reference": r"trước đây|khi đó|thời điểm đó",
}


def overlaps(start: int, end: int, spans) -> bool:
    return any(start < item.end and end > item.start for item in spans)


def parse_context(text: str) -> tuple[list[LegalReference], list[TemporalContext]]:
    """Offsets refer to the NFC/trimmed analysis text; original is never edited."""
    references = []
    for match in DOCUMENT.finditer(text):
        references.append(LegalReference(kind="document", text=match.group(), start=match.start(), end=match.end()))
    kinds = {"điều": "article", "khoản": "clause", "điểm": "point"}
    for match in PROVISION.finditer(text):
        references.append(
            LegalReference(
                kind=kinds[match["kind"].casefold()], text=match.group(), start=match.start(), end=match.end()
            )
        )
    for match in STATUTE.finditer(text):
        # A publication/effectivity verb is a date cue, not part of a statute title.
        if not re.search(r"ban hành|hiệu lực|áp dụng|được", match.group(), re.I):
            references.append(
                LegalReference(kind="statute_reference", text=match.group(), start=match.start(), end=match.end())
            )
    references.sort(key=lambda item: (item.start, item.end))
    temporal = []
    calendar_spans = list(CALENDAR.finditer(text))
    candidates = [(match, "date") for match in calendar_spans]
    candidates += [
        (match, "year")
        for match in YEAR.finditer(text)
        if not any(match.start() < other.end() and match.end() > other.start() for other in calendar_spans)
    ]
    candidates += [(match, "duration") for match in DURATION.finditer(text)]
    candidates += [(match, "relative") for match in RELATIVE.finditer(text)]
    used = set()
    for match, category in sorted(candidates, key=lambda item: (item[0].start(), -len(item[0].group()))):
        if overlaps(match.start(), match.end(), references) or (match.start(), match.end()) in used:
            continue
        value = match.group()
        iso_date = None
        if category == "date":
            try:
                if "/" in value:
                    day, month, year = map(int, value.split("/"))
                    iso_date = date(year, month, day)
                else:
                    iso_date = date.fromisoformat(value)
            except ValueError:
                continue
        prefix = text[max(0, match.start() - 65) : match.start()]
        cues = [(cue.end(), role) for role, pattern in CUES.items() for cue in re.finditer(pattern, prefix, re.I)]
        role = max(cues)[1] if cues else "unspecified"
        if category == "duration":
            role = "duration"
        elif category == "relative":
            role = (
                "current_reference"
                if value.casefold() in {"hiện nay", "hiện hành"}
                else "relative_reference"
                if value.casefold() in {"năm tới", "năm trước"}
                else "historical_reference"
            )
        negated = bool(re.search(r"(?:không phải|không áp dụng|không theo)\s*$", prefix, re.I))
        temporal.append(
            TemporalContext(
                text=value,
                start=match.start(),
                end=match.end(),
                role=role,
                iso_date=iso_date.isoformat() if iso_date else None,
                negated=negated,
            )
        )
        used.add((match.start(), match.end()))
    return references, temporal


def classify_model_time(mention: str, text: str, references, temporal) -> str:
    """Only literal grounded references are reclassified, never unsupported dates."""
    positions = [match for match in re.finditer(re.escape(mention), text)]
    has_negated_time = False
    for match in positions:
        for item in temporal:
            start, end = max(match.start(), item.start), min(match.end(), item.end)
            if start < end and not overlaps(start, end, references):
                if not item.negated:
                    return "time"
                has_negated_time = True
    if has_negated_time:
        return "negated_time"
    if positions and all(overlaps(match.start(), match.end(), references) for match in positions):
        return "reference"
    raise ValueError("Unsupported temporal span")


def supplied_context(text: str) -> dict[str, str]:
    """A small set of demonstrated scenario slots, not a legal ontology."""
    patterns = {
        "contract_duration": r"hợp đồng(?: lao động)?(?: xác định thời hạn)?\s+\d+\s*(?:năm|tháng)",
        "exit_reason": r"(?:nghỉ(?: việc)?|muốn nghỉ)\s+vì\s+[^.;?\n]{1,80}",
        "training_agreement": r"(?:không có|chưa ký|có ký)\s+thỏa thuận đào tạo",
    }
    return {name: match.group() for name, pattern in patterns.items() if (match := re.search(pattern, text, re.I))}


def reconcile_missing(text: str, missing: list[str]) -> tuple[list[str], list[str]]:
    slots = supplied_context(text)
    result, warnings = [], []
    for item in missing:
        duration_question = re.search(r"thời hạn hợp đồng|loại hợp đồng|hợp đồng.{0,20}bao lâu", item, re.I)
        other_question = re.search(r"đặc biệt|điều khoản|thỏa thuận|gia hạn|đào tạo|\s+và\s+", item, re.I)
        if "contract_duration" in slots and duration_question and not other_question:
            warnings.append("REDUNDANT_CONTRACT_DURATION_REMOVED")
        elif (
            "exit_reason" in slots
            and re.search(r"lý do.{0,15}nghỉ|nguyên nhân.{0,15}nghỉ", item, re.I)
            and not other_question
        ):
            warnings.append("REDUNDANT_EXIT_REASON_REMOVED")
        elif (
            "training_agreement" in slots
            and re.search(r"có.{0,15}thỏa thuận đào tạo", item, re.I)
            and not re.search(r"nội dung|chi phí|hoàn trả|và", item, re.I)
        ):
            warnings.append("REDUNDANT_TRAINING_QUESTION_REMOVED")
        else:
            result.append(item)
    employee_exit = re.search(r"\btôi\b[^.!?;\n]{0,180}\b(?:muốn|xin) nghỉ", text, re.I)
    if employee_exit and "hợp đồng lao động" in text.casefold() and not re.search(r"không\s+muốn nghỉ", text, re.I):
        if "exit_reason" not in slots and not any(re.search(r"lý do|nguyên nhân", item, re.I) for item in result):
            result.append("Bạn muốn nghỉ việc vì lý do gì?")
        if "training_agreement" not in slots and not any(re.search(r"đào tạo", item, re.I) for item in result):
            result.append("Có thỏa thuận đào tạo hoặc hoàn trả chi phí đào tạo không?")
    return list(dict.fromkeys(result))[:8], warnings
