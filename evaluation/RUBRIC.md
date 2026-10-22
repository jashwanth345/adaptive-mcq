# Independent MCQ review rubric

Version 1, Phase 19. Calibrate on development material before freezing the protocol. Rate each blinded candidate against its reference text; do not consult verifier decisions or another rater. Use `null` when you cannot judge. Null is not a failure score. Do not claim that mock fixtures measure AI performance.

| Field | Rating anchors |
|---|---|
| `valid` | True only if usable as a single-correct assessment item: factual/key/explanation correct, one answer, clear wording, plausible distinct distractors, and aligned with requested topic. Otherwise false; unknown null. |
| `factual_correctness` | True if stem, key and explanation are factually correct; false for a demonstrable error. A quotation alone is insufficient. |
| `answerability` | True if exactly one offered option is correct and enough information is given. Independently solve numerical questions. False for no/multiple answers or missing necessary information. |
| `grounding` | True if reference material supports the question and explanation. False for unsupported claims; null if the source itself is inconclusive. Applies to A too as post-generation reference alignment. |
| `relevance` | 1: off-topic or trivial incidental detail; 2: broadly related but weak learning-objective alignment; 3: directly tests the requested topic/objective. |
| `distractors` | 1: obvious, duplicate, nonsensical or accidentally correct distractors; 2: some plausible alternatives with weaknesses; 3: distinct plausible misconceptions, each incorrect. |
| `complexity` | 1: direct recall; 2: interpretation/relationship or one-step application; 3: multi-step reasoning/integration. Higher is not inherently better; compare to the requested cognitive level. |
| `difficulty` | Easy: accessible recall/basic application; medium: understanding and nontrivial application; hard: demanding integration or several reasoning steps. Judge for the declared learner/course level, not rater expertise. |
| `duplicate` | True if substantially the same learning task as another item in the review pack, ignoring paraphrase/options order; false if distinct; null if comparison is uncertain. This is cross-pack similarity judgement, separate from within-condition exact-stem counting. Similar A/B outputs are expected paired-experiment overlap; do not interpret this label as a within-condition diversity rate. |
| `review_seconds` | Actual active review time, if recorded. Do not estimate retrospectively; null if absent. |

Use one unique pseudonymous reviewer ID per person. Two independent labels must agree per field for that field to resolve automatically. A third person can supply `stage: "adjudication"` only after at least two independent ratings; record the adjudication rationale in a separate private review log. Do not replace or delete original disagreements. No individual reviewer should serve as their own adjudicator.

Keep the run hash, blind IDs and operator allocation map unchanged. The operator merges ratings; reviewers receive the item pack, this rubric and blank rows, without the allocation map. Keep authorized source texts private if their license/permissions require it. Review IDs and raw ratings are research records; retain/export them according to the approved study plan.
