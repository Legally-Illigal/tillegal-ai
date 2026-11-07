"""Read-only access to the pinned pilot index."""
from threading import Lock

from pydantic import BaseModel, ConfigDict, Field

from ai_core.bm25_retrieval import load_index
from ai_core.evidence_builder import EvidenceBuilder
from ai_core.retrieval_runtime import make_retriever
from src.framework.tools.contracts import ToolSpec


class SearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=10000)
    request_id: str = Field(min_length=1, max_length=128)
    top_k: int = Field(ge=1, le=100, strict=True)


class LegalRetrieval:
    def __init__(self, manifest, mode, rerank):
        self.index = load_index(manifest)
        self.retriever = make_retriever(self.index, mode, rerank)
        self.builder = EvidenceBuilder(self.index)
        self.lock = Lock()

    def search(self, args: SearchInput):
        # A cancelled async caller can leave a native inference call running.
        if not self.lock.acquire(blocking=False):
            raise BlockingIOError("retriever busy")
        try:
            hits = self.retriever.search(args.question, args.top_k)
            return self.builder.build(hits, request_id=args.request_id)
        finally:
            self.lock.release()

    def tool(self):
        return ToolSpec("legal_retrieval", "Search the experimental local corpus", SearchInput,
                        self.search, frozenset({"pilot.read"}), timeout_seconds=30)
