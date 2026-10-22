"""Independent human labels, explicit denominators and document-cluster uncertainty."""

import itertools
import math
import random
import statistics
from collections import Counter, defaultdict
from typing import Literal
from uuid import uuid4

from pydantic import Field

from .contracts import Strict, digest

FIELDS = (
    "valid",
    "factual_correctness",
    "answerability",
    "grounding",
    "relevance",
    "distractors",
    "complexity",
    "difficulty",
    "duplicate",
)


class Rating(Strict):
    blind_id: str
    reviewer: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    stage: Literal["independent", "adjudication"] = "independent"
    valid: bool | None = None
    factual_correctness: bool | None = None
    answerability: bool | None = None
    grounding: bool | None = None
    relevance: int | None = Field(default=None, ge=1, le=3)
    distractors: int | None = Field(default=None, ge=1, le=3)
    complexity: int | None = Field(default=None, ge=1, le=3)
    difficulty: Literal["easy", "medium", "hard"] | None = None
    duplicate: bool | None = None
    review_seconds: float | None = Field(
        default=None, ge=0, le=86400, allow_inf_nan=False
    )


def review_pack(run):
    records = {r["candidate_id"]: r for r in run["records"] if r["question"]}
    documents = {d["id"]: d for d in run["dataset"]["documents"]}
    mapping, items = {}, []
    for key, row in records.items():
        blind = str(uuid4())
        mapping[blind] = key
        items.append(
            {
                "blind_id": blind,
                "question": row["question"],
                "reference_text": documents[row["document_id"]]["text"],
                "requested_difficulty": row["requested_difficulty"],
                "requested_type": row["question_type"],
                "requested_cognitive_level": row["cognitive_level"],
            }
        )
    random.SystemRandom().shuffle(items)
    sha = digest(run)
    return (
        {
            "format": "blind-review-pack-v1",
            "run_sha256": sha,
            "evidence_status": run["evidence_status"],
            "items": items,
        },
        {"run_sha256": sha, "blind_to_candidate": mapping},
        {
            "run_sha256": sha,
            "ratings": [
                {
                    "blind_id": item["blind_id"],
                    "reviewer": "reviewer-1",
                    "stage": "independent",
                    **{k: None for k in FIELDS},
                    "review_seconds": None,
                }
                for item in items
            ],
        },
    )


def labels_for(run, mapping=None, annotations=None):
    if mapping is None and annotations is None:
        return {}, {"independent_ratings": 0, "adjudications": 0, "agreement": []}
    if (
        not mapping
        or not annotations
        or mapping.get("run_sha256") != digest(run)
        or annotations.get("run_sha256") != digest(run)
    ):
        raise ValueError("Ratings/map must reference the exact unchanged run")
    candidate_ids = {r["candidate_id"] for r in run["records"] if r["question"]}
    lookup = mapping["blind_to_candidate"]
    if (
        len(set(lookup.values())) != len(lookup)
        or set(lookup.values()) != candidate_ids
    ):
        raise ValueError("Blind map must cover each generated candidate exactly once")
    if len(annotations["ratings"]) > 10000:
        raise ValueError("Too many annotations")
    ratings, seen, per_candidate = [], set(), defaultdict(list)
    for raw in annotations["ratings"]:
        rating = Rating.model_validate(raw)
        key = (rating.blind_id, rating.reviewer, rating.stage)
        if rating.blind_id not in lookup or key in seen:
            raise ValueError("Unknown blind ID or duplicate reviewer rating")
        seen.add(key)
        ratings.append(rating)
        per_candidate[lookup[rating.blind_id]].append(rating)
    labels, pairwise = {}, defaultdict(list)
    for candidate, rows in per_candidate.items():
        independent = [r for r in rows if r.stage == "independent"]
        adjudications = [r for r in rows if r.stage == "adjudication"]
        if len(adjudications) > 1 or any(
            a.reviewer == r.reviewer for a in adjudications for r in independent
        ):
            raise ValueError("One separate adjudicator is permitted per candidate")
        if adjudications and len(independent) < 2:
            raise ValueError("Adjudication requires two independent ratings first")
        resolved = {}
        for field in FIELDS:
            values = [
                getattr(r, field) for r in independent if getattr(r, field) is not None
            ]
            final = getattr(adjudications[0], field) if adjudications else None
            resolved[field] = (
                final
                if final is not None
                else values[0]
                if len(values) >= 2 and len(set(values)) == 1
                else None
            )
        labels[candidate] = resolved
        for a, b in itertools.combinations(
            sorted(independent, key=lambda r: r.reviewer), 2
        ):
            if a.valid is not None and b.valid is not None:
                pairwise[(a.reviewer, b.reviewer)].append((a.valid, b.valid))
    agreement = []
    for pair, values in pairwise.items():
        n = len(values)
        observed = sum(a == b for a, b in values) / n
        pa, pb = sum(a for a, _ in values) / n, sum(b for _, b in values) / n
        expected = pa * pb + (1 - pa) * (1 - pb)
        agreement.append(
            {
                "reviewers": pair,
                "paired_items": n,
                "agreement": observed,
                "cohen_kappa": (observed - expected) / (1 - expected)
                if expected < 1
                else None,
            }
        )
    times = [r.review_seconds for r in ratings if r.review_seconds is not None]
    return labels, {
        "independent_ratings": sum(r.stage == "independent" for r in ratings),
        "adjudications": sum(r.stage == "adjudication" for r in ratings),
        "agreement": agreement,
        "review_time_seconds": sum(times) if times else None,
        "timed_ratings": len(times),
    }


