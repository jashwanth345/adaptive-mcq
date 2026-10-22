import pytest

from backend.app.adaptive import Policy, learning_view, profiles


def evidence(answers, level="easy", topic="t"):
    return [
        dict(
            topic_id=topic,
            topic="DBMS",
            difficulty=level,
            is_correct=value,
            version_id=f"{topic}-{level}-{i}",
        )
        for i, value in enumerate(answers)
    ]


def test_insufficient_evidence_is_not_a_fabricated_percentage():
    assert profiles([]) == []
    result = profiles(evidence([True, False]))[0]
    assert result["observations"] == 2 and result["performance_index"] is None
    assert all(x["estimate"] is None for x in result["levels"])


def test_promotion_demotion_and_replay_are_bounded_and_deterministic():
    source = evidence([True] * 3)
    result = profiles(source)[0]
    assert result["recommended_difficulty"] == "medium"
    assert result["performance_index"] == pytest.approx(79.4, abs=0.05)
    assert profiles(source) == profiles(source + source)
    assert (
        profiles(evidence([False] * 3, "hard"), preferred="hard")[0]["recommended_difficulty"]
        == "medium"
    )
    assert profiles(evidence([True] * 20))[0]["recommended_difficulty"] == "medium"


def test_only_covered_difficulty_contributes_and_time_does_not_penalize():
    source = evidence([True] * 3) + evidence([False], "hard")
    row = profiles(source)[0]
    assert [x["covered"] for x in row["levels"]] == [True, False, False]
    assert profiles([{**e, "response_ms": 9999999} for e in source]) == profiles(source)


def test_no_bank_means_no_unverified_recommendation_and_nearest_level_is_explained():
    data = dict(
        evidence=evidence([True] * 3),
        preferred_difficulty="easy",
        candidates=[],
        retained_evidence_count=3,
    )
    assert learning_view(data)["recommendation"] is None
    data["candidates"] = [dict(version_id="z", topic_id="t", topic="DBMS", difficulty="hard")]
    assert "Nearest available" in learning_view(data)["recommendation"]["reason"]


def test_invalid_policy_is_rejected():
    for values in [
        dict(decay=0),
        dict(promote_at=0.2, demote_at=0.4),
        dict(weights=(1, 0, 3)),
        dict(minimum_evidence=0),
    ]:
        with pytest.raises(ValueError):
            Policy(**values)
