"""Persist VBPL document metadata and source files."""

import asyncio
import hashlib
import mimetypes
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from storage3.exceptions import StorageApiError

from src.application.dto.source_document import SourceDocumentWrite
from src.application.interfaces.object_storage import ObjectStorage
from src.application.interfaces.source_document_store import SourceDocumentStore
from src.applications.tillegal.ingestion.crawler.parsers.html_to_markdown import convert_html_to_markdown
from src.applications.tillegal.ingestion.crawler.parsers.word_to_markdown import (
    LegacyDocConverterUnavailableError,
    convert_word_to_markdown,
)
from src.applications.tillegal.ingestion.crawler.vbpl_document import (
    VbplAttachment,
    download_vbpl_attachment,
    fetch_vbpl_document_page,
)
from src.applications.tillegal.ingestion.crawler.vbpl_sitemap import VbplDocumentUrl
from src.core.config import VbplCrawlSettings

VBPL_STORAGE_BUCKET = "vbpl-raw"
SOURCE_ID = "vbpl"
MARKDOWN_CONTENT_TYPE = "text/markdown; charset=utf-8"


class VbplDocumentIngestionService:
    """Fetch VBPL source metadata/files and upsert the stable document record."""

    def __init__(
        self,
        documents: SourceDocumentStore,
        storage: ObjectStorage,
        *,
        bucket: str = VBPL_STORAGE_BUCKET,
        settings: VbplCrawlSettings | None = None,
        markdown_indexer: Callable[[UUID, str, str], Awaitable[dict[str, object]]] | None = None,
    ) -> None:
        if not bucket.strip():
            raise ValueError("VBPL storage bucket must not be empty")
        self._documents = documents
        self._storage = storage
        self._bucket = bucket
        self._settings = settings
        self._markdown_indexer = markdown_indexer

    async def ingest(self, document_url: VbplDocumentUrl) -> dict[str, object]:
        """Ingest one discovered document, retaining previously stored file versions."""
        if self._settings is None:
            page = await asyncio.to_thread(fetch_vbpl_document_page, document_url.url)
        else:
            page = await asyncio.to_thread(fetch_vbpl_document_page, document_url.url, self._settings)
        existing = await self._documents.get_by_source_record_id(SOURCE_ID, page.document_id)
        previous_metadata = _mapping(existing.get("raw_metadata")) if existing is not None else {}
        previous_stored_files = _stored_files(previous_metadata)
        stored_files = previous_stored_files
        raw_file_ref = _optional_string(existing, "raw_file_ref")
        raw_file_sha256 = _optional_string(existing, "raw_file_sha256")
        raw_content_ref = _optional_string(existing, "raw_content_ref")
        raw_content_sha256 = _optional_string(existing, "raw_content_sha256")
        downloaded_count = 0
        markdown_created = False
        markdown_skipped_reason: str | None = None
        html_attachment = _body_html_attachment(page.attachments)
        source_attachment = _markdown_source_attachment(page.attachments, html_attachment)
        downloaded_contents: dict[str, bytes] = {}
        markdown_content_for_indexing: bytes | None = None
        needs_file_backfill = (
            existing is not None and raw_file_ref is None and raw_content_ref is None and not previous_stored_files
        )

        markdown_file = _stored_file_for_role(stored_files, "normalized_markdown")
        markdown_ref = _optional_string(markdown_file, "storage_ref")
        if self._markdown_indexer is not None and markdown_ref is not None:
            markdown_bucket, markdown_key = _storage_location(markdown_ref, self._bucket)
            try:
                markdown_content_for_indexing = await asyncio.to_thread(
                    self._storage.download,
                    markdown_bucket,
                    markdown_key,
                )
            except StorageApiError as error:
                if not _is_missing_storage_object(error):
                    raise
                stored_files = [item for item in stored_files if item is not markdown_file]

        if existing is None or needs_file_backfill:
            stored_files = list(stored_files)
            for attachment in page.attachments:
                if any(item.get("file_name") == attachment.file_name for item in stored_files):
                    continue
                content = await self._download_attachment(page.document_id, attachment)
                digest = hashlib.sha256(content).hexdigest()
                object_key = _storage_key(page.document_id, digest, attachment.file_name)
                await asyncio.to_thread(self._upload, object_key, content, _content_type(attachment))
                stored_files.append(
                    {
                        "file_name": attachment.file_name,
                        "storage_ref": f"{self._bucket}/{object_key}",
                        "sha256": digest,
                        "size": len(content),
                        "content_type": _content_type(attachment),
                    }
                )
                if attachment == html_attachment:
                    downloaded_contents[attachment.file_name] = content
                if attachment == source_attachment:
                    downloaded_contents[attachment.file_name] = content
                downloaded_count += 1

            pdf_file = _stored_file_for_extension(stored_files, ".pdf")
            html_file = _stored_file_for_extension(stored_files, (".html", ".htm"))
            if pdf_file is not None:
                raw_file_ref = _optional_string(pdf_file, "storage_ref")
                raw_file_sha256 = _optional_string(pdf_file, "sha256")
            if html_file is not None:
                raw_content_ref = _optional_string(html_file, "storage_ref")
                raw_content_sha256 = _optional_string(html_file, "sha256")
        else:
            if raw_file_ref is None:
                pdf_file = _stored_file_for_extension(stored_files, ".pdf")
                if pdf_file is not None:
                    raw_file_ref = _optional_string(pdf_file, "storage_ref")
                    raw_file_sha256 = _optional_string(pdf_file, "sha256")
            if raw_content_ref is None:
                html_file = _stored_file_for_extension(stored_files, (".html", ".htm"))
                if html_file is not None:
                    raw_content_ref = _optional_string(html_file, "storage_ref")
                    raw_content_sha256 = _optional_string(html_file, "sha256")

        if source_attachment is not None and not _has_markdown(stored_files):
            source_file = _stored_file_for_name(stored_files, source_attachment.file_name)
            source_ref = _optional_string(source_file, "storage_ref")
            source_sha256 = _optional_string(source_file, "sha256")
            if source_ref is None and source_attachment == html_attachment and raw_content_ref is not None:
                source_ref = raw_content_ref
                source_sha256 = raw_content_sha256
                stored_files.append(
                    {
                        "file_name": source_attachment.file_name,
                        "storage_ref": source_ref,
                        "sha256": source_sha256,
                        "size": source_attachment.size,
                        "content_type": _content_type(source_attachment),
                    }
                )

            source_content = downloaded_contents.get(source_attachment.file_name)
            if source_content is None and source_ref is not None:
                storage_bucket, object_key = _storage_location(source_ref, self._bucket)
                try:
                    source_content = await asyncio.to_thread(
                        self._storage.download,
                        storage_bucket,
                        object_key,
                    )
                except StorageApiError as error:
                    if not _is_missing_storage_object(error):
                        raise

            if source_content is None:
                source_content = await self._download_attachment(page.document_id, source_attachment)
                source_sha256 = hashlib.sha256(source_content).hexdigest()
                source_key = _storage_key(page.document_id, source_sha256, source_attachment.file_name)
                source_ref = f"{self._bucket}/{source_key}"
                await asyncio.to_thread(
                    self._upload,
                    source_key,
                    source_content,
                    _content_type(source_attachment),
                )
                _replace_stored_file(
                    stored_files,
                    source_attachment.file_name,
                    {
                        "file_name": source_attachment.file_name,
                        "storage_ref": source_ref,
                        "sha256": source_sha256,
                        "size": len(source_content),
                        "content_type": _content_type(source_attachment),
                    },
                )
                downloaded_count += 1
                if source_attachment == html_attachment:
                    raw_content_ref = source_ref
                    raw_content_sha256 = source_sha256

            try:
                if self._settings is None:
                    markdown = await asyncio.to_thread(
                        _convert_markdown_source,
                        source_attachment,
                        source_content,
                    )
                else:
                    markdown = await asyncio.to_thread(
                        _convert_markdown_source,
                        source_attachment,
                        source_content,
                        self._settings,
                    )
            except LegacyDocConverterUnavailableError:
                markdown_skipped_reason = "antiword_unavailable"
            else:
                markdown_content = markdown.encode("utf-8")
                markdown_digest = hashlib.sha256(markdown_content).hexdigest()
                markdown_key = _storage_key(page.document_id, markdown_digest, "origin.md")
                await asyncio.to_thread(self._upload, markdown_key, markdown_content, MARKDOWN_CONTENT_TYPE)
                markdown_content_for_indexing = markdown_content
                _replace_stored_file(
                    stored_files,
                    "origin.md",
                    {
                        "file_name": "origin.md",
                        "source_file_name": source_attachment.file_name,
                        "storage_ref": f"{self._bucket}/{markdown_key}",
                        "sha256": markdown_digest,
                        "size": len(markdown_content),
                        "content_type": MARKDOWN_CONTENT_TYPE,
                        "role": "normalized_markdown",
                        "source_storage_ref": source_ref,
                        "source_sha256": source_sha256,
                    },
                )
                markdown_created = True

        metadata: dict[str, object] = {
            **page.metadata,
            "sitemap_lastmod": document_url.lastmod.isoformat(),
            "sitemap_url": document_url.sitemap_url,
            "source_files": [_attachment_metadata(item, page.document_id) for item in page.attachments],
            "stored_files_refreshed": downloaded_count > 0,
        }
        if markdown_skipped_reason is not None:
            metadata["markdown_skipped_reason"] = markdown_skipped_reason
        if existing is None or needs_file_backfill or "stored_files" in previous_metadata or markdown_created:
            metadata["stored_files"] = stored_files
        saved = await self._documents.upsert(
            SourceDocumentWrite(
                source_id=SOURCE_ID,
                source_record_id=page.document_id,
                title=page.title,
                language="vi",
                source_url=document_url.url,
                issued_on=page.issued_on,
                effective_from=page.effective_from,
                effective_to=page.effective_to,
                effect_status_reported=page.effect_status_reported,
                raw_file_ref=raw_file_ref,
                raw_file_sha256=raw_file_sha256,
                raw_content_ref=raw_content_ref,
                raw_content_sha256=raw_content_sha256,
                raw_metadata=metadata,
                collected_at=datetime.now(UTC),
            )
        )
        if raw_file_ref is not None and saved.get("raw_file_ref") != raw_file_ref:
            raise RuntimeError("Database did not persist raw_file_ref; apply the VBPL source-document migration")
        if raw_content_ref is not None and saved.get("raw_content_ref") != raw_content_ref:
            raise RuntimeError("Database did not persist raw_content_ref; apply the VBPL source-document migration")
        markdown_indexing: dict[str, object] | None = None
        markdown_file = _stored_file_for_role(stored_files, "normalized_markdown")
        if self._markdown_indexer is not None and markdown_file is not None:
            source_document_id = _required_uuid(saved.get("id"), "source document id")
            current_markdown_ref = _optional_string(markdown_file, "storage_ref")
            if current_markdown_ref is None:
                raise RuntimeError("Stored normalized Markdown is missing its Storage reference")
            if markdown_content_for_indexing is None:
                markdown_bucket, markdown_key = _storage_location(current_markdown_ref, self._bucket)
                markdown_content_for_indexing = await asyncio.to_thread(
                    self._storage.download,
                    markdown_bucket,
                    markdown_key,
                )
            markdown_indexing = await self._markdown_indexer(
                source_document_id,
                page.title,
                markdown_content_for_indexing.decode("utf-8"),
            )
        return {
            "source_document_id": saved.get("id"),
            "source_record_id": page.document_id,
            "action": (
                "created" if existing is None else "files_backfilled" if downloaded_count else "metadata_updated"
            ),
            "attachment_count": len(page.attachments),
            "downloaded_attachment_count": downloaded_count,
            "markdown_created": markdown_created,
            "markdown_source_file": source_attachment.file_name if markdown_created and source_attachment else None,
            "markdown_skipped_reason": markdown_skipped_reason,
            "markdown_indexing": markdown_indexing,
        }

    def _upload(self, object_key: str, content: bytes, content_type: str) -> None:
        self._storage.upload(self._bucket, object_key, content, content_type)

    async def _download_attachment(self, document_id: str, attachment: VbplAttachment) -> bytes:
        if self._settings is None:
            return await asyncio.to_thread(download_vbpl_attachment, document_id, attachment)
        return await asyncio.to_thread(download_vbpl_attachment, document_id, attachment, self._settings)