def quantile(values, q):
    if not values:
        return None
    values = sorted(values)
    pos = (len(values) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def metric(values):
    """Values are (document_id, scalar). Cluster percentile bootstrap, fixed RNG."""
    groups = defaultdict(list)
    for doc, value in values:
        groups[doc].append(float(value))
    result = {
        "value": statistics.mean(v for _, v in values) if values else None,
        "rated_items": len(values),
        "source_documents": len(groups),
        "ci95": None,
        "status": "Evaluated" if values else "To be evaluated",
    }
    if len(groups) >= 2:
        rng, keys, samples = random.Random(19019), sorted(groups), []
        for _ in range(500):
            sample = [v for key in rng.choices(keys, k=len(keys)) for v in groups[key]]
            samples.append(statistics.mean(sample))
        result["ci95"] = [quantile(samples, 0.025), quantile(samples, 0.975)]
    return result


def summarize(run, mapping=None, annotations=None):
    if run.get("format") != "evaluation-run-v1" or not run.get("completed"):
        raise ValueError("Only completed evaluation runs can be summarized")
    labels, review = labels_for(run, mapping, annotations)
    synthetic = run["mode"] == "mock" or run["dataset"]["synthetic"]
    groups = defaultdict(list)
    for row in run["records"]:
        groups[(row["pair_id"], row["condition"])].append(row)
    summaries = []
    for (pair, condition), rows in sorted(groups.items()):
        generated = [r for r in rows if r["question"]]
        retained = [r for r in generated if r["retained"]]
        quality = {}
        for scope, subset in (("raw", generated), ("retained", retained)):
            quality[scope] = {}
            for field in FIELDS:
                values = []
                for row in subset:
                    value = labels.get(row["candidate_id"], {}).get(field)
                    if value is not None and not synthetic:
                        values.append(
                            (
                                row["document_id"],
                                value == row["requested_difficulty"]
                                if field == "difficulty"
                                else value,
                            )
                        )
                quality[scope][field] = {
                    **metric(values),
                    "eligible_items": len(subset),
                    "unrated_or_unresolved": len(subset) - len(values),
                }
        gold_invalid = [
            r
            for r in generated
            if labels.get(r["candidate_id"], {}).get("valid") is False
            and r["verifier_decision"] in ("PASS", "REJECT", "REGENERATE")
        ]
        gold_valid = [
            r
            for r in generated
            if labels.get(r["candidate_id"], {}).get("valid") is True
            and r["verifier_decision"] in ("PASS", "REJECT", "REGENERATE")
        ]
        signatures = [
            " ".join(r["question"]["stem"].casefold().split()) for r in generated
        ]
        timings = {
            stage: {
                "observations": sum(r[stage] is not None for r in rows),
                "p50_seconds": quantile(
                    [r[stage] for r in rows if r[stage] is not None], 0.5
                ),
                "p95_seconds": quantile(
                    [r[stage] for r in rows if r[stage] is not None], 0.95
                ),
            }
            for stage in (
                "generation_seconds",
                "verification_seconds",
                "math_seconds",
                "execution_seconds",
            )
        }
        summaries.append(
            {
                "pair_id": pair,
                "condition": condition,
                "requested_slots": len(rows),
                "generated_candidates": len(generated),
                "retained_candidates": len(retained),
                "retention_yield": len(retained) / len(generated)
                if generated
                else None,
                "end_to_end_yield": len(retained) / len(rows),
                "errors": dict(Counter(r["error"] for r in rows if r["error"])),
                "verifier_decisions": dict(
                    Counter(r["verifier_decision"] for r in rows)
                ),
                "math_statuses": dict(
                    Counter(r["math"]["status"] for r in rows if r["math"])
                ),
                "model_relationships": dict(
                    Counter(r["model_relationship"] for r in rows)
                ),
                "question_types": dict(Counter(r["question_type"] for r in generated)),
                "cognitive_levels": dict(
                    Counter(r["cognitive_level"] for r in generated)
                ),
                "exact_stem_repeats": len(signatures) - len(set(signatures)),
                "duplicate_denominator": len(generated),
                "quality": quality,
                "timing": timings,
                "verifier_false_acceptance": metric(
                    []
                    if synthetic
                    else [
                        (r["document_id"], r["verifier_decision"] == "PASS")
                        for r in gold_invalid
                    ]
                ),
                "verifier_false_rejection": metric(
                    []
                    if synthetic
                    else [
                        (r["document_id"], r["verifier_decision"] == "REJECT")
                        for r in gold_valid
                    ]
                ),
                "verifier_valid_not_passed": metric(
                    []
                    if synthetic
                    else [
                        (r["document_id"], r["verifier_decision"] != "PASS")
                        for r in gold_valid
                    ]
                ),
            }
        )
    return {
        "format": "evaluation-summary-v1",
        "run_id": run["id"],
        "run_sha256": digest(run),
        "evidence_status": run["evidence_status"],
        "research_results_available": not synthetic
        and any(value is not None for row in labels.values() for value in row.values()),
        "review": review,
        "groups": summaries,
        "uncertainty_method": "500 source-document cluster bootstrap replicates; percentile 95% interval; unavailable below two documents; exploratory for small samples",
        "timing_scope": "Serial execution after frozen retrieval; includes failed calls; excludes dataset preparation, queueing and retrieval. B generation is reused in C/D. Mock timing is software timing only.",
        "not_measured": [
            "retrieval latency",
            "queue latency",
            "peak full-stack memory",
            "paging incidents",
            "semantic duplicate calibration",
            "student satisfaction",
            "learning outcomes",
        ],
        "interpretation": "No confidence intervals or observed percentages alone establish causal gains. Pipeline comparisons are paired by source/case/seed; model pairs must be compared separately.",
    }
