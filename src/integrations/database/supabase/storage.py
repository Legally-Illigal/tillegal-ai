"""Supabase Storage adapter for ingestion objects."""

from supabase import Client


class SupabaseObjectStorage:
    """Upload files using the configured Supabase client."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def upload(
        self,
        bucket: str,
        object_key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        self._client.storage.from_(bucket).upload(
            object_key,
            content,
            file_options={"content-type": content_type, "upsert": "true"},
        )
