import asyncio
from datetime import date
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from storage3.exceptions import StorageApiError

from src.application.services.vbpl_document_ingestion_service import (
    VBPL_STORAGE_BUCKET,
    VbplDocumentIngestionService,
    _storage_key,
)
from src.applications.tillegal.ingestion.crawler.parsers.word_to_markdown import LegacyDocConverterUnavailableError
from src.applications.tillegal.ingestion.crawler.vbpl_document import (
    VbplAttachment,
    VbplDocumentPage,
)
from src.applications.tillegal.ingestion.crawler.vbpl_sitemap import VbplDocumentUrl


class FakeDocuments:
    def __init__(self, existing: dict[str, object] | None = None, saved_id: str = "source-document-id") -> None:
        self.existing = existing
        self.saved_id = saved_id
        self.saved = None

    async def get_by_source_record_id(self, source_id: str, source_record_id: str):
        return self.existing

    async def upsert(self, document):
        self.saved = document
        return {
            "id": self.saved_id,
            "raw_file_ref": document.raw_file_ref,
            "raw_content_ref": document.raw_content_ref,
        }


class FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, str, bytes, str]] = []
        self.objects: dict[tuple[str, str], bytes] = {}

    def upload(self, bucket: str, key: str, content: bytes, content_type: str) -> None:
        assert bucket == VBPL_STORAGE_BUCKET
        self.uploads.append((bucket, key, content, content_type))
        self.objects[(bucket, key)] = content

    def download(self, bucket: str, key: str) -> bytes:
        return self.objects[(bucket, key)]


class MissingObjectStorage(FakeStorage):
    def download(self, bucket: str, key: str) -> bytes:
        try:
            return super().download(bucket, key)
        except KeyError as error:
            raise StorageApiError("Object not found", "not_found", 404) from error


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


def _page_without_html() -> VbplDocumentPage:
    return VbplDocumentPage(
        document_id="175384",
        title="Nghị quyết",
        metadata={},
        attachments=(
            VbplAttachment("original.pdf", "175384/original.pdf", "application/pdf", 5),
            VbplAttachment(
                "source.docx",
                "175384/source.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                5,
            ),
        ),
    )


def _docx_content() -> bytes:
    document = """<?xml version="1.0" encoding="UTF-8"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body><w:p><w:r><w:t>Document from Word.</w:t></w:r></w:p></w:body>
    </w:document>"""
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as docx:
        docx.writestr("word/document.xml", document)
    return archive.getvalue()


def _document_url() -> VbplDocumentUrl:
    return VbplDocumentUrl(
        "https://vbpl.vn/van-ban/chi-tiet/resolution--175384",
        date(2026, 11, 9),
        "https://vbpl.vn/sitemap/1.xml",
    )


def _download_attachment(document_id: str, attachment: VbplAttachment) -> bytes:
    if attachment.file_name.lower().endswith(".html"):
        return b"<html><body><p>Document <strong>content</strong>.</p></body></html>"
    return attachment.file_name.encode()


def test_new_document_downloads_and_uploads_all_source_attachments(monkeypatch) -> None:
    documents = FakeDocuments()
    storage = FakeStorage()
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.fetch_vbpl_document_page",
        lambda url: _page(),
    )
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.download_vbpl_attachment",
        _download_attachment,
    )

    result = asyncio.run(VbplDocumentIngestionService(documents, storage).ingest(_document_url()))

    assert result["action"] == "created"
    assert result["downloaded_attachment_count"] == 3
    assert result["markdown_created"] is True
    assert len(storage.uploads) == 4
    assert documents.saved is not None
    assert documents.saved.raw_file_ref.startswith(f"{VBPL_STORAGE_BUCKET}/vbpl/175384/")
    assert documents.saved.raw_content_ref.startswith(f"{VBPL_STORAGE_BUCKET}/vbpl/175384/")
    stored_files = documents.saved.raw_metadata["stored_files"]
    assert len(stored_files) == 4
    markdown_file = next(item for item in stored_files if item.get("role") == "normalized_markdown")
    markdown_upload = next(item for item in storage.uploads if item[1].endswith("/origin.md"))
    assert markdown_file["storage_ref"].endswith("/origin.md")
    assert markdown_upload[2].decode("utf-8") == "Document **content**.\n"


