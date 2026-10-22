"""Public synthetic smoke inputs; never a measured research dataset."""

from .contracts import Config, Dataset, digest


def smoke_inputs():
    passages = [
        (
            "concept",
            "Normalization reduces redundant data. Replication copies data to another location.",
            "conceptual",
        ),
        (
            "math",
            "To add two integers, combine their values. The sum of 2 and 3 is 5.",
            "numerical",
        ),
    ]
    docs, cases = [], []
    for name, text, kind in passages:
        docs.append(
            {
                "id": name,
                "revision": "synthetic-v1",
                "split": "development",
                "text": text,
                "sha256": digest(text),
            }
        )
        cases.append(
            {
                "id": name,
                "document_id": name,
                "topic": "Synthetic " + name,
                "question_type": kind,
                "contexts": [
                    {"id": name + "-chunk", "text": text, "sha256": digest(text)}
                ],
                "retrieval": "synthetic",
                "embedding_model": "no-embedding-run",
                "embedding_revision": "synthetic-v1",
            }
        )
    data = Dataset(
        name="Synthetic smoke dataset — not research evidence",
        synthetic=True,
        authorized_material=True,
        documents=docs,
        cases=cases,
    )
    config = Config(
        pairs=[
            {
                "id": "fixture",
                "generator": "synthetic-generator",
                "verifier": "synthetic-verifier",
            }
        ],
        seeds=[42, 43],
    )
    return data, config
