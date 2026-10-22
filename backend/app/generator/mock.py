"""Deterministic UI fixture. This is not an LLM or a quality evaluation."""

from .schemas import Candidate, Generated


def generate_mock(source):
    quote = source["excerpt"][:140].strip()
    if len(quote) < 5:
        return Generated(status="insufficient_evidence", question=None)
    placeholders = [f"Placeholder distractor {label} (test only)." for label in "BCD"]
    placeholders = [
        text + " Example." if text.lower() == quote.lower() else text for text in placeholders
    ]
    return Generated(
        status="draft",
        question=Candidate(
            stem="Test draft: which excerpt is copied from the selected study material?",
            options=[quote, *placeholders],
            correct_option=0,
            explanation="This deterministic test copies a source excerpt. The distractors are placeholders, not AI-generated educational content.",
            citation=source["citation"],
            evidence_quote=quote,
        ),
    )