def _mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _optional_string(value: dict[str, object] | None, key: str) -> str | None:
    if value is None:
        return None
    result = value.get(key)
    return result if isinstance(result, str) else None


def _stored_files(metadata: dict[str, object]) -> list[dict[str, object]]:
    files = metadata.get("stored_files")
    if not isinstance(files, list):
        return []
    return [item for item in files if isinstance(item, dict)]


def _stored_file_for_extension(
    files: list[dict[str, object]],
    extension: str | tuple[str, ...],
) -> dict[str, object] | None:
    suffixes = (extension,) if isinstance(extension, str) else extension
    return next(
        (
            item
            for item in files
            if isinstance(item.get("file_name"), str) and item["file_name"].lower().endswith(suffixes)
        ),
        None,
    )


def _stored_file_for_name(files: list[dict[str, object]], file_name: str) -> dict[str, object] | None:
    return next((item for item in files if item.get("file_name") == file_name), None)


def _stored_file_for_role(files: list[dict[str, object]], role: str) -> dict[str, object] | None:
    return next((item for item in files if item.get("role") == role), None)


def _replace_stored_file(files: list[dict[str, object]], file_name: str, replacement: dict[str, object]) -> None:
    files[:] = [item for item in files if item.get("file_name") != file_name]
    files.append(replacement)


