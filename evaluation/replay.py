"""Observational replay compares decisions, never counterfactual learning outcomes."""

from collections import defaultdict
from dataclasses import asdict

from backend.app.adaptive import DEFAULT_POLICY, profiles

from .contracts import digest


def replay(bundle):
    if (
        bundle.get("format") != "adaptive-export-v1"
        or bundle.get("consent_confirmed") is not True
    ):
        raise ValueError("Use an authorized, consent-confirmed adaptive export")
    if not isinstance(bundle.get("events"), list) or len(bundle["events"]) > 10000:
        raise ValueError("Replay is limited to 10000 events")
    sequences = set()
    for row in bundle["events"]:
        if (
            not isinstance(row, dict)
            or type(row.get("sequence")) is not int
            or row["sequence"] < 1
            or row["sequence"] in sequences
            or any(
                not isinstance(row.get(key), str) or not 1 <= len(row[key]) <= 120
                for key in ("learner", "topic", "version")
            )
        ):
            raise ValueError("Invalid or duplicate event sequence/identity")
        sequences.add(row["sequence"])
    learners, seen, decisions = defaultdict(list), set(), []
    # Stable sequence numbers originate from the scoped database export. No wall-clock dates are needed.
    for row in sorted(bundle["events"], key=lambda e: e["sequence"]):
        if type(row.get("is_correct")) is not bool or row.get("difficulty") not in (
            "easy",
            "medium",
            "hard",
        ):
            raise ValueError("Invalid response event")
        key = (row["learner"], row["version"])
        if key in seen:
            raise ValueError("Duplicate first-exposure event")
        seen.add(key)
        history = learners[row["learner"]]
        before = {p["topic_id"]: p for p in profiles(history)}
        adaptive = before.get(row["topic"], {}).get("recommended_difficulty", "easy")
        decisions.append(
            {
                "sequence": row["sequence"],
                "learner": row["learner"],
                "topic": row["topic"],
                "fixed_difficulty": "easy",
                "adaptive_difficulty": adaptive,
                "observed_difficulty": row["difficulty"],
                "policies_disagree": adaptive != "easy",
            }
        )
        history.append(
            {
                "topic_id": row["topic"],
                "topic": row["topic"],
                "version_id": row["version"],
                "difficulty": row["difficulty"],
                "is_correct": row["is_correct"],
            }
        )
    return {
        "format": "adaptive-replay-v1",
        "input_sha256": digest(bundle),
        "policy": asdict(DEFAULT_POLICY),
        "learners": len(learners),
        "eligible_events": len(decisions),
        "decisions": decisions,
        "disagreements": sum(d["policies_disagree"] for d in decisions),
        "learning_gain": None,
        "status": "OFFLINE OBSERVATIONAL REPLAY — NOT A LEARNER EXPERIMENT",
        "limitations": "Uses only exported eligible events, with an easy cold-start prior. Missing history changes recommendations. Observed answers cannot be assigned to questions a different policy would have selected. No randomization, pre/post test, satisfaction measure or causal outcome is supplied.",
    }
