"""Test-only SQL bridge for reusing synthetic classroom fixtures on native PostgreSQL."""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

import psycopg
import pymupdf
from argon2 import PasswordHasher
from psycopg.rows import dict_row

from deployment.native import connect, credentials


def main():
    name = os.environ["MCQ_NATIVE_TEST_DATABASE"]
    if not re.fullmatch(r"mcq_acceptance_[a-f0-9]+", name):
        raise SystemExit("Synthetic seeding requires an acceptance database.")
    root = Path(os.environ["MCQ_TEST_UPLOADS"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with connect(credentials(), name, owner=True) as conn:
        conn.autocommit = True
        conn.row_factory = dict_row
        for line in sys.stdin:
            item = json.loads(line)
            try:
                if item.get("op") == "pdf":
                    key = item["document"].replace("-", "") + ".pdf"
                    with pymupdf.open() as pdf:
                        page = pdf.new_page()
                        page.insert_text(
                            (72, 72),
                            "Normalization reduces redundant data. Synthetic source for software tests.",
                        )
                        content = pdf.tobytes()
                    (root / key).write_bytes(content)
                    result = {
                        "key": key,
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "size": len(content),
                    }
                elif item.get("op") == "teacher":
                    hashed = PasswordHasher(
                        memory_cost=19456, time_cost=2, parallelism=1
                    ).hash("Fixture teacher 42!")
                    with conn.transaction():
                        teacher = conn.execute(
                            "INSERT INTO mcq.users(email,display_name,password_hash) VALUES('teacher.fixture@example.com','Review Teacher',%s) RETURNING id",
                            (hashed,),
                        ).fetchone()["id"]
                        conn.execute(
                            "INSERT INTO mcq.user_roles(user_id,role) VALUES(%s,'teacher')",
                            (teacher,),
                        )
                    result = {"teacher": teacher, "hash": hashed}
                else:
                    params = item.get("params", [])
                    ordered = []

                    def parameter(match, ordered=ordered, params=params):
                        ordered.append(params[int(match.group(1)) - 1])
                        return "%s"

                    statement = re.sub(
                        r"\$(\d+)", parameter, item["sql"].replace("%", "%%")
                    )
                    cursor = conn.execute(statement, ordered or None)
                    result = {"rows": cursor.fetchall() if cursor.description else []}
                print(
                    json.dumps({"id": item["id"], "result": result}, default=str),
                    flush=True,
                )
            except (OSError, ValueError, KeyError, psycopg.Error) as exc:
                print(
                    json.dumps({"id": item["id"], "error": type(exc).__name__}),
                    flush=True,
                )


if __name__ == "__main__":
    main()
