from __future__ import annotations
import re
from typing import Tuple

import httpx
from bs4 import BeautifulSoup


class DocumentProcessor:

    def process_file(self, path: str, ext: str) -> str:
        ext = ext.lower()
        if ext == ".pdf":
            return self._pdf(path)
        if ext in (".txt", ".md"):
            return self._text(path)
        if ext == ".docx":
            return self._docx(path)
        raise ValueError(f"Unsupported extension: {ext}")

    def _pdf(self, path: str) -> str:
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n".join(pages).strip()
        except ImportError:
            pass

        try:
            import PyPDF2
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(p.extract_text() or "" for p in reader.pages).strip()
        except ImportError:
            raise RuntimeError("Install pdfplumber for PDF support: pip install pdfplumber")

    def _text(self, path: str) -> str:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def _docx(self, path: str) -> str:
        try:
            from docx import Document
            return "\n".join(p.text for p in Document(path).paragraphs)
        except ImportError:
            raise RuntimeError("Install python-docx for Word support: pip install python-docx")

    async def process_url(self, url: str) -> Tuple[str, str]:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url

        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return title, text.strip()
