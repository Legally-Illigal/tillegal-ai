import asyncio
from datetime import date

from src.application.services.vbpl_document_ingestion_service import (
    VBPL_STORAGE_BUCKET,
    VbplDocumentIngestionService,
    _storage_key,
)
from src.applications.tillegal.ingestion.crawler.vbpl_document import (
    VbplAttachment,
    VbplDocumentPage,
)
from src.applications.tillegal.ingestion.crawler.vbpl_sitemap import VbplDocumentUrl


class FakeDocuments:
    def __init__(self, existing: dict[str, object] | None = None) -> None:
        self.existing = existing
        self.saved = None

    async def get_by_source_record_id(self, source_id: str, source_record_id: str):
        return self.existing

    async def upsert(self, document):
        self.saved = document
        return {
            "id": "source-document-id",
            "raw_file_ref": document.raw_file_ref,
            "raw_content_ref": document.raw_content_ref,
        }


class FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, str, bytes, str]] = []

    def upload(self, bucket: str, key: str, content: bytes, content_type: str) -> None:
        assert bucket == VBPL_STORAGE_BUCKET
        self.uploads.append((bucket, key, content, content_type))


def _page() -> VbplDocumentPage:
    return VbplDocumentPage(
        document_id="175384",
        title="Nghị quyết",
        metadata={"meta_tags": {"article:modified_time": "2026-11-09"}},
        attachments=(
            VbplAttachment("original.pdf", "175384/original.pdf", "application/octet-stream", 5),
            VbplAttachment("body.html", "175384/body.html", "application/octet-stream", 5),
            VbplAttachment("source.doc", "175384/source.doc", "application/octet-stream", 5),
        ),
    )


def _document_url() -> VbplDocumentUrl:
    return VbplDocumentUrl(
        "https://vbpl.vn/van-ban/chi-tiet/resolution--175384",
        date(2026, 11, 9),
        "https://vbpl.vn/sitemap/1.xml",
    )


def test_new_document_downloads_and_uploads_all_source_attachments(monkeypatch) -> None:
    documents = FakeDocuments()
    storage = FakeStorage()
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.fetch_vbpl_document_page",
        lambda url: _page(),
    )
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.download_vbpl_attachment",
        lambda document_id, attachment: attachment.file_name.encode(),
    )

    result = asyncio.run(VbplDocumentIngestionService(documents, storage).ingest(_document_url()))

    assert result["action"] == "created"
    assert result["downloaded_attachment_count"] == 3
    assert len(storage.uploads) == 3
    assert documents.saved is not None
    assert documents.saved.raw_file_ref.startswith(f"{VBPL_STORAGE_BUCKET}/vbpl/175384/")
    assert documents.saved.raw_content_ref.startswith(f"{VBPL_STORAGE_BUCKET}/vbpl/175384/")
    assert len(documents.saved.raw_metadata["stored_files"]) == 3


def test_existing_document_updates_metadata_without_replacing_raw_files(monkeypatch) -> None:
    documents = FakeDocuments(
        {
            "id": "source-document-id",
            "raw_file_ref": "vbpl-raw/old-pdf",
            "raw_file_sha256": "old-pdf-hash",
            "raw_content_ref": "vbpl-raw/old-html",
            "raw_content_sha256": "old-html-hash",
            "raw_metadata": {"stored_files": [{"file_name": "old.pdf", "storage_ref": "vbpl-raw/old-pdf"}]},
        }
    )
    storage = FakeStorage()
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.fetch_vbpl_document_page",
        lambda url: _page(),
    )
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.download_vbpl_attachment",
        lambda *args: (_ for _ in ()).throw(AssertionError("existing files must not be downloaded")),
    )

    result = asyncio.run(VbplDocumentIngestionService(documents, storage).ingest(_document_url()))

    assert result["action"] == "metadata_updated"
    assert result["downloaded_attachment_count"] == 0
    assert storage.uploads == []
    assert documents.saved.raw_file_ref == "vbpl-raw/old-pdf"
    assert documents.saved.raw_file_sha256 == "old-pdf-hash"
    assert documents.saved.raw_content_ref == "vbpl-raw/old-html"
    assert documents.saved.raw_content_sha256 == "old-html-hash"
    assert documents.saved.raw_metadata["stored_files"][0]["storage_ref"] == "vbpl-raw/old-pdf"


def test_existing_metadata_only_document_backfills_missing_source_files(monkeypatch) -> None:
    documents = FakeDocuments({"id": "source-document-id", "raw_metadata": {}})
    storage = FakeStorage()
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.fetch_vbpl_document_page",
        lambda url: _page(),
    )
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.download_vbpl_attachment",
        lambda document_id, attachment: attachment.file_name.encode(),
    )

    result = asyncio.run(VbplDocumentIngestionService(documents, storage).ingest(_document_url()))

    assert result["action"] == "files_backfilled"
    assert result["downloaded_attachment_count"] == 3
    assert len(storage.uploads) == 3
    assert documents.saved is not None
    assert documents.saved.raw_file_ref.startswith(f"{VBPL_STORAGE_BUCKET}/vbpl/175384/")
    assert documents.saved.raw_content_ref.startswith(f"{VBPL_STORAGE_BUCKET}/vbpl/175384/")
    assert len(documents.saved.raw_metadata["stored_files"]) == 3


def test_storage_key_uses_ascii_name_for_unicode_vbpl_file_names() -> None:
    key = _storage_key(
        "659e0ef0-dc14-11f1-853e-e5ac88a55ccb",
        "9d8065b4c51f99586750642d077c389e8fee57976be6f5b4fa85a6a95d531f80",
        "NQ 33.2026 ngày 14.10.2026 Sửa đổi, bổ sung một số điều.pdf",
    )

    assert key.isascii()
    assert key == (
        "vbpl/659e0ef0-dc14-11f1-853e-e5ac88a55ccb/"
        "9d8065b4c51f99586750642d077c389e8fee57976be6f5b4fa85a6a95d531f80/origin.pdf"
    )
