"""Explicit no-secret pilot HTTP smoke, also usable for isolated runtime artifacts."""

import argparse
import hashlib
import json
import os
import platform
import unicodedata
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.bootstrap import create_app
from src.core.config import AppSettings

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True)
    parser.add_argument("--provider", choices=["mock", "local"], default="mock")
    parser.add_argument(
        "--question", default="Đối thoại định kỳ tại nơi làm việc được tổ chức ít nhất bao lâu một lần?"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("New output required")
    config = {
        "TILLEGAL_RAG_PILOT": "1",
        "TILLEGAL_INDEX": args.index,
        "TILLEGAL_ANSWER_PROVIDER": args.provider,
        "TILLEGAL_ANSWER_MODEL": "qwen-pilot",
        "TILLEGAL_LOCAL_PORT": "18963",
        "TILLEGAL_CONTEXT_POLICY": "context_judge",
    }
    with patch.dict(os.environ, config, clear=True), TestClient(create_app(AppSettings())) as client:
        response = client.post(
            "/pilot/legal-qa",
            json={
                "question": args.question,
                "top_k": 3,
                "workflow": "semantic" if args.provider == "local" else "draft",
            },
        )
    report = {
        "python": platform.python_version(),
        "unicode": unicodedata.unidata_version,
        "index_manifest_sha256": hashlib.sha256(Path(args.index).read_bytes()).hexdigest(),
        "provider": args.provider,
        "http_status": response.status_code,
        "result": response.json(),
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    assert response.status_code == 200, response.text
    print(response.status_code, report["result"]["status"])
