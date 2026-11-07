"""Trace the integration with real parsing/ranking and explicit model/store fakes."""

import json
import unittest
from copy import deepcopy
from unittest.mock import Mock

import numpy as np

from src.applications.tillegal.agents.judge.adapter import adapt_evidence_bundle
from src.applications.tillegal.agents.judge.agent import FixtureJudgeProvider
from src.applications.tillegal.agents.response.adapter import make_summary_input
from src.applications.tillegal.agents.response.agent import FixtureSummaryProvider
from src.applications.tillegal.composition import create_tillegal_modules
from src.applications.tillegal.ingestion.data_contracts import NULLABLE_FIELDS, ContractError, build_document
from src.integrations.embedding.adapter import LocalEmbeddingAdapter


class MemoryStore:
    def __init__(self):
        self.rows = {}

    async def save(self, document, parsed, profile, windows):
        vid = document["document_version_id"]
        self.rows[vid] = json.dumps(dict(document=document, parsed=parsed, profile=profile, windows=windows))
        return vid

    async def load(self, version_ids, profile):
        return [json.loads(self.rows[i]) for i in version_ids]


class FixtureEncoder:
    config = dict(model="fixture", revision="test", dimension=384, pooling="fixture", text_policy="fixture")

    def __init__(self):
        self.calls = []

    def windows(self, text):
        return [(i, min(i + 24, len(text)), text[i : i + 24]) for i in range(0, len(text), 24)]

    def encode(self, texts, kind):
        self.calls.append(kind)
        result = np.zeros((len(texts), 384), dtype=np.float32)
        for i, text in enumerate(texts):
            result[i, sum(text.encode()) % 384] = 1
        return result


def document():
    fields = dict.fromkeys(NULLABLE_FIELDS)
    fields.update(title="Nguồn giả định", source_url="https://example.invalid/fixture")
    return build_document(
        **fields,
        source_id="fixture",
        source_record_id="01",
        source_snapshot_id="a" * 64,
        content_format="html",
        content="<p>Điều 1. Quy tắc giả định</p><p>1. Điều kiện A áp dụng cho ví dụ này, trừ ngoại lệ B.</p>",
        raw_ref=dict(uri="fixture:///01", file_sha256="b" * 64, record_key="id", record_value="01"),
        processing_steps=["fixture"],
        issues=["SYNTHETIC_NOT_LAW"],
    )


class FlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.backend = FixtureEncoder()
        self.embedder = LocalEmbeddingAdapter(self.backend)
        self.store = MemoryStore()
        self.judge = FixtureJudgeProvider({})
        self.summary = FixtureSummaryProvider({})
        self.modules = create_tillegal_modules(
            store=self.store, embedder=self.embedder, judge_provider=self.judge, summary_provider=self.summary
        )

    async def test_ingest_read_hybrid_judge_summary(self):
        doc = document()
        vid = await self.modules.ingestion.ingest(doc)
        record = json.loads(self.store.rows[vid])
        self.assertGreater(len(record["windows"]), len(record["parsed"]["chunks"]))
        result = await self.modules.retrieval.search("Điều kiện A", version_ids=(vid,), request_id="r", top_k=2)
        self.assertEqual(self.backend.calls, ["passage", "query"])
        self.assertEqual(result["retrieval"]["retrieval_method"], "HYBRID")
        bundle = result["evidence_bundle"]
        evidence = next(e for e in bundle["evidence"] if "ngoại lệ B" in e["quote"])
        eid = evidence["evidence_id"]
        self.assertEqual(evidence["document_version_id"], vid)
        self.assertEqual(evidence["chunk"]["article"], "1")
        context = dict(
            question="Điều kiện A", query_plan={"issues": [{"issue_id": "I1", "text": "Điều kiện A"}]}, as_of_date=None
        )
        judge_input = adapt_evidence_bundle(bundle, **context, search_rounds_completed=1, query_history=[])
        self.judge.response = dict(
            status="SUFFICIENT",
            issue_checks=[dict(issue_id="I1", coverage="full", evidence_ids=[eid])],
            usable_evidence_ids=[eid],
            missing_items=[],
            next_queries=[],
            explanation="Nhãn fixture",
            error_code=None,
        )
        assessed = await self.modules.evaluate(judge_input)
        self.assertEqual(assessed["status"], "SUFFICIENT", assessed)
        self.summary.response = dict(
            units=[
                dict(text=evidence["quote"], issue_ids=["I1"], evidence_ids=[eid], statement_type="source_statement")
            ],
            limitations=[],
            abstain=False,
        )
        draft = await self.modules.summarize(make_summary_input(bundle, assessed, **context))
        self.assertEqual(draft["status"], "DRAFT_UNVERIFIED", draft)
        self.assertEqual(draft["claims"][0]["citation_ids"], [draft["citations"][0]["citation_id"]])
        citation = draft["citations"][0]
        self.assertEqual(
            (citation["evidence_id"], citation["document_version_id"], citation["source_url"]),
            (eid, vid, doc.source_url),
        )
        self.assertFalse(citation["exact_citation_verified"])

    async def test_corrupt_and_incompatible_windows_fail(self):
        vid = await self.modules.ingestion.ingest(document())
        original = json.loads(self.store.rows[vid])
        for change in ("profile", "locator", "missing"):
            row = deepcopy(original)
            if change == "profile":
                row["profile"]["revision"] = "other"
            elif change == "locator":
                row["windows"][0]["start"] += 1
            else:
                row["windows"].pop()
            self.store.rows[vid] = json.dumps(row)
            with self.assertRaises(ContractError):
                await self.modules.retrieval.search("A", version_ids=(vid,), request_id="r")

    async def test_encoder_rejects_invalid_outputs(self):
        self.assertEqual(await self.embedder.embed_documents([]), [])
        self.assertFalse(self.backend.calls)
        for values in (np.zeros((2, 384)), np.zeros((1, 1536)), np.full((1, 384), np.nan)):
            self.backend.encode = Mock(return_value=values)
            with self.assertRaises(ContractError):
                await self.embedder.embed_query("q")
        with self.assertRaises(ContractError):
            await self.embedder.embed_query(" ")

    async def test_preparsed_identity_and_bootstrap(self):
        from src.applications.tillegal.ingestion.legal_parser import parse_document
        from src.bootstrap import create_app
        from src.core.config import AppSettings

        doc = document()
        parsed = parse_document(doc)
        app = create_app(AppSettings(), tillegal_modules=self.modules)
        self.assertIs(app.state.tillegal_modules, self.modules)
        vid = await app.state.tillegal_modules.ingestion.ingest(doc, parsed=parsed)
        self.assertEqual(vid, doc.document_version_id)
        parsed["chunks"][0]["document_version_id"] = "different"
        with self.assertRaises(ContractError):
            await self.modules.ingestion.ingest(doc, parsed=parsed)

    async def test_transferred_window_offsets_in_nfc_text(self):
        import unicodedata

        from src.integrations.embedding.local_encoder import LocalEncoder

        encoder = object.__new__(LocalEncoder)
        encoder.tokenizer = lambda text, **kwargs: {"offset_mapping": [(i, i + 1) for i in range(len(text))]}
        text = ("a" + chr(0x301)) * 900
        normalized = unicodedata.normalize("NFC", text)
        windows = encoder.windows(text)
        self.assertEqual([(a, b) for a, b, _ in windows], [(0, 480), (416, 896), (832, 900)])
        self.assertTrue(all(piece == normalized[a:b] for a, b, piece in windows))
