import json
import logging
from pathlib import Path

from app.config import INDEX_FILE

logger = logging.getLogger(__name__)


def chapter_key(chapter) -> str:
    return str(chapter.get("id") or chapter["slug"])


def chapter_filename(key: str, slug: str) -> str:
    """Stable filename, independent of position."""
    return f"{key}-{slug}.md"


def load_index(cache_path: Path):
    index_file = cache_path / INDEX_FILE
    if not index_file.exists():
        return []
    try:
        return json.loads(index_file.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Could not read {index_file}: {e}")
        return []


def merge_with_cache(chapter_list, old_entries):
    """
    Merge the online chapter list with the cached index. Chapters cached
    earlier but no longer online are kept, placed after the nearest preceding
    chapter that still exists. Returns [(position, entry)], where position is
    the online index (or the anchor's index for deleted ones, -1 if at start).
    """
    online_keys = {chapter_key(c) for c in chapter_list}
    deleted, anchor = {}, None
    for e in old_entries:
        if e["key"] in online_keys:
            anchor = e["key"]
        else:
            deleted.setdefault(anchor, []).append(e)

    merged = [(-1, e) for e in deleted.get(None, [])]
    for i, c in enumerate(chapter_list):
        key = chapter_key(c)
        merged.append(
            (
                i,
                {
                    "key": key,
                    "title": c["title"],
                    "slug": c["slug"],
                    "file": chapter_filename(key, c["slug"]),
                    "url": c["url"],  # present only for chapters still online
                },
            )
        )
        merged.extend((i, e) for e in deleted.get(key, []))
    return merged


def write_index(cache_path: Path, merged):
    """Persist order of everything on disk (incl. entries beyond the
    --chapters limit) so deleted chapters keep their position next run."""
    index = [
        {k: v for k, v in e.items() if k != "url"}
        for _, e in merged
        if (cache_path / e["file"]).exists()
    ]
    tmp = cache_path / (INDEX_FILE + ".tmp")
    tmp.write_text(json.dumps(index, indent=2), encoding="utf-8")
    tmp.replace(cache_path / INDEX_FILE)  # atomic: no half-written index on crash
