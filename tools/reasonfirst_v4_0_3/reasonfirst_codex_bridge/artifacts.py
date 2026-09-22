from __future__ import annotations

import base64
from io import BytesIO
import json
import mimetypes
import os
from pathlib import Path
import stat
import xml.etree.ElementTree as ET
import zipfile
from typing import Any

TEXT_EXTENSIONS = {
    ".md", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".yaml", ".yml",
    ".xml", ".html", ".htm", ".log", ".svg",
}
DOCUMENT_EXTENSIONS = {".pdf", ".docx"}
VISUAL_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".pdf"}
SAFE_ARTIFACT_EXTENSIONS = TEXT_EXTENSIONS | DOCUMENT_EXTENSIONS | VISUAL_EXTENSIONS


def _within(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or any(part in {"..", ""} for part in rel.parts):
        raise ValueError("artifact path must be a safe repository-relative path")
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("artifact path escapes workspace") from exc
    if candidate.is_symlink():
        raise ValueError("symlink artifacts are not supported")
    return candidate


def artifact_file(root: Path, relative: str, *, max_bytes: int = 8 * 1024 * 1024) -> dict[str, Any]:
    path = _within(root, relative)
    if not path.is_file():
        raise FileNotFoundError(relative)
    ext = path.suffix.lower()
    if ext not in SAFE_ARTIFACT_EXTENSIONS:
        raise ValueError(f"unsupported artifact extension: {ext or '<none>'}")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("artifact is not a regular file")
    if info.st_size > max_bytes:
        raise ValueError(f"artifact is too large to publish: {info.st_size} bytes > {max_bytes}")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return {
        "absolute_path": str(path),
        "path": str(path.relative_to(root)),
        "name": path.name,
        "extension": ext,
        "size": info.st_size,
        "mime_type": mime,
    }


def _read_text(path: Path, max_chars: int) -> tuple[str, bool]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    return text[:max_chars], len(text) > max_chars


def _extract_docx(path: Path, max_chars: int) -> tuple[str, bool]:
    with zipfile.ZipFile(path) as archive:
        raw = archive.read("word/document.xml")
    root = ET.fromstring(raw)
    chunks: list[str] = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            chunks.append(node.text)
        elif node.tag.endswith("}p"):
            chunks.append("\n")
    text = "".join(chunks).strip()
    return text[:max_chars], len(text) > max_chars


def _extract_pdf(path: Path, max_chars: int, max_pages: int = 20) -> tuple[str, bool, int]:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return "", False, 0
    reader = PdfReader(str(path))
    chunks: list[str] = []
    pages = min(len(reader.pages), max_pages)
    for page in reader.pages[:pages]:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            chunks.append("")
        if sum(len(c) for c in chunks) >= max_chars:
            break
    text = "\n\n".join(chunks)
    return text[:max_chars], len(text) > max_chars or len(reader.pages) > pages, len(reader.pages)


def _image_preview(path: Path, *, max_base64_chars: int = 9000) -> dict[str, Any] | None:
    try:
