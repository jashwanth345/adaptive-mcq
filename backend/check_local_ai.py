"""Bounded real local inference check; no database writes or model downloads."""
import json
import time
from uuid import uuid4

from .app.auth.security import AuthError
from .app.config import PROJECT_ROOT, load_settings
from .app.generator.client import OllamaGenerator
from .app.generator.prompt import build_prompt
from .app.generator.schemas import GenerateRequest
from .app.hardware import snapshot
from .app.verifier.client import LocalVerifier


def main():
    report = {"hardware_before": snapshot(), "synthetic_source": True, "cloud_used": False}
    settings = load_settings()
    source = {"citation": "S1", "excerpt": "Retrieval-augmented generation retrieves relevant passages from a document before generating an answer. Embeddings represent text as numerical vectors. Semantic retrieval compares these vectors to find passages related to a query. Grounding connects an answer to supporting source material. A verifier checks the proposed answer against that material.", "clipped": False}
    payload = GenerateRequest(material_ids=[uuid4()], topic="Retrieval-augmented generation", idempotency_key=uuid4())
    started = time.monotonic()
    try:
        client = OllamaGenerator(settings)
        report["model"] = client.inspect()
        prompt, sources, tokens = build_prompt(payload, [source], settings.llm_context_tokens, settings.llm_output_tokens)
        result, metadata = client.generate(prompt, tokens)
        report["generation"] = result.model_dump()
        report["generation_metadata"] = metadata
        if result.question is not None:
            question = result.question.model_dump()
            report["exact_source_quote"] = question["evidence_quote"] in sources[0]["excerpt"]
            blind, critique, metadata = LocalVerifier(settings).review({**question, "source": sources[0], "difficulty": "easy"})
            report["verification"] = {"blind": blind.model_dump(), "critique": critique.model_dump(), "metadata": metadata}
        report["completed"] = True
    except AuthError as error:
        report.update(completed=False, error_code=error.code)
    report.update(seconds=round(time.monotonic()-started, 2), hardware_after=snapshot())
    path = PROJECT_ROOT / "logs/real-local-ai-check.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
