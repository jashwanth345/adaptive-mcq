"""Run with: python -m evaluation --help. All outputs stay local."""

import argparse
import sys
from pathlib import Path

from backend.app.auth.security import AuthError

from .contracts import Config, Dataset
from .fixtures import smoke_inputs
from .replay import replay
from .reporting import review_pack, summarize
from .runner import run
from .storage import read_json, runner_lock, save_run, write_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "smoke", help="Isolated synthetic software check; no models or database"
    )
    template = sub.add_parser(
        "template", help="Save synthetic dataset/config templates for editing"
    )
    template.add_argument("directory", type=Path)
    execute = sub.add_parser("run", help="Execute a bounded matched experiment")
    execute.add_argument("dataset", type=Path)
    execute.add_argument("config", type=Path)
    execute.add_argument(
        "--allow-local-inference",
        action="store_true",
        help="Explicit operator opt-in after hardware validation; stop other AI jobs first",
    )
    pack = sub.add_parser(
        "review-pack",
        help="Create blinded items, private allocation map and annotation template",
    )
    pack.add_argument("run", type=Path)
    pack.add_argument("directory", type=Path)
    report = sub.add_parser(
        "report",
        help="Aggregate independently rated results with coverage and uncertainty",
    )
    report.add_argument("run", type=Path)
    report.add_argument("output", type=Path)
    report.add_argument("--mapping", type=Path)
    report.add_argument("--ratings", type=Path)
    policy = sub.add_parser(
        "replay", help="Compare adaptive/fixed decisions; never infer learning gains"
    )
    policy.add_argument("input", type=Path)
    policy.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "template":
            dataset, config = smoke_inputs()
            args.directory.mkdir(exist_ok=False, parents=True)
            write_json(args.directory / "dataset.json", dataset.model_dump())
            write_json(args.directory / "config.json", config.model_dump())
            print(
                "Synthetic templates saved. Replace with authorized material and record real retrieval provenance for research."
            )
        elif args.command in ("smoke", "run"):
            dataset, config = (
                smoke_inputs()
                if args.command == "smoke"
                else (
                    Dataset.model_validate(read_json(args.dataset)),
                    Config.model_validate(read_json(args.config)),
                )
            )
            with runner_lock():
                result = run(
                    dataset,
                    config,
                    allow_local=getattr(args, "allow_local_inference", False),
                )
                directory = save_run(result, summarize(result))
            print(result["evidence_status"])
            print(f"Saved {len(result['records'])} matched slots: {directory}")
        elif args.command == "review-pack":
            result = read_json(args.run)
            if not result.get("completed"):
                raise ValueError("The run is incomplete")
            blind, mapping, ratings = review_pack(result)
            args.directory.mkdir(exist_ok=False, parents=True)
            write_json(args.directory / "reviewer-items.json", blind)
            write_json(args.directory / "OPERATOR-ONLY-map.json", mapping)
            write_json(args.directory / "ratings-template.json", ratings)
            print(
                "Give reviewers only reviewer-items.json and ratings-template.json. Keep the allocation map private."
            )
        elif args.command == "report":
            result = summarize(
                read_json(args.run),
                read_json(args.mapping) if args.mapping else None,
                read_json(args.ratings) if args.ratings else None,
            )
            write_json(args.output, result)
            print(result["evidence_status"])
        else:
            write_json(args.output, replay(read_json(args.input)))
            print(
                "Saved observational policy replay. Learning outcomes: To be evaluated."
            )
    except AuthError as error:
        print(
            f"Evaluation stopped: {error.code}. No fallback or download was attempted.",
            file=sys.stderr,
        )
        return 1
    except (ValueError, OSError, KeyError, TypeError) as error:
        # No input files, tokens or model output are printed on failure.
        print(
            f"Evaluation stopped ({type(error).__name__}). Check the input contracts, output permissions and local readiness. Existing outputs are never overwritten.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
