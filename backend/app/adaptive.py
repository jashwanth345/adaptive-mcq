"""Candidate performance index, not a calibrated probability of knowledge."""

from collections import defaultdict
from dataclasses import asdict, dataclass

from fastapi import APIRouter, Request
from sqlalchemy import text

from .attempts import checked
from .student.routes import Student

LEVELS = ("easy", "medium", "hard")


@dataclass(frozen=True)
class Policy:
    version: str = "bounded-performance-v1"
    prior_correct: float = 1.0
    prior_incorrect: float = 1.0
    decay: float = 0.95
    minimum_evidence: int = 3
    recent_window: int = 3
    promote_at: float = 0.75
    demote_at: float = 0.4
    weights: tuple = (1, 2, 3)
    lookback_limit: int = 5000

    def __post_init__(self):
        if not (
            0 < self.decay <= 1
            and 0 <= self.demote_at < self.promote_at <= 1
            and self.minimum_evidence >= 1
            and self.recent_window >= 1
            and self.prior_correct > 0
            and self.prior_incorrect > 0
            and len(self.weights) == 3
            and all(w > 0 for w in self.weights)
        ):
            raise ValueError("Invalid adaptive policy")


def level_estimate(events, level, policy):
    matching = [(index, e) for index, e in enumerate(events) if e["difficulty"] == level]
    weighted = [
        (policy.decay ** (len(events) - 1 - index), int(e["is_correct"])) for index, e in matching
    ]
    p = (policy.prior_correct + sum(w * y for w, y in weighted)) / (
        policy.prior_correct + policy.prior_incorrect + sum(w for w, _ in weighted)
    )
    return p, len(matching), [e["is_correct"] for _, e in matching[-policy.recent_window :]]


DEFAULT_POLICY = Policy()


def profiles(evidence, preferred="easy", policy=DEFAULT_POLICY):
    groups = defaultdict(list)
    seen = set()
    for e in evidence:
        if e["version_id"] not in seen:
            groups[e["topic_id"]].append(e)
            seen.add(e["version_id"])
    result = []
    for topic, events in groups.items():
        current = preferred if preferred in LEVELS else "easy"
        reason = "More evidence needed at the current level."
        stats = {
            level: {"correct": 0.0, "total": 0.0, "count": 0, "recent": []} for level in LEVELS
        }
        for event in events:
            for value in stats.values():
                value["correct"] *= policy.decay
                value["total"] *= policy.decay
            value = stats[event["difficulty"]]
            value["total"] += 1
            value["correct"] += int(event["is_correct"])
            value["count"] += 1
            value["recent"] = (value["recent"] + [event["is_correct"]])[-policy.recent_window :]
            if event["difficulty"] != current:
                continue
            p = (policy.prior_correct + value["correct"]) / (
                policy.prior_correct + policy.prior_incorrect + value["total"]
            )
            recent = value["recent"]
            old = LEVELS.index(current)
            if value["count"] >= policy.minimum_evidence and len(recent) >= policy.recent_window:
                if p >= policy.promote_at and all(recent):
                    current = LEVELS[min(2, old + 1)]
                    reason = "Stable correct responses support one level higher."
                elif (
                    p <= policy.demote_at
                    and sum(not x for x in recent) >= (policy.recent_window + 1) // 2
                ):
                    current = LEVELS[max(0, old - 1)]
                    reason = "Recent difficulty supports one level lower."
                else:
                    reason = "Keep this level while collecting more evidence."
        levels = []
        numerator = denominator = 0.0
        for level, weight in zip(LEVELS, policy.weights, strict=True):
            value = stats[level]
            p = (policy.prior_correct + value["correct"]) / (
                policy.prior_correct + policy.prior_incorrect + value["total"]
            )
            covered = value["count"] >= policy.minimum_evidence
            levels.append(
                dict(
                    difficulty=level,
                    observations=value["count"],
                    covered=covered,
                    estimate=round(p, 4) if covered else None,
                )
            )
            if covered:
                numerator += weight * p
                denominator += weight
        result.append(
            dict(
                topic_id=topic,
                topic=events[-1]["topic"],
                observations=len(events),
                performance_index=round(100 * numerator / denominator, 1) if denominator else None,
                recommended_difficulty=current,
                reason=reason,
                levels=levels,
            )
        )
    return sorted(result, key=lambda x: (x["topic"].lower(), x["topic_id"]))


def learning_view(data, policy=DEFAULT_POLICY):
    rows = profiles(data["evidence"], data["preferred_difficulty"], policy)
    by_topic = {r["topic_id"]: r for r in rows}

    def rank(item):
        profile = by_topic.get(item["topic_id"])
        desired = profile["recommended_difficulty"] if profile else data["preferred_difficulty"]
        index = profile["performance_index"] if profile else None
        # Cold-start/under-covered topics first, then weaker sufficiently observed topics.
        return (
            index is not None,
            index or 0,
            profile["observations"] if profile else 0,
            abs(LEVELS.index(item["difficulty"]) - LEVELS.index(desired)),
            item["version_id"],
        )

    candidate = min(data["candidates"], key=rank) if data["candidates"] else None
    if candidate:
        candidate = dict(candidate)
        profile = by_topic.get(candidate["topic_id"])
        desired = profile["recommended_difficulty"] if profile else data["preferred_difficulty"]
        candidate["reason"] = "Unseen, automatically checked private question. " + (
            "Matches the recommended level."
            if candidate["difficulty"] == desired
            else "Nearest available level in this topic; the recommended level is unavailable."
        )
    return dict(
        policy=asdict(policy),
        policy_status="Candidate policy — thresholds to be evaluated",
        topics=rows,
        eligible_observations=len(data["evidence"]),
        retained_evidence_count=data["retained_evidence_count"],
        recommendation=candidate,
        candidate_count=len(data["candidates"]),
        scope="Latest 5000 eligible observations; up to 50 eligible unseen private candidates. Fixed classroom tests never adapt.",
    )


router = APIRouter(prefix="/api/v1/student", tags=["Adaptive learning"])


@router.get("/learning")
def learning(principal: Student, request: Request):
    with request.app.state.database.session() as session:
        data = session.execute(
            text("SELECT mcq.learning_data(:student)"), {"student": principal.user["id"]}
        ).scalar_one()
    return learning_view(checked(data))
