"""Pinned local embedding snapshot; no downloads from request-handling code."""

import hashlib
import json
from pathlib import Path

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
COMMIT = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
PIPELINE = "token224-stride192-mean-l2-v1"
REVISION = COMMIT + ":" + PIPELINE
MODEL_DIR = Path(__file__).resolve().parents[3] / "models" / "all-MiniLM-L6-v2"
FILES = (
    "1_Pooling/config.json",
    "README.md",
    "config.json",
    "config_sentence_transformers.json",
    "model.safetensors",
    "modules.json",
    "sentence_bert_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_snapshot(root=MODEL_DIR, *, hashes=True):
    manifest = json.loads((root / "snapshot.json").read_text(encoding="utf-8"))
    if (
        manifest["model"] != MODEL_NAME
        or manifest["commit"] != COMMIT
        or set(manifest["files"]) != set(FILES)
    ):
        raise ValueError("Invalid embedding snapshot")
    for name in FILES:
        path = root / name
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Incomplete embedding snapshot")
        if hashes and digest(path) != manifest["files"][name]:
            raise ValueError("Corrupt embedding snapshot")
    return manifest
