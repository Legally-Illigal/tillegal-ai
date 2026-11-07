"""Restore the pinned Python 3.12 corpus artifact and verify local pilot prerequisites."""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlopen

from ai_core.bm25_retrieval import TOKENIZER, load_index, term_statistics
from ai_core.data_contracts import canonical_json

INDEX = Path("data/indexes/labor-pilot-3-t4-bm25")
FILES = {
    "manifest.json": "133e58271b534fb59e437b0bc5066b50e9b61d4f86dd3cc3ad0e8896c7674f66",
    "index.json": "075333b67502eca35f1450befed3583b7f0c7e178231904511388cf6eeaa59ef",
}
MODEL = Path("data/models/qwen.gguf")
PUBLIC_SOURCE = ("https://raw.githubusercontent.com/lynkvu2901/Tilligal/"
                 "825b579cd0d8652d6d07ac3bb17524688ff07b30/data/indexes/labor-pilot-3-t4-bm25/")
SOURCE_SHA = "0e2fbd8cc6457a42e34f0a5b3129010af57b6a55bbe59f223a6c6586ed7e16c1"
MODEL_SHA = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"
MODEL_URL = ("https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/"
             "91cad51170dc346986eccefdc2dd33a9da36ead9/qwen2.5-1.5b-instruct-q4_k_m.gguf")


def verify(path, expected):
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise ValueError(f"Checksum mismatch: {path}")


def rebuild_public(stage):
    with urlopen(PUBLIC_SOURCE + "index.json", timeout=60) as response:
        data = response.read(6796162)
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA:
        raise ValueError("Public pilot snapshot checksum mismatch")
    payload = json.loads(data)
    payload["tokenizer"] = TOKENIZER
    payload["statistics"] = term_statistics(payload["chunks"])
    target = canonical_json(payload) + b"\n"
    (stage / "index.json").write_bytes(target)
    verify(stage / "index.json", FILES["index.json"])
    # Use the reviewed 3.12 manifest without machine-specific input paths.
    template = Path(__file__).with_name("pilot_manifest.json")
    shutil.copyfile(template, stage / "manifest.json")
    load_index(stage / "manifest.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-zip", type=Path)
    parser.add_argument("--download-model", action="store_true")
    parser.add_argument("--model", type=Path, default=MODEL)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        parser.error("Use Python 3.12 for this pilot artifact")
    if not INDEX.exists():
        INDEX.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=INDEX.parent) as tmp:
            stage = Path(tmp) / "index"
            stage.mkdir()
            if args.index_zip:
                with zipfile.ZipFile(args.index_zip) as archive:
                    for name, expected in FILES.items():
                        with archive.open(name) as source, (stage / name).open("xb") as dest:
                            shutil.copyfileobj(source, dest)
                        verify(stage / name, expected)
            else:
                rebuild_public(stage)
            stage.rename(INDEX)
    for name, expected in FILES.items():
        if name == "manifest.json" and (INDEX / name).read_bytes() == Path(__file__).with_name("pilot_manifest.json").read_bytes():
            continue
        verify(INDEX / name, expected)
    load_index(INDEX / "manifest.json")
    if args.download_model and not args.model.exists():
        args.model.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=args.model.parent) as tmp:
            part = Path(tmp) / "download"
            with urlopen(MODEL_URL, timeout=60) as src, part.open("xb") as dest:
                shutil.copyfileobj(src, dest)
            verify(part, MODEL_SHA)
            part.rename(args.model)
    verify(args.model, MODEL_SHA)
    print("BM25 loaded; model and index checksums verified")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        sys.exit(f"Pilot setup failed: {exc}. Check network, paths and SHA256. "
                 "Use --download-model to obtain missing weights or --index-zip for offline restore.")
