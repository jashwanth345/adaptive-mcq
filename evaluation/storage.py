"""Bounded local JSON, immutable run directories and safe CSV cells."""

import csv
import json
from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock, Timeout

from .contracts import digest

ROOT = Path(__file__).resolve().parent / "runs"


def read_json(path):
    path = Path(path)
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("Input exceeds 20 MiB")
    return json.loads(
        path.read_text(encoding="utf-8-sig"),
        parse_constant=lambda _: (_ for _ in ()).throw(
            ValueError("Nonfinite JSON is forbidden")
        ),
    )


def write_json(path, data):
    with Path(path).open("x", encoding="utf-8", newline="\n") as out:
        json.dump(data, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write("\n")


@contextmanager
def runner_lock():
    ROOT.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(str(ROOT / ".runner.lock"), timeout=0):
            yield
    except Timeout:
        raise ValueError("Another evaluation is running") from None


def save_run(run, summary):
    directory = ROOT / run["id"]
    directory.mkdir(exist_ok=False)
    write_json(directory / "run.json", run)
    write_json(directory / "summary.json", summary)
    with (directory / "records.csv").open("x", encoding="utf-8-sig", newline="") as out:
        fields = [
            "candidate_id",
            "pair_id",
            "case_id",
            "document_id",
            "seed",
            "condition",
            "question_type",
            "retained",
            "error",
            "verifier_decision",
            "generation_seconds",
            "verification_seconds",
            "math_seconds",
            "execution_seconds",
        ]
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for row in run["records"]:
            writer.writerow({key: safe_cell(row.get(key)) for key in fields})
    write_json(
        directory / "complete.json",
        {"run_sha256": digest(run), "summary_sha256": digest(summary)},
    )
    return directory


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value
