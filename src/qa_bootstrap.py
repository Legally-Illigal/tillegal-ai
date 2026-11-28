"""Dependency injection for the single-pass QA workflow; no implicit network setup."""

from src.applications.tillegal.agents.judge.agent import JudgeAgent
from src.applications.tillegal.agents.response.agent import SummaryAgent
from src.applications.tillegal.graphs.single_pass import SinglePassWorkflow
from src.query_search_bootstrap import QuerySearch


def create_single_pass_workflow(
    pipeline: QuerySearch, *, judge_provider, summary_provider, allow_live: bool = False
) -> SinglePassWorkflow:
    """Inject already configured services. Unknown provider modes require live opt-in.

    The caller must also explicitly construct any live retrieval/query services.
    Providers shared across requests must be thread safe and set their own I/O timeout.
    """
    if not allow_live and any(
        getattr(provider, "mode", None) != "mock" for provider in (judge_provider, summary_provider)
    ):
        raise ValueError("QA_LIVE_PROVIDER_OPT_IN_REQUIRED")
    return SinglePassWorkflow(pipeline, JudgeAgent(judge_provider), SummaryAgent(summary_provider))
