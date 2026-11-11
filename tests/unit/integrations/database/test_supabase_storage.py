from src.integrations.database.supabase.storage import SupabaseObjectStorage


class FakeBucket:
    def __init__(self) -> None:
        self.uploaded: tuple[str, bytes, dict[str, str]] | None = None
        self.downloaded: str | None = None
        self.content = b"stored object"

    def upload(self, path: str, content: bytes, *, file_options: dict[str, str]) -> None:
        self.uploaded = (path, content, file_options)

    def download(self, path: str) -> bytes:
        self.downloaded = path
        return self.content


class FakeStorage:
    def __init__(self, bucket: FakeBucket) -> None:
        self.bucket = bucket
        self.bucket_name: str | None = None

    def from_(self, bucket_name: str) -> FakeBucket:
        self.bucket_name = bucket_name
        return self.bucket


class FakeClient:
    def __init__(self) -> None:
        self.bucket = FakeBucket()
        self.storage = FakeStorage(self.bucket)


def test_supabase_storage_uploads_to_the_selected_bucket() -> None:
    client = FakeClient()
    storage = SupabaseObjectStorage(client)  # type: ignore[arg-type]

    storage.upload("vbpl-raw", "vbpl/175384/hash/source.pdf", b"%PDF-1.7", "application/pdf")

    assert client.storage.bucket_name == "vbpl-raw"
    assert client.bucket.uploaded == (
        "vbpl/175384/hash/source.pdf",
        b"%PDF-1.7",
        {"content-type": "application/pdf", "upsert": "true"},
    )


def test_supabase_storage_downloads_from_the_selected_bucket() -> None:
    client = FakeClient()
    storage = SupabaseObjectStorage(client)  # type: ignore[arg-type]

    content = storage.download("vbpl-raw", "vbpl/175384/hash/origin.html")

    assert client.storage.bucket_name == "vbpl-raw"
    assert client.bucket.downloaded == "vbpl/175384/hash/origin.html"
    assert content == b"stored object"
