import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from uuid import uuid4

from sqlalchemy import text

from ..auth.security import AuthError
from .extract import MAX_BYTES, OCR_SPLITTER, SPLITTER, clean_text, text_chunks


def reject(code, status=422):
    return AuthError(status, code, "The PDF could not be processed.")


class MaterialService:
    def __init__(self, database, root: Path):
        self.database, self.root = database, root
        self.gate = Lock()

    def extract(self, path):
        # Both children are supervised directly; a timeout kills and reaps the
        # child before the private, temporary page images are removed.
        with TemporaryDirectory(prefix="mcq-ocr-", dir=self.root.resolve()) as temporary:
            arguments = [sys.executable, str(Path(__file__).with_name("extract.py")), str(path)]
            if sys.platform == "win32":
                arguments.append(temporary)
            data = self.run_worker(arguments, 30)
            scanned = data.get("scanned_pages", [])
            if scanned:
                powershell = (
                    Path(os.environ.get("SystemRoot", "C:/Windows"))
                    / "System32/WindowsPowerShell/v1.0/powershell.exe"
                )
                recognized = self.run_worker(
                    [
                        str(powershell),
                        "-NoProfile",
                        "-NonInteractive",
                        "-File",
                        str(Path(__file__).with_name("windows_ocr.ps1")),
                        temporary,
                    ],
                    45,
                    failure="PDF_OCR_UNAVAILABLE",
                )
                total = data.get("text_characters", 0)
                for number in scanned:
                    content = clean_text(recognized.get(f"{number:03d}", ""))
                    total += len(content)
                    if len(content) > 40000 or total > 200000:
                        raise reject("PDF_TEXT_LIMIT")
                    for chunk in text_chunks(content, number):
                        data["chunks"].append({**chunk, "splitter": OCR_SPLITTER})
                data["chunks"].sort(key=lambda chunk: chunk["page"])
                if not data["chunks"]:
                    raise reject("PDF_NO_TEXT")
            return data

    @staticmethod
    def run_worker(arguments, timeout, failure="INVALID_PDF"):
        try:
            result = subprocess.run(
                arguments,
                capture_output=True,
                stdin=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
        except subprocess.TimeoutExpired:
            raise reject("PDF_TIMEOUT", 422) from None
        if result.returncode:
            raise reject(failure)
        try:
            data = json.loads(result.stdout.decode("utf-8-sig"))
        except (ValueError, UnicodeError):
            raise reject(failure) from None
        if "error" in data:
            raise reject(data["error"])
        return data

    def store(self, owner, title, path, digest, size, data):
        # File exists first. A failed transaction removes it in the route; a hard
        # process crash can leave an unreferenced file (see operator recovery docs).
        with self.database.session() as session, session.begin():
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:owner,8))"),
                {"owner": str(owner)},
            )
            existing = session.execute(
                text("""
                SELECT m.id FROM mcq.materials m JOIN mcq.documents d ON d.material_id=m.id
                WHERE m.owner_id=:owner AND d.sha256=:hash AND NOT m.archived LIMIT 1
            """),
                {"owner": owner, "hash": digest},
            ).scalar_one_or_none()
            if existing:
                return {"id": existing, "reused": True}
            quota = session.execute(
                text(
                    "SELECT count(*),coalesce(sum(byte_size),0) FROM mcq.documents WHERE owner_id=:owner"
                ),
                {"owner": owner},
            ).one()
            if quota[0] >= 50 or quota[1] + size > 100 * 1024 * 1024:
                raise reject("MATERIAL_QUOTA", 409)
            material = session.execute(
                text(
                    "INSERT INTO mcq.materials(owner_id,title) VALUES(:owner,:title) RETURNING id"
                ),
                {"owner": owner, "title": title},
            ).scalar_one()
            document = session.execute(
                text("""
                INSERT INTO mcq.documents(material_id,owner_id,version,storage_key,sha256,byte_size,page_count)
                VALUES(:material,:owner,1,:key,:hash,:size,:pages) RETURNING id
            """),
                {
                    "material": material,
                    "owner": owner,
                    "key": path.name,
                    "hash": digest,
                    "size": size,
                    "pages": data["page_count"],
                },
            ).scalar_one()
            session.execute(
                text("""
                INSERT INTO mcq.chunks(document_id,owner_id,ordinal,page_start,page_end,content,content_sha256,token_count,splitter_version)
                VALUES(:document,:owner,:ordinal,:page,:page,:content,:hash,:tokens,:splitter)
            """),
                [
                    {
                        **chunk,
                        "document": document,
                        "owner": owner,
                        "ordinal": n,
                        "splitter": chunk.get("splitter", SPLITTER),
                    }
                    for n, chunk in enumerate(data["chunks"])
                ],
            )
            session.execute(
                text(
                    "INSERT INTO mcq.audit_events(actor_id,event_type,entity_type,entity_id) VALUES(:owner,'material.processed','material',:material)"
                ),
                {"owner": owner, "material": material},
            )
            return {"id": material, "reused": False}

    def listing(self, owner, offset, limit):
        with self.database.session() as session:
            rows = (
                session.execute(
                    text("""
                SELECT m.id,m.title,m.created_at,d.page_count,d.byte_size,
                (SELECT count(*) FROM mcq.chunks c WHERE c.document_id=d.id) AS chunk_count
                FROM mcq.materials m JOIN mcq.documents d ON d.material_id=m.id
                WHERE m.owner_id=:owner AND NOT m.archived AND d.version=1
                ORDER BY m.created_at DESC,m.id DESC LIMIT :limit OFFSET :offset
            """),
                    {"owner": owner, "limit": limit, "offset": offset},
                )
                .mappings()
                .all()
            )
            count = session.execute(
                text(
                    "SELECT count(*) FROM mcq.materials m WHERE owner_id=:owner AND NOT archived AND EXISTS(SELECT 1 FROM mcq.documents d WHERE d.material_id=m.id AND d.version=1)"
                ),
                {"owner": owner},
            ).scalar_one()
            return {
                "items": [dict(row) for row in rows],
                "total": count,
                "offset": offset,
                "limit": limit,
            }

    def preview(self, owner, material, page):
        with self.database.session() as session:
            row = (
                session.execute(
                    text("""
                SELECT m.id,m.title,m.created_at,d.id AS document,d.page_count,d.byte_size,
                (SELECT count(*) FROM mcq.chunks c WHERE c.document_id=d.id) AS chunk_count
                FROM mcq.materials m JOIN mcq.documents d ON d.material_id=m.id
                WHERE m.id=:material AND m.owner_id=:owner AND NOT m.archived AND d.version=1
            """),
                    {"owner": owner, "material": material},
                )
                .mappings()
                .one_or_none()
            )
            if row is None or page > row["page_count"]:
                raise reject("MATERIAL_NOT_FOUND", 404)
            chunks = (
                session.execute(
                    text(
                        "SELECT ordinal,content FROM mcq.chunks WHERE document_id=:doc AND owner_id=:owner AND page_start=:page ORDER BY ordinal"
                    ),
                    {"doc": row["document"], "owner": owner, "page": page},
                )
                .mappings()
                .all()
            )
            pages = set(
                session.execute(
                    text(
                        "SELECT DISTINCT page_start FROM mcq.chunks WHERE document_id=:doc AND owner_id=:owner"
                    ),
                    {"doc": row["document"], "owner": owner},
                ).scalars()
            )
            return {
                **row,
                "page": page,
                "chunks": [dict(c) for c in chunks],
                "empty_pages": [p for p in range(1, row["page_count"] + 1) if p not in pages],
                "ocr_pages": list(
                    session.execute(
                        text(
                            "SELECT DISTINCT page_start FROM mcq.chunks WHERE document_id=:doc AND owner_id=:owner AND splitter_version=:splitter ORDER BY page_start"
                        ),
                        {"doc": row["document"], "owner": owner, "splitter": OCR_SPLITTER},
                    ).scalars()
                ),
            }

    def new_path(self):
        self.root.mkdir(parents=True, exist_ok=True)
        # Refuse a redirected upload directory. Filenames never come from clients.
        if self.root.is_symlink() or self.root.resolve() != self.root.absolute():
            raise reject("UPLOAD_STORAGE_UNAVAILABLE", 503)
        return self.root / f"{uuid4().hex}.pdf"


def file_digest(path):
    with path.open("rb") as file:
        if file.read(5) != b"%PDF-":
            raise reject("INVALID_PDF")
        file.seek(0)
        return sha256(file.read(MAX_BYTES + 1)).hexdigest()
