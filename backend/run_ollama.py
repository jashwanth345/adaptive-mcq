"""Explicit local-only, CPU-only Ollama launcher. No model downloads here."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def environment():
    models = ROOT / "models" / "ollama"
    models.mkdir(parents=True, exist_ok=True)
    return {
        **os.environ,
        "OLLAMA_HOST": "127.0.0.1:11434",
        "OLLAMA_NO_CLOUD": "1",
        "OLLAMA_MODELS": str(models),
        "OLLAMA_NUM_PARALLEL": "1",
        "OLLAMA_MAX_LOADED_MODELS": "1",
        "OLLAMA_CONTEXT_LENGTH": "2048",
        "OLLAMA_KEEP_ALIVE": "0",
        "OLLAMA_MAX_QUEUE": "1",
        "CUDA_VISIBLE_DEVICES": "-1",
        "ROCR_VISIBLE_DEVICES": "-1",
        "GGML_VK_VISIBLE_DEVICES": "-1",
        "OLLAMA_VULKAN": "0",
        "OLLAMA_ORIGINS": "http://127.0.0.1:8000",
    }


def executable():
    path = ROOT / "tools" / "ollama" / "ollama.exe"
    if not path.is_file():
        raise SystemExit("Prepare the official portable Ollama runtime under tools/ollama first.")
    return path


if __name__ == "__main__":
    raise SystemExit(
        subprocess.call(
            [str(executable()), "serve"],
            env=environment(),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    )
