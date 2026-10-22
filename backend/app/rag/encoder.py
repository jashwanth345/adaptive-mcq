import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

from ..auth.security import AuthError
from ..hardware import snapshot
from .model_files import MODEL_NAME, REVISION, verify_snapshot


def fail(code, status=503):
    return AuthError(status, code, "Local retrieval is unavailable.")


def validate_vectors(vectors, expected):
    if not isinstance(vectors, list) or len(vectors) != expected:
        raise fail("EMBEDDING_FAILED")
    for vector in vectors:
        if (
            not isinstance(vector, list)
            or len(vector) != 384
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in vector)
            or not 0.999 <= math.sqrt(sum(v * v for v in vector)) <= 1.001
        ):
            raise fail("EMBEDDING_FAILED")
    return vectors


class LocalEncoder:
    model_name, revision = MODEL_NAME, REVISION

    def available(self):
        try:
            verify_snapshot(hashes=False)
            return (
                importlib.util.find_spec("sentence_transformers") is not None
                and importlib.util.find_spec("torch") is not None
            )
        except (OSError, ValueError, KeyError):
            return False

    def encode(self, texts):
        if not self.available():
            raise fail("EMBEDDING_NOT_INSTALLED")
        # The worker exits before the LLM starts. Never load Torch while the
        # student's machine is already under severe memory pressure.
        available = snapshot().get("available_ram_gib")
        if available is not None and available < 1.0:
            raise fail("EMBEDDING_LOW_MEMORY", 409)
        try:
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("worker.py"))],
                input=json.dumps(texts, ensure_ascii=True).encode("ascii"),
                capture_output=True,
                timeout=180,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            if result.returncode:
                raise fail("EMBEDDING_FAILED")
            data = json.loads(result.stdout)
            return validate_vectors(data.get("vectors"), len(texts))
        except subprocess.TimeoutExpired:
            raise fail("EMBEDDING_TIMEOUT") from None
        except (OSError, ValueError, TypeError):
            raise fail("EMBEDDING_FAILED") from None
