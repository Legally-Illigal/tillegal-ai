"""Database repository adapters."""

from src.integrations.database.repositories.chunk_repository import ChunkRepository
from src.integrations.database.repositories.dense_index_repository import DenseIndexRepository
from src.integrations.database.repositories.execution_repository import ExecutionRepository
from src.integrations.database.repositories.outbox_repository import OutboxLeaseError, OutboxRepository
from src.integrations.database.repositories.parsed_document_repository import ParsedDocumentRepository
from src.integrations.database.repositories.source_document_repository import SourceDocumentRepository
from src.integrations.database.repositories.sparse_index_repository import SparseIndexRepository
from src.integrations.database.repositories.sparse_retrieval_repository import SparseRetrievalRepository
from src.integrations.database.repositories.supabase_vector_repository import SupabaseVectorRepository

__all__ = [
    "ChunkRepository",
    "DenseIndexRepository",
    "ExecutionRepository",
    "OutboxLeaseError",
    "OutboxRepository",
    "ParsedDocumentRepository",
    "SourceDocumentRepository",
    "SparseIndexRepository",
    "SparseRetrievalRepository",
    "SupabaseVectorRepository",
]
