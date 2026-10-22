# Phase 10 hardware record — 7 October 2026

**Hardware-validated model selection: pending. No generator/verifier LLM inference was run.**

The user explicitly requested lightweight website development and a separated mock/test generator if local inference could not run comfortably. Development proceeds in `GENERATOR_MODE=mock`; no model-weight download or inference benchmark is required to demonstrate the draft workflow.

| Item | Evidence |
|---|---|
| Laptop | User-reported Dell Inspiron 14 3000 |
| CPU | Read-only local snapshot: Intel Core i5-1035G1 @ 1.00 GHz; 8 logical CPUs |
| Operating system | Read-only local snapshot: Windows 11, build 26300 |
| Usable physical RAM | 7.77 GiB |
| Available physical RAM | Initial snapshot 0.93 GiB; later snapshot 0.63 GiB (91% memory load). These are individual readings, not a benchmark or constant capacity. |
| GPU | User-reported Intel UHD integrated graphics, no dedicated GPU/VRAM |
| Shared GPU memory | User-reported up to 3.9 GB; drawn from system RAM, not additional capacity |
| Free workspace-drive storage | 55.85 GiB initially; 54.35 GiB after runtime preparation |

The default test workflow avoids both local LLM inference and embedding inference. It still exercises real authentication, PDF extraction, owned source selection, database writes, APIs and navigation. Existing semantic RAG is separately available and was tested in Phase 9; Phase 10 uses synthetic vectors where needed to check its integration without loading the embedding model.

The smallest current adapter candidate is **Qwen2.5 0.5B Instruct Q4_K_M**, approximately 398 MB in the published Ollama listing. This is a future candidate, not an installed or recommended-for-production model. Even a small weight file needs additional runtime/context/system memory. A 1.5 GiB free-RAM gate is a precaution, not proof of performance. Larger checkpoints are not selected. No simultaneous dual-model design is used.

Before the user's updated instruction arrived, the official Ollama v0.40.0 portable Windows runtime archive had finished downloading (1,468,064,949 bytes). Its release SHA-256 was verified as `3623e256762ca89bd6fa99b0cc4106401919ce9df926411673e632e3ea287bb5`. CPU runtime files were extracted under `tools/ollama/`, excluding CUDA/Vulkan/ROCm directories. This is a runtime package, not model weights. It has not been started. The archive remains in the task's `work/` directory, outside the application deliverables.

Small tokenizer files were prepared under `models/qwen2.5-tokenizer/` at revision `7ae557604adf67be50417f59c2c2f167def9a775`, with per-file hashes. They support lightweight token-budget tests; they are not LLM weights. No generator/verifier model is installed by this phase. The existing MiniLM embedding snapshot is retained from Phase 9.

## Deferred evidence

Actual LLM peak RAM, successful runtime startup, load time, tokens/second, generation latency, unload behavior, tokenizer parity with Ollama, factual correctness, distractor quality and independent-verifier performance: **To be evaluated**. No accuracy percentage, GPU capability or benchmark result is inferred from mock tests.

Future inference evaluation requires a fresh memory/storage check, an explicit decision to prepare the small model, serialized CPU execution and measurements with the website/database running. Larger models or a second model require a separate hardware review. Until then, mock mode keeps the project demonstrable without API credits, cloud accounts or payment.