def _is_missing_storage_object(error: StorageApiError) -> bool:
    return str(error.status) == "404" and error.code.lower() in {"not_found", "object_not_found"}


def _required_uuid(value: object, field_name: str) -> UUID:
    if not isinstance(value, str):
        raise RuntimeError(f"Database response is missing {field_name}")
    try:
        return UUID(value)
    except ValueError as error:
        raise RuntimeError(f"Database returned an invalid {field_name}") from error


def _body_html_attachment(attachments: tuple[VbplAttachment, ...]) -> VbplAttachment | None:
    html_attachments = [item for item in attachments if item.file_name.lower().endswith((".html", ".htm"))]
    return next(
        (item for item in html_attachments if "body_content" in item.file_name.lower()),
        html_attachments[0] if html_attachments else None,
    )


def _markdown_source_attachment(
    attachments: tuple[VbplAttachment, ...],
    html_attachment: VbplAttachment | None,
) -> VbplAttachment | None:
    if html_attachment is not None:
        return html_attachment
    word_attachments = [item for item in attachments if item.file_name.lower().endswith((".docx", ".doc"))]
    return next((item for item in word_attachments if item.file_name.lower().endswith(".docx")), None) or next(
        iter(word_attachments),
        None,
    )


def _convert_markdown_source(
    attachment: VbplAttachment,
    content: bytes,
    settings: VbplCrawlSettings | None = None,
) -> str:
    if attachment.file_name.lower().endswith((".html", ".htm")):
        return convert_html_to_markdown(content)
    if settings is not None:
        return convert_word_to_markdown(content, attachment.file_name, settings.doc_conversion_timeout_seconds)
    return convert_word_to_markdown(content, attachment.file_name)


def _has_markdown(files: list[dict[str, object]]) -> bool:
    return any(item.get("role") == "normalized_markdown" for item in files)


def _storage_location(storage_ref: str, expected_bucket: str) -> tuple[str, str]:
    bucket, separator, object_key = storage_ref.partition("/")
    if not separator or bucket != expected_bucket or not object_key:
        raise ValueError(f"Invalid VBPL Storage reference: {storage_ref}")
    return bucket, object_key


def _storage_key(document_id: str, digest: str, file_name: str) -> str:
    extension_match = re.search(r"\.([A-Za-z0-9]{1,10})$", file_name)
    extension = extension_match.group(1).lower() if extension_match is not None else "bin"
    return f"vbpl/{document_id}/{digest}/origin.{extension}"


def _content_type(attachment: VbplAttachment) -> str:
    guessed, _ = mimetypes.guess_type(attachment.file_name)
    return guessed or attachment.content_type


def _attachment_metadata(attachment: VbplAttachment, document_id: str) -> dict[str, object]:
    return {
        "file_name": attachment.file_name,
        "full_path": attachment.full_path or f"{document_id}/{attachment.file_name}",
        "content_type": _content_type(attachment),
        "size": attachment.size,
    }
