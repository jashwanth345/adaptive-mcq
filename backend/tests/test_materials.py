import subprocess
from hashlib import sha256

import pymupdf
import pytest
from sqlalchemy import text

from backend.app.auth.security import AuthError
from backend.app.materials.extract import MAX_BYTES, PdfRejected, clean_text, extract
from backend.app.materials.service import MaterialService
from backend.tests.test_student import integration, operator, students  # noqa: F401


def pdf_bytes(
    pages=("Database normalization preserves data integrity.", "Transactions provide atomicity."),
    encrypted=False,
):
    with pymupdf.open() as doc:
        for text_value in pages:
            page = doc.new_page()
            if text_value:
                page.insert_text((50, 60), text_value)
        return (
            doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret")
            if encrypted
            else doc.tobytes()
        )


def test_extraction_preserves_pages_and_hashes(tmp_path):
    path = tmp_path / "source.pdf"
    path.write_bytes(pdf_bytes(("Alpha\n" * 120, "", "<script>alert('untrusted')</script>")))
    result = extract(path)
    assert result["page_count"] == 3 and result["empty_pages"] == [2]
    assert {c["page"] for c in result["chunks"]} == {1, 3}
    for chunk in result["chunks"]:
        assert chunk["hash"] == sha256(chunk["content"].encode()).hexdigest()
        assert chunk["tokens"] >= 1 and len(chunk["content"]) <= 1200
    assert clean_text("one\x00\t two\r\nthree") == "one two\nthree"


@pytest.mark.parametrize(
    "kind,code",
    [
        ("invalid", "INVALID_PDF"),
        ("encrypted", "ENCRYPTED_PDF"),
        ("blank", "PDF_NO_TEXT"),
        ("long", "PDF_PAGE_LIMIT"),
    ],
)
def test_bad_pdfs_are_explicit(tmp_path, kind, code):
    content = {
        "invalid": lambda: b"not pdf",
        "encrypted": lambda: pdf_bytes(encrypted=True),
        "blank": lambda: pdf_bytes(("",)),
        "long": lambda: pdf_bytes(("text",) * 101),
    }[kind]()
    path = tmp_path / "source.pdf"
    path.write_bytes(content)
    with pytest.raises(PdfRejected, match=code):
        extract(path)


def test_extraction_timeout_and_crash_are_safe(monkeypatch, tmp_path):
    service = MaterialService(None, tmp_path)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("private-file-path", 30)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(AuthError) as error:
        service.extract(tmp_path / "private.pdf")
    assert error.value.code == "PDF_TIMEOUT"
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess([], 1, b"", b"private traceback"),
    )
    with pytest.raises(AuthError) as error:
        service.extract(tmp_path / "private.pdf")
    assert error.value.code == "INVALID_PDF"


