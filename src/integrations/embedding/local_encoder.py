"""Persistent exact cosine retrieval. Model downloads are an explicit setup action."""

import unicodedata
from pathlib import Path

import numpy as np

from src.applications.tillegal.ingestion.data_contracts import ContractError

MODEL = "intfloat/multilingual-e5-small"


class LocalEncoder:
    def __init__(self, model_path, revision, batch_size=8):
        from importlib.metadata import version

        import torch
        from transformers import AutoModel, AutoTokenizer

        if type(batch_size) is not int or batch_size < 1 or not isinstance(revision, str) or not revision.strip():
            raise ContractError("Invalid batch size/revision")
        files = sorted(
            p
            for p in Path(model_path).iterdir()
            if p.is_file() and (p.suffix in {".json", ".safetensors", ".model", ".txt"})
        )
        if not any(p.suffix == ".safetensors" for p in files):
            raise ContractError("Expected local safetensors weights")
        from src.applications.tillegal.ingestion.data_contracts import canonical_json, content_hash, file_hash

        fingerprint = content_hash(canonical_json([(p.name, file_hash(p)) for p in files]).decode())
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
        self.model = AutoModel.from_pretrained(
            model_path, local_files_only=True, trust_remote_code=False, use_safetensors=True
        ).eval()
        self.batch_size = batch_size
        self.config = {
            "model": MODEL,
            "revision": revision,
            "dimension": 384,
            "max_tokens": 512,
            "pooling": "masked_mean_l2",
            "text_policy": "nfc_windows_480_overlap64_v1",
            "dtype": "float32",
            "device": "cpu",
            "snapshot_sha256": fingerprint,
            "libraries": {name: version(name) for name in ("torch", "transformers", "numpy")},
        }

    def windows(self, text):
        # Token offsets map back to NFC embedding text; canonical source stays untouched.
        text = unicodedata.normalize("NFC", text)
        offsets = self.tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
        if not offsets:
            return [(0, len(text), text)]
        windows = []
        for start in range(0, len(offsets), 416):
            end = min(start + 480, len(offsets))
            a, b = offsets[start][0], offsets[end - 1][1]
            windows.append((a, b, text[a:b]))
            if end == len(offsets):
                break
        return windows

    def encode(self, texts, kind):
        values = [kind + ": " + unicodedata.normalize("NFC", text) for text in texts]
        vectors = []
        for offset in range(0, len(values), self.batch_size):
            batch = self.tokenizer(
                values[offset : offset + self.batch_size], padding=True, truncation=False, return_tensors="pt"
            )
            if batch["input_ids"].shape[1] > 512:
                raise ContractError("ENCODER_TOKEN_LIMIT: query or window too long")
            with self.torch.inference_mode():
                hidden = self.model(**batch).last_hidden_state
                mask = batch["attention_mask"].unsqueeze(-1)
                pooled = (hidden * mask).sum(1) / mask.sum(1)
                vectors.append(self.torch.nn.functional.normalize(pooled, p=2, dim=1).cpu().numpy())
        return np.concatenate(vectors).astype("float32")
