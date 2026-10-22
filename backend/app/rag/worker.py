"""One CPU-only inference job. Exit releases model memory. Never downloads."""

import json
import os
import socket
import sys


def offline(*args, **kwargs):
    raise OSError("Embedding worker network access is disabled")


def run(texts, root):
    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    model = SentenceTransformer(
        str(root),
        device="cpu",
        local_files_only=True,
        trust_remote_code=False,
        model_kwargs={"use_safetensors": True},
    )
    if model.get_embedding_dimension() != 384:
        raise ValueError("Unexpected embedding dimension")
    model.eval()  # inference_mode alone does not disable dropout.
    tokenizer = model.tokenizer
    vectors, counts, windows_count = [], [], 0
    with torch.inference_mode():
        for value in texts:
            ids = tokenizer(value, add_special_tokens=False, truncation=False)["input_ids"]
            if not ids:
                raise ValueError("Empty token input")
            counts.append(len(ids))
            windows = []
            for start in range(0, len(ids), 192):
                windows.append(ids[start : start + 224])
                if start + 224 >= len(ids):
                    break
            encoded = []
            for start in range(0, len(windows), 4):
                # This snapshot is BERT-based: wrap exact window token IDs with
                # CLS/SEP, avoiding decode/re-tokenize changes to WordPiece tokens.
                sequences = [
                    [tokenizer.cls_token_id, *w, tokenizer.sep_token_id]
                    for w in windows[start : start + 4]
                ]
                width = max(map(len, sequences))
                batch = {
                    "input_ids": torch.tensor(
                        [s + [tokenizer.pad_token_id] * (width - len(s)) for s in sequences]
                    ),
                    "attention_mask": torch.tensor(
                        [[1] * len(s) + [0] * (width - len(s)) for s in sequences]
                    ),
                    "token_type_ids": torch.zeros((len(sequences), width), dtype=torch.long),
                }
                encoded.append(model(batch)["sentence_embedding"])
            windows_count += len(windows)
            vector = torch.cat(encoded).mean(dim=0)
            vector = torch.nn.functional.normalize(vector, dim=0)
            vectors.append(vector.tolist())
    return {"vectors": vectors, "token_counts": counts, "windows": windows_count}


if __name__ == "__main__":
    os.environ.update(
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        DO_NOT_TRACK="1",
        TOKENIZERS_PARALLELISM="false",
        OMP_NUM_THREADS="2",
        MKL_NUM_THREADS="2",
    )
    socket.socket.connect = offline
    socket.socket.connect_ex = offline
    socket.create_connection = offline
    from model_files import MODEL_DIR, verify_snapshot

    try:
        verify_snapshot()
        texts = json.loads(sys.stdin.buffer.read(4 * 1024 * 1024))
        if (
            not isinstance(texts, list)
            or not 1 <= len(texts) <= 500
            or any(not isinstance(t, str) or not t.strip() or len(t) > 5000 for t in texts)
        ):
            raise ValueError("Invalid embedding input")
        result = run(texts, MODEL_DIR)
    except Exception:
        result = {"error": "EMBEDDING_FAILED"}
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=True).encode("ascii"))
