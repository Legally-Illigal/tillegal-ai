"""Compare warm pilot workflows in-process on identical questions and retrieval settings."""
import logging
import os
from statistics import median
from time import perf_counter
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.bootstrap import create_app
from src.core.config import AppSettings


def main():
    logging.disable(logging.CRITICAL)
    config = {"TILLEGAL_RAG_PILOT": "1", "TILLEGAL_RETRIEVAL_MODE": "bm25",
              "TILLEGAL_ANSWER_PROVIDER": "mock", "TILLEGAL_RESPONSE_PROVIDER": "mock",
              "TILLEGAL_RERANK": "false", "TILLEGAL_SEARCH_BUDGET": "4", "TILLEGAL_SEARCH_ROUNDS": "2"}
    with patch.dict(os.environ, config), TestClient(create_app(AppSettings())) as client:
        for question in ("Trích dẫn: đối thoại", "đối thoại; nghỉ phép"):
            samples = {"basic": [], "multi_agent": []}
            for i in range(6):
                for mode in samples if i % 2 == 0 else reversed(samples):
                    started = perf_counter()
                    res = client.post("/pilot/legal-qa", json={"question": question, "top_k": 1, "workflow": mode})
                    elapsed = (perf_counter()-started)*1000
                    res.raise_for_status()
                    if i:
                        samples[mode].append(elapsed)
                    result = res.json()
                    if i == 5:
                        print(mode, result["status"], "calls", len(result.get("retrieval_trace", [1])))
            print(question, {mode: round(median(ms), 1) for mode, ms in samples.items()})


if __name__ == "__main__":
    main()
