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
