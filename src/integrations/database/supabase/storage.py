"""Supabase Storage adapter for ingestion objects."""

from supabase import Client


class SupabaseObjectStorage:
    """Read and write files using the configured Supabase client."""

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

    def download(self, bucket: str, object_key: str) -> bytes:
        content = self._client.storage.from_(bucket).download(object_key)
        if not isinstance(content, bytes):
            raise TypeError("Supabase Storage returned a non-bytes object")
        return content
