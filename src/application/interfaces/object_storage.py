"""Object storage contract for ingestion use cases."""

from typing import Protocol


class ObjectStorage(Protocol):
    """Upload an immutable object to a named bucket."""

    def upload(
        self,
        bucket: str,
        object_key: str,
        content: bytes,
        content_type: str,
    ) -> None: ...
