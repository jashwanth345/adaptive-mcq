import re
import unicodedata

CORPUS_LIMIT = 2000
NEAR_THRESHOLD = 0.85


def normalize(stem):
    return " ".join(re.findall(r"\w+|[+*/=<>%\-]", unicodedata.normalize("NFKC", stem).casefold()))


def compare(stem, rows):
    target = normalize(stem)
    tokens = set(target.split())
    matches = []
    for row in rows[:CORPUS_LIMIT]:
        candidate = normalize(row["stem"])
        other = set(candidate.split())
        overlap = len(tokens & other) / max(1, len(tokens | other))
        if target == candidate or (min(len(tokens), len(other)) >= 4 and overlap >= NEAR_THRESHOLD):
            matches.append(
                {
                    "version_id": str(row["id"]),
                    "kind": "exact" if target == candidate else "near",
                    "similarity": round(overlap, 3),
                }
            )
    complete = len(rows) <= CORPUS_LIMIT
    return {
        "status": "fail" if matches else "pass" if complete else "incomplete",
        "complete": complete,
        "scanned": min(len(rows), CORPUS_LIMIT),
        "match_count": len(matches),
        "matches": matches[:10],
        "detail": "Normalized stems and token overlap only; semantic paraphrases may be missed. Similarity is a lexical measure, not a quality score.",
    }
