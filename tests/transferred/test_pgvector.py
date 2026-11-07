"""Optional isolated PostgreSQL/pgvector migration and actual RPC body round trip."""

import json
import os
import subprocess
import unittest
from pathlib import Path

from src.applications.tillegal.ingestion.legal_parser import parse_document
from src.integrations.embedding.adapter import LocalEmbeddingAdapter

from .test_module_flow import FixtureEncoder, document


@unittest.skipUnless(os.environ.get("PGLITE_TEST_PREFIX"), "requires isolated PGlite test installation")
class PgvectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_transactional_roundtrip(self):
        from src.integrations.database.repositories.version_window_repository import persistence_payload

        doc = document()
        parsed = parse_document(doc)
        source, mapped = persistence_payload(doc.to_dict(), parsed)
        embedder = LocalEmbeddingAdapter(FixtureEncoder())
        windows = await embedder.embed_documents(parsed["chunks"])
        request = json.dumps([source, mapped, embedder.profile, windows], ensure_ascii=False)
        run = subprocess.run(
            [os.environ.get("TILLEGAL_TEST_NODE", "node"), str(Path(__file__).with_name("check_pgvector.cjs"))],
            input=request,
            capture_output=True,
            encoding="utf-8",
            timeout=120,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        row = json.loads(run.stdout)
        self.assertEqual(row["document"], doc.to_dict())
        self.assertEqual(row["parsed"], parsed)
        self.assertEqual(row["windows"], windows)