def test_ingestion_indexes_stored_markdown_after_persisting_source_document(monkeypatch) -> None:
    documents = FakeDocuments(saved_id="00000000-0000-0000-0000-000000000001")
    storage = FakeStorage()
    observed: list[tuple[object, str, str]] = []
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.fetch_vbpl_document_page",
        lambda url: _page(),
    )
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.download_vbpl_attachment",
        _download_attachment,
    )

    async def index_markdown(source_document_id, title, markdown):
        observed.append((source_document_id, title, markdown))
        return {"chunk_count": 1, "embedding_count": 1}

    result = asyncio.run(
        VbplDocumentIngestionService(
            documents,
            storage,
            markdown_indexer=index_markdown,
        ).ingest(_document_url())
    )

    assert len(observed) == 1
    assert str(observed[0][0]) == "00000000-0000-0000-0000-000000000001"
    assert observed[0][1] == "Nghị quyết"
    assert "Document **content**." in observed[0][2]
    assert result["markdown_indexing"] == {"chunk_count": 1, "embedding_count": 1}


def test_existing_document_updates_metadata_without_replacing_raw_files(monkeypatch) -> None:
    documents = FakeDocuments(
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "raw_file_ref": "vbpl-raw/old-pdf",
            "raw_file_sha256": "old-pdf-hash",
            "raw_content_ref": "vbpl-raw/old-html",
            "raw_content_sha256": "old-html-hash",
            "raw_metadata": {
                "stored_files": [
                    {"file_name": "old.pdf", "storage_ref": "vbpl-raw/old-pdf"},
                    {"file_name": "body.html", "storage_ref": "vbpl-raw/old-html"},
                    {"file_name": "origin.md", "storage_ref": "vbpl-raw/old-md", "role": "normalized_markdown"},
                ]
            },
        },
        saved_id="00000000-0000-0000-0000-000000000001",
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
    assert result["markdown_created"] is False
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
        _download_attachment,
    )

    result = asyncio.run(VbplDocumentIngestionService(documents, storage).ingest(_document_url()))

    assert result["action"] == "files_backfilled"
    assert result["downloaded_attachment_count"] == 3
    assert result["markdown_created"] is True
    assert len(storage.uploads) == 4
    assert documents.saved is not None
    assert documents.saved.raw_file_ref.startswith(f"{VBPL_STORAGE_BUCKET}/vbpl/175384/")
    assert documents.saved.raw_content_ref.startswith(f"{VBPL_STORAGE_BUCKET}/vbpl/175384/")
    assert len(documents.saved.raw_metadata["stored_files"]) == 4


def test_existing_document_creates_markdown_from_stored_html_once(monkeypatch) -> None:
    html_key = "vbpl/175384/html-hash/origin.html"
    documents = FakeDocuments(
        {
            "id": "source-document-id",
            "raw_file_ref": "vbpl-raw/vbpl/175384/pdf-hash/origin.pdf",
            "raw_file_sha256": "pdf-hash",
            "raw_content_ref": f"{VBPL_STORAGE_BUCKET}/{html_key}",
            "raw_content_sha256": "html-hash",
            "raw_metadata": {
                "stored_files": [
                    {"file_name": "original.pdf", "storage_ref": "vbpl-raw/vbpl/175384/pdf-hash/origin.pdf"},
                    {"file_name": "body.html", "storage_ref": f"{VBPL_STORAGE_BUCKET}/{html_key}"},
                ]
            },
        }
    )
    storage = FakeStorage()
    storage.objects[(VBPL_STORAGE_BUCKET, html_key)] = b"<html><body><p>Stored <em>HTML</em>.</p></body></html>"
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.fetch_vbpl_document_page",
        lambda url: _page(),
    )
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.download_vbpl_attachment",
        lambda *args: (_ for _ in ()).throw(AssertionError("stored HTML must be used")),
    )

    result = asyncio.run(VbplDocumentIngestionService(documents, storage).ingest(_document_url()))

    assert result["action"] == "metadata_updated"
    assert result["markdown_created"] is True
    assert result["downloaded_attachment_count"] == 0
    assert len(storage.uploads) == 1
    assert storage.uploads[0][1].endswith("/origin.md")
    assert storage.uploads[0][2] == b"Stored *HTML*.\n"
    assert documents.saved.raw_content_ref == f"{VBPL_STORAGE_BUCKET}/{html_key}"
    assert any(item.get("role") == "normalized_markdown" for item in documents.saved.raw_metadata["stored_files"])


