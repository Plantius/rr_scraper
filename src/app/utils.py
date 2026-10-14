import gzip
import re
from pathlib import Path
from urllib.parse import urlparse


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def url_slug(url: str) -> str:
    parts = [p for p in urlparse(url).path.split("/") if p]
    try:
        return parts[parts.index("fiction") + 2]
    except (ValueError, IndexError):
        return ""


def open_text(path, mode: str):
    """Open a text file, transparently gzipped if the path ends in .gz."""
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, mode + "t", encoding="utf-8")
    return open(path, mode, encoding="utf-8")
