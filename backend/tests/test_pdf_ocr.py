"""Bounded scanned-PDF processing; real OCR is exercised in the browser journey."""

import subprocess

import pymupdf
import pytest

from backend.app.auth.security import AuthError
from backend.app.materials.extract import OCR_SPLITTER, PdfRejected, extract
from backend.app.materials.service import MaterialService


def scanned_pdf(path, pages=1):
    with pymupdf.open() as source:
        page = source.new_page()
        page.insert_text((50, 80), "Database normalization preserves integrity.", fontsize=18)
        raster = page.get_pixmap().tobytes("png")
    with pymupdf.open() as document:
        for _ in range(pages):
            page = document.new_page()
            page.insert_image(page.rect, stream=raster)
        document.save(path)


def test_scan_raster_is_bounded_and_keeps_page_number(tmp_path):
    path = tmp_path / "scan.pdf"
    scanned_pdf(path)
    images = tmp_path / "images"
    images.mkdir()
    data = extract(path, images)
    assert data["scanned_pages"] == [1] and not data["chunks"]
    image = pymupdf.Pixmap(images / "001.png")
    assert max(image.width, image.height) <= 2000


def test_scan_page_limit_is_explicit(tmp_path):
    path = tmp_path / "scan.pdf"
    scanned_pdf(path, 11)
    with pytest.raises(PdfRejected, match="PDF_OCR_PAGE_LIMIT"):
        extract(path, tmp_path)


def test_ocr_merges_in_page_order_with_provenance_and_cleans_images(tmp_path, monkeypatch):
    service = MaterialService(None, tmp_path)
    responses = iter(
        [
            {
                "page_count": 2,
                "chunks": [{"page": 2, "content": "Typed source", "hash": "test", "tokens": 12}],
                "scanned_pages": [1],
                "text_characters": 12,
            },
            {"001": "Scanned source\x00\nwith a page reference"},
        ]
    )
    monkeypatch.setattr(service, "run_worker", lambda *args, **kwargs: next(responses))
    result = service.extract(tmp_path / "scan.pdf")
    assert [c["page"] for c in result["chunks"]] == [1, 2]
    assert result["chunks"][0]["splitter"] == OCR_SPLITTER
    assert "\x00" not in result["chunks"][0]["content"]
    assert not list(tmp_path.glob("mcq-ocr-*"))


@pytest.mark.parametrize(
    "recognized,code",
    [
        ({"001": ""}, "PDF_NO_TEXT"),
        ({"001": "x" * 40001}, "PDF_TEXT_LIMIT"),
    ],
)
def test_ocr_empty_and_excessive_text_are_rejected(tmp_path, monkeypatch, recognized, code):
    service = MaterialService(None, tmp_path)
    responses = iter([{"chunks": [], "scanned_pages": [1]}, recognized])
    monkeypatch.setattr(service, "run_worker", lambda *args, **kwargs: next(responses))
    with pytest.raises(AuthError) as error:
        service.extract(tmp_path / "scan.pdf")
    assert error.value.code == code
    assert not list(tmp_path.glob("mcq-ocr-*"))


def test_worker_does_not_inherit_stdin_and_handles_invalid_json(monkeypatch):
    def invalid(*args, **kwargs):
        assert kwargs["stdin"] == subprocess.DEVNULL
        return subprocess.CompletedProcess([], 0, b"not-json", b"")

    monkeypatch.setattr(subprocess, "run", invalid)
    with pytest.raises(AuthError) as error:
        MaterialService.run_worker(["worker"], 30)
    assert error.value.code == "INVALID_PDF"
