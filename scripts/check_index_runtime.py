"""Report runtime compatibility without rewriting or bypassing index validation."""

import argparse
import hashlib
import json
import platform
import unicodedata
from pathlib import Path

from ai_core.bm25_retrieval import load_index
from ai_core.data_contracts import ContractError

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manifests", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    rows = []
    for path in args.manifests:
        raw = path.read_bytes()
        manifest = json.loads(raw)
        payload = json.loads((path.parent / "index.json").read_bytes())
        row = {
            "path": str(path),
            "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "tokenizer": payload["tokenizer"],
            "source": payload["source"],
            "canonical_chunks_sha256": hashlib.sha256(
                json.dumps(payload["chunks"], sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest(),
        }
        try:
            index = load_index(path)
            row.update(
                status="COMPATIBLE",
                index_id=index.index_id,
                smoke_hit_count=len(index.search("bảo hiểm xã hội", 3)["results"]),
            )
        except ContractError as exc:
            row.update(status="INCOMPATIBLE", reason=str(exc))
        rows.append(row)
    with args.output.open("x", encoding="utf8") as f:
        json.dump(
            {"python": platform.python_version(), "unicode": unicodedata.unidata_version, "artifacts": rows},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print([(r["path"], r["status"]) for r in rows])
