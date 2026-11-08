"""Explicit composition root for transferred modules; no graph changes."""

import asyncio
from dataclasses import dataclass

from src.applications.tillegal.agents.judge.agent import JudgeAgent
from src.applications.tillegal.agents.judge.schemas import anthropic_output_schema
from src.applications.tillegal.agents.response.agent import SummaryAgent, check_provider_schema
from src.applications.tillegal.ingestion.legal_parser import make_chunks
from src.applications.tillegal.ingestion.service import IngestionService
from src.applications.tillegal.retrieval.service import RetrievalService
from src.framework.llm.gateway import ModelGateway


@dataclass
class RagServices:
    ingestion: IngestionService
    retrieval: RetrievalService


@dataclass
class TillegalModules(RagServices):
    judge: JudgeAgent
    summary: SummaryAgent

    async def evaluate(self, value: dict, *, telemetry=None) -> dict:
        return await asyncio.to_thread(self.judge.evaluate, value, telemetry=telemetry)

    async def summarize(self, value: dict, *, telemetry=None) -> dict:
        return await asyncio.to_thread(self.summary.summarize, value, telemetry=telemetry)


def create_tillegal_modules(
    *, store, embedder, judge_provider, summary_provider, reranker=None, chunker=make_chunks
) -> TillegalModules:
    # Validate decoding schemas before wrapping concrete providers behind the gateway.
    from src.integrations.llm.anthropic_provider import AnthropicProvider

    if isinstance(judge_provider, AnthropicProvider) and judge_provider.structured_output:
        if judge_provider.output_schema != anthropic_output_schema():
            raise ValueError("JUDGE_PROVIDER_SCHEMA_MISMATCH")
    check_provider_schema(summary_provider)
    return TillegalModules(
        IngestionService(store, embedder, chunker=chunker),
        RetrievalService(store, embedder, reranker),
        JudgeAgent(ModelGateway(judge_provider)),
        SummaryAgent(ModelGateway(summary_provider)),
    )


def create_local_modules(
    client, *, model_path, revision, judge_provider, summary_provider, reranker=None, chunker=make_chunks
):
    """Standalone startup factory. The caller owns the Supabase client and snapshot paths."""
    store, embedder = _local_dependencies(client, model_path, revision)
    return create_tillegal_modules(
        store=store,
        embedder=embedder,
        judge_provider=judge_provider,
        summary_provider=summary_provider,
        reranker=reranker,
        chunker=chunker,
    )


def create_local_rag_services(client, *, model_path, revision, chunker=make_chunks) -> RagServices:
    store, embedder = _local_dependencies(client, model_path, revision)
    return RagServices(IngestionService(store, embedder, chunker=chunker), RetrievalService(store, embedder))


def _local_dependencies(client, model_path, revision):
    from src.integrations.database.repositories.version_window_repository import VersionWindowRepository
    from src.integrations.embedding.adapter import LocalEmbeddingAdapter
    from src.integrations.embedding.local_encoder import LocalEncoder

    return VersionWindowRepository(client), LocalEmbeddingAdapter(LocalEncoder(model_path, revision))
