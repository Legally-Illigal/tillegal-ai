"""Deterministic Vietnamese query analysis, with no invented legal references."""

import re
import unicodedata
from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from src.applications.tillegal.agents.query.context import classify_model_time, parse_context
from src.applications.tillegal.agents.query.schemas import LegalReference, SearchObjective, StatedFact, TemporalContext


class QueryInputError(ValueError):
    """Invalid user query, with a content-free public error code."""


class Subquery(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    purpose: Literal["lookup", "question_part", "topic"]


class QueryPlan(BaseModel):
    original: str = Field(min_length=1, max_length=10000)
    intent: Literal["quote_lookup", "legal_question"]
    domain: Literal["labour", "unknown"]
    temporal_scope: list[str]
    subqueries: list[Subquery] = Field(min_length=1, max_length=4)
    clarification: str | None
    analysis_method: Literal["deterministic", "llm"] = "deterministic"
    analysis_model: str | None = None
    facts: list[StatedFact] = Field(default_factory=list, max_length=12)
    issues: list[str] = Field(default_factory=list, max_length=4)
    missing_information: list[str] = Field(default_factory=list, max_length=8)
    citations: list[LegalReference] = Field(default_factory=list)
    temporal_context: list[TemporalContext] = Field(default_factory=list)
    search_objectives: list[SearchObjective] = Field(default_factory=list, max_length=4)
    planning_warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def context_and_links(self) -> Self:
        text = unicodedata.normalize("NFC", self.original).strip()
        if any(
            item.start >= item.end or text[item.start : item.end] != item.text
            for item in [*self.citations, *self.temporal_context]
        ):
            raise ValueError("Context span differs from original analysis text")
        indices = [item.query_index for item in self.search_objectives]
        if len(indices) != len(set(indices)):
            raise ValueError("Duplicate objective query mapping")
        for item in self.search_objectives:
            if item.query_index >= len(self.subqueries) or any(
                index < 0 or index >= len(self.issues) for index in item.issue_indices
            ):
                raise ValueError("Objective refers to missing issue/query")
        return self


def understand(question: str) -> dict:
    """Preserve the exact argument in original; analyze validated NFC text."""
    if not isinstance(question, str):
        raise QueryInputError("QUERY_INPUT_TYPE")
    if not 1 <= len(question) <= 10000:
        raise QueryInputError("QUERY_INPUT_LENGTH")
    if any(unicodedata.category(char) in {"Cc", "Cs"} and char not in "\t\n\r" for char in question):
        raise QueryInputError("QUERY_INPUT_CHARACTER")
    text = unicodedata.normalize("NFC", question).strip()
    if not text:
        raise QueryInputError("QUERY_INPUT_EMPTY")
    parts = [
        s.strip(" ?;")
        for s in re.split(r"[;?\n]+|\s+và\s+(?=(?:khi nào|ai |bao nhiêu|điều kiện|thủ tục))", text, flags=re.I)
        if s.strip(" ?;")
    ]
    prefix = re.match(r"^(?:trích dẫn|trích nguyên văn|tìm đoạn)\s*[:\s]\s*", text, re.I)
    topic = text[prefix.end() :].strip(' “”?."') if prefix else ""
    citation_lookup = bool(
        re.match(r"^(?:tra cứu|tìm|nội dung|nguyên văn)\s+(?:điều|khoản)\s+\d+", text, re.I)
        and not re.search(r"có phải|có được|trường hợp|của tôi|tôi có", text, re.I)
    )
    quote_only = bool(topic and len(parts) == 1) or citation_lookup
    if citation_lookup and not topic:
        topic = text
    queries = [topic] if quote_only else parts[:4] or [text]
    dates = []
    invalid_date = False
    for match in re.finditer(
        r"(?<![/\w])(?:\d{1,2}/\d{1,2}/\d{4}|(?:19|20)\d{2}|hiện nay|hiện hành)(?![/\w])", text, re.I
    ):
        mention = match.group()
        if "/" in mention:
            day, month, year = map(int, mention.split("/"))
            try:
                date(year, month, day)
            except ValueError:
                invalid_date = True
                continue
        dates.append(mention)
    clarification = None
    if len(parts) > 4:
        clarification = "Vui lòng chia câu hỏi thành tối đa bốn phần."
    elif (
        (not topic and prefix)
        or len(text.split()) < 2
        or text.casefold().strip(" ?") in {"có được không", "như vậy đúng không", "trường hợp này"}
    ):
        clarification = "Bạn cần tra cứu quy định hoặc tình huống cụ thể nào?"
    if invalid_date:
        clarification = "Ngày được nêu không hợp lệ. Bạn vui lòng kiểm tra lại ngày, tháng và năm."
    subqueries = [Subquery(text=q, purpose="lookup" if quote_only else "question_part") for q in queries]
    if not quote_only:
        topics = re.finditer(
            r"đối thoại định kỳ|nghỉ hằng năm|nghỉ phép|thời giờ làm việc|"
            r"chấm dứt hợp đồng lao động|tiền lương|làm thêm giờ",
            text,
            re.I,
        )
        seen = {q.casefold() for q in queries}
        for match in topics:
            topic_text = match.group()
            if len(subqueries) < 4 and topic_text.casefold() not in seen:
                subqueries.append(Subquery(text=topic_text, purpose="topic"))
                seen.add(topic_text.casefold())
    facts = []
    issues = []
    missing = []
    # A deliberately narrow offline planner, not a general legal reasoner.
    employment_exit = bool(
        re.search(r"hợp đồng lao động", text, re.I)
        and re.search(r"\btôi\b[^.!?;\n]{0,180}\b(?:muốn|xin) nghỉ(?: việc)?", text, re.I)
        and not re.search(r"không\s+(?:muốn|xin) nghỉ|bị sa thải|bị chấm dứt", text, re.I)
        and len(parts) == 1
        and not quote_only
    )
    if employment_exit:
        for pattern in [
            r"hợp đồng lao động\s+(?:\d+\s*(?:năm|tháng)|không xác định thời hạn)",
            r"(?:mới )?(?:làm|làm việc)(?: được)?\s+\d+\s*(?:tháng|năm)",
            r"(?:muốn|xin) nghỉ(?: việc)?",
        ]:
            match = re.search(pattern, text, re.I)
            if match:
                facts.append(StatedFact(text=match.group(), source_quote=match.group()))
        context = " ".join(f.text for f in facts)
        objectives = [
            (
                "Đơn phương chấm dứt hợp đồng lao động và nghĩa vụ báo trước",
                "người lao động đơn phương chấm dứt hợp đồng lao động nghĩa vụ báo trước trường hợp miễn báo trước",
            ),
            (
                "Nghĩa vụ bồi thường khi chấm dứt hợp đồng lao động",
                "người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật bồi thường chi phí đào tạo",
            ),
        ]
        subqueries = [
            Subquery(text=f"{objective}; tình huống: {context}", purpose="question_part") for _, objective in objectives
        ]
        issues = [issue for issue, _ in objectives]
        missing = [
            "Lý do nghỉ việc và ngày dự kiến nghỉ là gì?",
            "Có thỏa thuận đào tạo hoặc cam kết hoàn trả chi phí đào tạo không?",
        ]
    # Collapse identical objectives in the planner; Search also reuses exact requests.
    subqueries = list({item.text: item for item in subqueries}.values())
    references, temporal = parse_context(text)
    # The legacy list stays available; typed roles separate identity from dates.
    dates = list(
        dict.fromkeys(
            mention for mention in dates if classify_model_time(mention, text, references, temporal) == "time"
        )
    )
    return QueryPlan(
        citations=references,
        temporal_context=temporal,
        search_objectives=[SearchObjective(query_index=index, issue_indices=[index]) for index in range(len(issues))]
        if len(issues) == len(subqueries)
        else [],
        facts=facts,
        issues=issues,
        missing_information=missing,
        original=question,
        intent="quote_lookup" if quote_only else "legal_question",
        domain="labour" if re.search(r"lao động|tiền lương|nghỉ phép|làm việc", text, re.I) else "unknown",
        temporal_scope=dates,
        clarification=clarification,
        subqueries=subqueries,
    ).model_dump()
