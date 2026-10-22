"""Isolated PDF-to-text worker; never executes document scripts or follows links."""

import json
import re
import sys
import unicodedata
from hashlib import sha256
from pathlib import Path

import pymupdf

MAX_BYTES = 5 * 1024 * 1024
SPLITTER = "page-char-1200-overlap-120-v1"
OCR_SPLITTER = "windows-ocr-page-char-1200-overlap-120-v1"
MAX_OCR_PAGES = 10


class PdfRejected(Exception):
    pass


def clean_text(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = "".join(c for c in value if c in "\n\t" or not unicodedata.category(c).startswith("C"))
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()).strip()


def text_chunks(text, number):
    chunks = []
    for start in range(0, len(text), 1080):
        content = text[start : start + 1200].strip()
        if content:
            chunks.append(
                {
                    "page": number,
                    "content": content,
                    "hash": sha256(content.encode()).hexdigest(),
                    "tokens": max(1, len(content.encode())),
                }
            )
        if start + 1200 >= len(text):
            break
    return chunks


def extract(path, ocr_dir=None):
    try:
        with pymupdf.open(path) as document:
            if not document.is_pdf:
                raise PdfRejected("INVALID_PDF")
            if document.is_encrypted or document.needs_pass:
                raise PdfRejected("ENCRYPTED_PDF")
            if not 1 <= len(document) <= 100:
                raise PdfRejected("PDF_PAGE_LIMIT")
            chunks, empty, total, scanned = [], [], 0, []
            for number, page in enumerate(document, 1):
                text = clean_text(page.get_text("text", sort=True))
                total += len(text)
                if len(text) > 40000 or total > 200000:
                    raise PdfRejected("PDF_TEXT_LIMIT")
                if not text:
                    empty.append(number)
                    if ocr_dir and page.get_images():
                        scanned.append(number)
                        if len(scanned) > MAX_OCR_PAGES:
                            raise PdfRejected("PDF_OCR_PAGE_LIMIT")
                        # One bounded raster at a time, at most ~12 MB RGB.
                        scale = min(2, 2000 / max(page.rect.width, page.rect.height))
                        image = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
                        image.save(Path(ocr_dir) / f"{number:03d}.png")
                        del image
                chunks.extend(text_chunks(text, number))
            if not chunks and not scanned:
                raise PdfRejected("PDF_NO_TEXT")
            return {
                "page_count": len(document),
                "empty_pages": empty,
                "chunks": chunks,
                "scanned_pages": scanned,
                "text_characters": total,
            }
    except PdfRejected:
        raise
    except Exception:
        raise PdfRejected("INVALID_PDF") from None


if __name__ == "__main__":
    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)
    try:
        result = extract(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    except PdfRejected as exc:
        result = {"error": str(exc)}
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=True).encode("ascii"))