@pytest.mark.integration
@integration
def test_pdf_library_privacy_duplicates_limits_and_failure_cleanup(request, tmp_path, monkeypatch):
    client, app, ids, tokens = request.getfixturevalue("students")
    service = app.state.materials
    service.root = tmp_path / "uploads"
    headers = {**tokens[0], "Content-Type": "application/pdf"}
    url = "/api/v1/materials"
    content = pdf_bytes(("Normalization source", "", "Transactions source"))
    assert (
        client.post(
            url + "?title=Private", content=content, headers={"Content-Type": "application/pdf"}
        ).status_code
        == 401
    )
    assert not service.root.exists()
    # Reject declared oversize after authentication, before allocating a file.
    response = client.post(
        url + "?title=Oversize",
        content=b"%PDF-",
        headers={**headers, "Content-Length": str(MAX_BYTES + 1)},
    )
    assert response.status_code == 413 and response.json()["error"]["code"] == "PDF_TOO_LARGE"
    assert not service.root.exists() and not service.gate.locked()
    # A dishonest length cannot leave a partial upload or a held processing slot.
    response = client.post(
        url + "?title=Mismatch", content=b"%PDF-", headers={**headers, "Content-Length": "1"}
    )
    assert (
        response.status_code == 400 and response.json()["error"]["code"] == "INVALID_CONTENT_LENGTH"
    )
    assert not list(service.root.glob("*.pdf")) and not service.gate.locked()
    # Chunked uploads have no declared length; the streamed-byte cap still applies.
    response = client.post(
        url + "?title=Streamed-oversize",
        content=iter([b"%PDF-", b"x" * MAX_BYTES]),
        headers=headers,
    )
    assert response.status_code == 413 and response.json()["error"]["code"] == "PDF_TOO_LARGE"
    assert not list(service.root.glob("*.pdf")) and not service.gate.locked()
    response = client.post(url + "?title=Private", content=content, headers=headers)
    assert response.status_code == 201, response.text
    mid = response.json()["id"]
    assert not response.json()["reused"]
    assert len(list(service.root.glob("*.pdf"))) == 1
    assert client.get(url, headers=tokens[0]).json()["total"] == 1
    assert client.get(url, headers=tokens[1]).json()["total"] == 0
    assert client.get(url + "/" + mid, headers=tokens[1]).status_code == 404
    preview = client.get(url + "/" + mid + "?page=3", headers=tokens[0])
    assert preview.status_code == 200, preview.text
    assert preview.headers["cache-control"] == "no-store"
    assert preview.json()["empty_pages"] == [2]
    assert preview.json()["chunks"][0]["content"] == "Transactions source"
    for private in ["storage_key", "owner_id", "document", "sha256"]:
        assert private not in preview.json()
    assert client.get(url + "/" + mid + "?page=4", headers=tokens[0]).status_code == 404
    duplicate = client.post(url + "?title=Renamed", content=content, headers=headers)
    assert duplicate.json() == {"id": mid, "reused": True}
    assert len(list(service.root.glob("*.pdf"))) == 1
    for body, mime, code, status in [
        (b"bad", "application/pdf", "INVALID_PDF", 422),
        (content, "text/plain", "PDF_REQUIRED", 415),
        (b"%PDF-" + b"x" * MAX_BYTES, "application/pdf", "PDF_TOO_LARGE", 413),
        (pdf_bytes(("",)), "application/pdf", "PDF_NO_TEXT", 422),
    ]:
        response = client.post(
            url + "?title=Failure", content=body, headers={**tokens[0], "Content-Type": mime}
        )
        assert response.status_code == status and response.json()["error"]["code"] == code, (
            response.text
        )
        assert len(list(service.root.glob("*.pdf"))) == 1
    service.gate.acquire()
    try:
        response = client.post(url + "?title=Busy", content=content, headers=headers)
        assert response.status_code == 409 and response.json()["error"]["code"] == "PDF_BUSY"
    finally:
        service.gate.release()
    assert client.post(url + "?title=%20", content=content, headers=headers).status_code == 422
    assert client.get(url + "?limit=25", headers=tokens[0]).status_code == 422
    # Teacher-only account uses the same private library contract.
    with operator(app.state.database), app.state.database.session() as session, session.begin():
        session.execute(
            text("INSERT INTO mcq.user_roles(user_id,role) VALUES(:id,'teacher')"), {"id": ids[1]}
        )
        session.execute(
            text("DELETE FROM mcq.user_roles WHERE user_id=:id AND role='student'"), {"id": ids[1]}
        )
    response = client.post(
        url + "?title=Teacher",
        content=content,
        headers={**tokens[1], "Content-Type": "application/pdf"},
    )
    assert response.status_code == 201 and response.json()["id"] != mid
    assert client.get(url + "/" + response.json()["id"], headers=tokens[0]).status_code == 404
    with app.state.database.session() as session:
        assert not session.execute(
            text("SELECT has_table_privilege(current_user,'mcq.documents','UPDATE,DELETE')")
        ).scalar_one()

    def fail(*args):
        raise AuthError(409, "MATERIAL_QUOTA", "Full")

    monkeypatch.setattr(service, "store", fail)
    response = client.post(url + "?title=Quota", content=content, headers=headers)
    assert response.status_code == 409
    assert len(list(service.root.glob("*.pdf"))) == 2
    assert not service.gate.locked()