def test_missing_stored_markdown_is_rebuilt_from_source_and_indexed(monkeypatch) -> None:
    source_key = "vbpl/175384/docx-hash/origin.docx"
    documents = FakeDocuments(
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "raw_metadata": {
                "stored_files": [
                    {
                        "file_name": "source.docx",
                        "storage_ref": f"{VBPL_STORAGE_BUCKET}/{source_key}",
                        "sha256": "docx-hash",
                    },
                    {
                        "file_name": "origin.md",
                        "storage_ref": f"{VBPL_STORAGE_BUCKET}/vbpl/175384/missing/origin.md",
                        "role": "normalized_markdown",
                    },
                ]
            },
        },
        saved_id="00000000-0000-0000-0000-000000000001",
    )
    storage = MissingObjectStorage()
    storage.objects[(VBPL_STORAGE_BUCKET, source_key)] = _docx_content()
    observed_markdown: list[str] = []
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.fetch_vbpl_document_page",
        lambda url: _page_without_html(),
    )
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service._convert_markdown_source",
        lambda attachment, content, settings=None: "Rebuilt markdown.\n",
    )

    async def index_markdown(source_document_id, title, markdown):
        observed_markdown.append(markdown)
        return {"chunk_count": 1, "embedding_count": 1}

    result = asyncio.run(
        VbplDocumentIngestionService(
            documents,
            storage,
            markdown_indexer=index_markdown,
        ).ingest(_document_url())
    )

    markdown_files = [
        item for item in documents.saved.raw_metadata["stored_files"] if item.get("role") == "normalized_markdown"
    ]
    assert len(markdown_files) == 1
    assert result["markdown_created"] is True
    assert observed_markdown == ["Rebuilt markdown.\n"]
    assert storage.objects[(VBPL_STORAGE_BUCKET, markdown_files[0]["storage_ref"].removeprefix("vbpl-raw/"))]
    assert result["markdown_indexing"] == {"chunk_count": 1, "embedding_count": 1}


def test_missing_stored_source_is_redownloaded_and_reference_replaced(monkeypatch) -> None:
    page = VbplDocumentPage(
        document_id="175384",
        title="Nghị quyết",
        metadata={},
        attachments=(
            VbplAttachment("original.pdf", "175384/original.pdf", "application/pdf", 5),
            VbplAttachment("source.doc", "175384/source.doc", "application/msword", 5),
        ),
    )
    stale_source_key = "vbpl/175384/missing/origin.doc"
    documents = FakeDocuments(
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "raw_metadata": {
                "stored_files": [
                    {
                        "file_name": "source.doc",
                        "storage_ref": f"{VBPL_STORAGE_BUCKET}/{stale_source_key}",
                        "sha256": "stale-hash",
                    }
                ]
            },
        }
    )
    storage = MissingObjectStorage()
    downloaded: list[str] = []
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.fetch_vbpl_document_page",
        lambda url: page,
    )

    def download(document_id: str, attachment: VbplAttachment) -> bytes:
        downloaded.append(attachment.file_name)
        return b"refetched legal document"

    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.download_vbpl_attachment",
        download,
    )
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service._convert_markdown_source",
        lambda attachment, content, settings=None: "Refetched markdown.\n",
    )

    result = asyncio.run(VbplDocumentIngestionService(documents, storage).ingest(_document_url()))

    source_files = [
        item for item in documents.saved.raw_metadata["stored_files"] if item.get("file_name") == "source.doc"
    ]
    assert downloaded == ["source.doc"]
    assert len(source_files) == 1
    assert source_files[0]["sha256"] != "stale-hash"
    assert storage.objects[(VBPL_STORAGE_BUCKET, source_files[0]["storage_ref"].removeprefix("vbpl-raw/"))]
    assert result["downloaded_attachment_count"] == 1
    assert result["markdown_created"] is True


def test_document_without_html_uses_docx_as_markdown_source(monkeypatch) -> None:
    documents = FakeDocuments()
    storage = FakeStorage()
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.fetch_vbpl_document_page",
        lambda url: _page_without_html(),
    )

    def download(document_id: str, attachment: VbplAttachment) -> bytes:
        return _docx_content() if attachment.file_name.endswith(".docx") else b"pdf"

    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.download_vbpl_attachment",
        download,
    )

    result = asyncio.run(VbplDocumentIngestionService(documents, storage).ingest(_document_url()))

    assert result["markdown_created"] is True
    assert documents.saved.raw_content_ref is None
    markdown_file = next(
        item for item in documents.saved.raw_metadata["stored_files"] if item.get("role") == "normalized_markdown"
    )
    assert markdown_file["source_file_name"] == "source.docx"
    assert markdown_file["source_storage_ref"].endswith("/origin.docx")
    markdown_upload = next(item for item in storage.uploads if item[1].endswith("/origin.md"))
    assert markdown_upload[2] == b"Document from Word.\n"


