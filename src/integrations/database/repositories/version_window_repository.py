"""Map staging IDs to immutable database records and store E5 windows atomically."""

from uuid import UUID

from src.applications.tillegal.ingestion.data_contracts import ContractError
from src.integrations.database.repositories.parsed_document_repository import ParsedDocumentWrite
from src.integrations.database.repositories.rpc import DatabaseRepositoryError, SupabaseRpcRepository
from src.integrations.database.repositories.source_document_repository import SourceDocumentWrite


def persistence_payload(document, parsed):
    # The legacy source table has one row/structure per upstream record. Reserve
    # a namespace for immutable version rows. Preserve original source fields.
    staging = {k: v for k, v in document.items() if k != "content"}
    source = {k: v for k, v in document.items() if k in SourceDocumentWrite.model_fields}
    source.update(
        source_id="tillegal:staging-version:v1",
        source_record_id=document["document_version_id"],
        raw_metadata={"staging": staging},
        raw_content=document["content"],
        raw_content_sha256=document["content_sha256"],
        raw_content_format=document["content_format"],
        raw_file_ref=document["raw_ref"]["uri"],
        raw_file_sha256=document["raw_ref"]["file_sha256"],
        title=document["title"] or document["document_id"],
    )
    # The transaction binds the generated FK. The source model requires a display
    # title, while original nullable title lives in staging and is used in citations.
    structure = {
        k: parsed[k] for k in ("schema_version", "parser_version", "max_chars", "content_sha256", "excluded_segments")
    }
    structure.update(source_document_id=UUID(int=0), issues=[{"code": i} for i in parsed["issues"]])
    nodes = [
        dict(
            node_id=n["node_id"],
            kind=n["kind"],
            parent_node_id=n["parent_id"],
            label=n["label"],
            scope=n["scope"],
            heading_block_id=n["heading_block_id"],
            ordinal=i,
            metadata=n,
        )
        for i, n in enumerate(parsed["nodes"])
    ]
    blocks = [
        dict(
            block_id=b["block_id"],
            content=b["text"],
            node_id=b["node_id"],
            block_type=b["kind"],
            ordinal=i,
            start_offset=b["source_start"],
            end_offset=b["source_end"],
            metadata=b,
        )
        for i, b in enumerate(parsed["blocks"])
    ]
    chunks = [
        dict(
            chunk_key=c["chunk_id"],
            content=c["text"],
            content_sha256=c["text_sha256"],
            node_id=c["node_id"],
            block_id=c["block_id"],
            chunk_type=c["block_kind"],
            ordinal=i,
            start_offset=c["text_start"],
            end_offset=c["text_end"],
            metadata=c,
        )
        for i, c in enumerate(parsed["chunks"])
    ]
    mapped = ParsedDocumentWrite(structure=structure, nodes=nodes, blocks=blocks, chunks=chunks).model_dump(mode="json")
    mapped["structure"].pop("source_document_id")
    return SourceDocumentWrite(**source).model_dump(mode="json"), mapped


class VersionWindowRepository(SupabaseRpcRepository):
    async def save(self, document, parsed, profile, windows):
        source, mapped = persistence_payload(document, parsed)
        result = await self.call_rpc(
            "save_staging_version", {"p_source": source, "p_parsed": mapped, "p_profile": profile, "p_windows": windows}
        )
        if result != document["document_version_id"]:
            raise DatabaseRepositoryError("Unexpected stored version identity")
        return result

    async def load(self, version_ids, profile):
        if not version_ids or len(set(version_ids)) != len(version_ids):
            raise ContractError("Expected explicit unique version IDs")
        records = []
        for vid in sorted(version_ids):
            row = await self.call_rpc("read_staging_version", {"p_version": vid, "p_profile": profile})
            if not isinstance(row, dict) or row.get("document", {}).get("document_version_id") != vid:
                raise DatabaseRepositoryError("Version/profile unavailable")
            records.append(row)
        return records
