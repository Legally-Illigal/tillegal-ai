"""Offline regression tests for the existing Query boundary."""

import unicodedata

import pytest

from src.applications.tillegal.agents.query.agent import QueryPlan, understand


@pytest.mark.parametrize("question", [None, 1, False, [], {}, b"query"])
def test_invalid_type(question):
    with pytest.raises(ValueError, match="^QUERY_INPUT_TYPE$"):
        understand(question)


@pytest.mark.parametrize("question", ["", " " * 10001, "x" * 10001])
def test_length(question):
    with pytest.raises(ValueError, match="^QUERY_INPUT_LENGTH$"):
        understand(question)


@pytest.mark.parametrize("question", [" ", "\t\n\r", "\u00a0"])
def test_blank(question):
    with pytest.raises(ValueError, match="^QUERY_INPUT_EMPTY$"):
        understand(question)


@pytest.mark.parametrize("character", ["\0", "\x1b", "\x7f", "\x85", "\ud800"])
def test_characters(character):
    with pytest.raises(ValueError, match="^QUERY_INPUT_CHARACTER$"):
        understand("Nghỉ phép " + character)


def test_unicode_and_original():
    original = "  Người lao động nghỉ phép năm 2024?  "
    decomposed = unicodedata.normalize("NFD", original)
    first, second = understand(original), understand(decomposed)
    assert first.pop("original") == original
    assert second.pop("original") == decomposed
    assert first == second
    assert understand("x" * 10000)["original"] == "x" * 10000
    assert understand("Nghỉ\t phép\nTiền lương\r")


@pytest.mark.parametrize("mention", ["29/02/2024", "29/02/2000", "31/12/2024", "1/1/2024"])
def test_valid_date(mention):
    plan = understand("Quy định ngày " + mention)
    assert plan["temporal_scope"] == [mention]
    assert plan["clarification"] is None


@pytest.mark.parametrize("mention", ["29/02/2023", "29/02/1900", "31/02/2024", "31/04/2024", "0/12/2024", "1/13/2024"])
def test_invalid_date(mention):
    plan = understand("Quy định ngày " + mention + " và năm 2020")
    assert plan["temporal_scope"] == ["2020"]
    assert plan["clarification"]
    assert mention in plan["original"]


@pytest.mark.parametrize(
    "question,expected",
    [
        ("Quy định tháng 02/2024", []),
        ("Quy định ngày 29/02", []),
        ("Quy định năm 2024", ["2024"]),
        ("Quy định hiện nay", ["hiện nay"]),
        ("Quy định hiện hành", ["hiện hành"]),
        ("Quy định năm tới", []),
        ("Luật 45/2019/QH14", []),
        ("Nghỉ phép bao nhiêu ngày?", []),
    ],
)
def test_temporal_semantics(question, expected):
    assert understand(question)["temporal_scope"] == expected


def test_contract_and_regressions():
    plan = understand("Trích dẫn: đối thoại")
    assert set(plan) == {"original", "intent", "domain", "temporal_scope", "subqueries", "clarification"}
    assert QueryPlan.model_validate(plan).model_dump() == plan
    assert plan["intent"] == "quote_lookup"
    assert plan["subqueries"] == [{"text": "đối thoại", "purpose": "lookup"}]
    assert understand("Có được không?")["clarification"]
    assert understand("Người lao động nghỉ phép?")["domain"] == "labour"
    assert understand("a?b?c?d?e")["clarification"]
