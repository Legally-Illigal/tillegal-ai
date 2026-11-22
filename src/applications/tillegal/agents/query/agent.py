"""Deterministic Vietnamese query analysis, with no invented legal references."""

import re
import unicodedata
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


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
    quote_only = bool(topic and len(parts) == 1)
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
    return QueryPlan(
        original=question,
        intent="quote_lookup" if quote_only else "legal_question",
        domain="labour" if re.search(r"lao động|tiền lương|nghỉ phép|làm việc", text, re.I) else "unknown",
        temporal_scope=dates,
        clarification=clarification,
        subqueries=subqueries,
    ).model_dump()
