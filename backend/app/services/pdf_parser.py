from io import BytesIO
from pathlib import Path

import fitz
import pdfplumber

from app.utils.text import clean_legal_text


class PDFParser:
    def extract_text(self, file_path: Path) -> str:
        text = self._extract_with_pymupdf(file_path)
        if len(text.split()) < 200:
            text = self._extract_with_pdfplumber(file_path)
        return clean_legal_text(text)

    def extract_text_from_bytes(self, content: bytes) -> str:
        text = self._extract_with_pymupdf_bytes(content)
        if len(text.split()) < 200:
            text = self._extract_with_pdfplumber_bytes(content)
        return clean_legal_text(text)

    def get_page_count_from_bytes(self, content: bytes) -> int:
        with fitz.open(stream=content, filetype="pdf") as document:
            return document.page_count

    def _extract_with_pymupdf(self, file_path: Path) -> str:
        parts: list[str] = []
        with fitz.open(file_path) as document:
            for page in document:
                parts.append(page.get_text("text"))
        return "\n".join(parts)

    def _extract_with_pymupdf_bytes(self, content: bytes) -> str:
        parts: list[str] = []
        with fitz.open(stream=content, filetype="pdf") as document:
            for page in document:
                parts.append(page.get_text("text"))
        return "\n".join(parts)

    def _extract_with_pdfplumber(self, file_path: Path) -> str:
        parts: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)

    def _extract_with_pdfplumber_bytes(self, content: bytes) -> str:
        parts: list[str] = []
        with pdfplumber.open(BytesIO(content)) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)