def test_existing_document_without_html_converts_stored_docx(monkeypatch) -> None:
    docx_key = "vbpl/175384/docx-hash/origin.docx"
    docx_ref = f"{VBPL_STORAGE_BUCKET}/{docx_key}"
    documents = FakeDocuments(
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "raw_file_ref": "vbpl-raw/vbpl/175384/pdf-hash/origin.pdf",
            "raw_file_sha256": "pdf-hash",
            "raw_metadata": {
                "stored_files": [
                    {"file_name": "original.pdf", "storage_ref": "vbpl-raw/vbpl/175384/pdf-hash/origin.pdf"},
                    {"file_name": "source.docx", "storage_ref": docx_ref, "sha256": "docx-hash"},
                ]
            },
        }
    )
    storage = FakeStorage()
    storage.objects[(VBPL_STORAGE_BUCKET, docx_key)] = _docx_content()
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.fetch_vbpl_document_page",
        lambda url: _page_without_html(),
    )
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.download_vbpl_attachment",
        lambda *args: (_ for _ in ()).throw(AssertionError("stored DOCX must be used")),
    )

    result = asyncio.run(VbplDocumentIngestionService(documents, storage).ingest(_document_url()))

    assert result["markdown_created"] is True
    assert result["downloaded_attachment_count"] == 0
    markdown_file = next(
        item for item in documents.saved.raw_metadata["stored_files"] if item.get("role") == "normalized_markdown"
    )
    assert markdown_file["source_file_name"] == "source.docx"
    assert markdown_file["source_storage_ref"] == docx_ref
    assert storage.uploads[0][2] == b"Document from Word.\n"


def test_document_without_html_or_docx_uses_legacy_doc(monkeypatch) -> None:
    page = VbplDocumentPage(
        document_id="175384",
        title="Nghị quyết",
        metadata={},
        attachments=(VbplAttachment("source.doc", "175384/source.doc", "application/msword", 12),),
    )
    documents = FakeDocuments()
    storage = FakeStorage()
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.fetch_vbpl_document_page",
        lambda url: page,
    )
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.download_vbpl_attachment",
        lambda document_id, attachment: bytes.fromhex("D0CF11E0A1B11AE1") + b"legacy doc",
    )
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.convert_word_to_markdown",
        lambda content, file_name: "Document from legacy DOC.\n",
    )

    result = asyncio.run(VbplDocumentIngestionService(documents, storage).ingest(_document_url()))

    assert result["markdown_source_file"] == "source.doc"
    assert documents.saved.raw_content_ref is None
    markdown_file = next(
        item for item in documents.saved.raw_metadata["stored_files"] if item.get("role") == "normalized_markdown"
    )
    assert markdown_file["source_file_name"] == "source.doc"
    markdown_upload = next(item for item in storage.uploads if item[1].endswith("/origin.md"))
    assert markdown_upload[2] == b"Document from legacy DOC.\n"


def test_missing_antiword_skips_doc_markdown_without_failing_ingestion(monkeypatch) -> None:
    page = VbplDocumentPage(
        document_id="175384",
        title="Nghị quyết",
        metadata={},
        attachments=(VbplAttachment("source.doc", "175384/source.doc", "application/msword", 12),),
    )
    documents = FakeDocuments()
    storage = FakeStorage()
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.fetch_vbpl_document_page",
        lambda url: page,
    )
    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service.download_vbpl_attachment",
        lambda document_id, attachment: bytes.fromhex("D0CF11E0A1B11AE1") + b"legacy doc",
    )

    def missing_antiword(attachment, content):
        raise LegacyDocConverterUnavailableError("antiword is unavailable")

    monkeypatch.setattr(
        "src.application.services.vbpl_document_ingestion_service._convert_markdown_source",
        missing_antiword,
    )

    result = asyncio.run(VbplDocumentIngestionService(documents, storage).ingest(_document_url()))

    assert result["markdown_created"] is False
    assert result["markdown_skipped_reason"] == "antiword_unavailable"
    assert documents.saved is not None
    assert documents.saved.raw_metadata["markdown_skipped_reason"] == "antiword_unavailable"
    assert any(item["file_name"] == "source.doc" for item in documents.saved.raw_metadata["stored_files"])
    assert not any(item[1].endswith("/origin.md") for item in storage.uploads)


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
