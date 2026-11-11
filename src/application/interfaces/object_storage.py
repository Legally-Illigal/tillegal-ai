"""Object storage contract for ingestion use cases."""

from typing import Protocol


class ObjectStorage(Protocol):
    """Read and write objects in a named bucket."""

    def upload(
        self,
        bucket: str,
        object_key: str,
        content: bytes,
        content_type: str,
    ) -> None: ...

    def download(self, bucket: str, object_key: str) -> bytes: ...
