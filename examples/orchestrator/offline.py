"""Replay explicit synthetic fixtures through the production single-pass entrypoint."""

import asyncio
import json
import sys
from copy import deepcopy
from pathlib import Path

from src.applications.tillegal.agents.judge.agent import FixtureJudgeProvider
from src.applications.tillegal.agents.query.agent import QueryPlan
from src.applications.tillegal.agents.response.agent import FixtureSummaryProvider
from src.applications.tillegal.agents.search.agent import SearchOptions
from src.applications.tillegal.retrieval.contracts import RetrievalResponse
from src.framework.runtime.execution_context import ExecutionContext
from src.qa_bootstrap import create_single_pass_workflow
from src.query_search_bootstrap import QuerySearch


class ReplayPlanner:
    def __init__(self, plan):
        self.plan = QueryPlan.model_validate(plan).model_dump(mode="json")

    async def understand(self, question):
        if question != self.plan["original"]:
            raise ValueError("FIXTURE_QUESTION_MISMATCH")
        return deepcopy(self.plan)


class ReplayRetrieval:
    def __init__(self, responses):
        self.responses = [RetrievalResponse.model_validate(r) for r in responses]

    async def search(self, request):
        for response in self.responses:
            if all(getattr(response, k) == v for k, v in request.model_dump().items()):
                return response.model_copy(deep=True)
        raise ValueError("FIXTURE_REQUEST_MISMATCH")


async def main():
    fixture = json.loads(Path(__file__).with_name("fixture.json").read_text(encoding="utf-8"))
    pipeline = QuerySearch(
        ReplayRetrieval(fixture["responses"]),
        SearchOptions.model_validate(fixture["options"]),
        ReplayPlanner(fixture["plan"]),
    )
    workflow = create_single_pass_workflow(
        pipeline,
        judge_provider=FixtureJudgeProvider(fixture["judge_response"]),
        summary_provider=FixtureSummaryProvider(fixture["summary_response"]),
    )
    return await workflow.execute(
        fixture["plan"]["original"],
        ExecutionContext(run_id="offline-demo", request_id="offline-demo"),
        timeout_seconds=10,
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(asyncio.run(main()).model_dump_json(indent=2))
