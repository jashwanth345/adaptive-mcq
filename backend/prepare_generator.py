"""One-time download of the public Qwen2.5 tokenizer; model weights use Ollama pull."""

import hashlib
import json
import urllib.request

from backend.app.generator.prompt import TOKENIZER_DIR, TOKENIZER_REVISION

if __name__ == "__main__":
    TOKENIZER_DIR.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in ("tokenizer.json", "tokenizer_config.json"):
        path = TOKENIZER_DIR / name
        url = (
            f"https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/resolve/{TOKENIZER_REVISION}/{name}"
        )
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read(12 * 1024 * 1024)
        path.write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    (TOKENIZER_DIR / "snapshot.json").write_text(
        json.dumps({"revision": TOKENIZER_REVISION, "files": hashes}, indent=2)
    )
    print("Local Qwen2.5 tokenizer prepared. No model weights or inference downloaded here.")
