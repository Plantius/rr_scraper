import logging
import time
from pathlib import Path

import html2text
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from app.cache import load_index, merge_with_cache, write_index
from app.config import BASE_URL, CHAPTER_DELAY
from app.fetch import fetch_page

logger = logging.getLogger(__name__)
h = html2text.HTML2Text()


def scrape_chapters(chapter_list, num_chapters, cache_dir: str = "chapters"):
    """
    Fetch chapters one at a time and cache each to its own file. Cached
    chapters are skipped, so interrupted runs resume. Chapters cached earlier
    but since deleted online are retained in their original position.
    The index is saved after every newly fetched chapter.

    Returns the ordered list of (title, slug, filepath).
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    merged = merge_with_cache(chapter_list, load_index(cache_path))
    selected = [(pos, e) for pos, e in merged if pos < num_chapters]
    manifest = []

    try:
        with logging_redirect_tqdm(), tqdm(selected, desc="Chapters", unit="ch") as bar:
            for _, entry in bar:
                title, slug = entry["title"], entry["slug"]
                filepath = cache_path / entry["file"]
                bar.set_postfix_str(title[:40])

                if filepath.exists():
                    manifest.append((title, slug, filepath))
                    continue

                if not entry.get("url"):
                    logger.warning(
                        f"Cached file for deleted chapter '{title}' is missing"
                    )
                    continue

                page = fetch_page(f"{BASE_URL}{entry['url']}")
                if page is None:
                    logger.warning(f"Skipping chapter '{title}' (fetch failed)")
                    continue

                soup = page.find("div", class_="chapter-content")
                if soup is None:
                    logger.warning(f"Skipping chapter '{title}' (content not found)")
                    continue

                text = h.handle(soup.prettify())
                text = f'<a id="{slug}"></a>\n\n## {title}\n\n{text}'

                filepath.write_text(text, encoding="utf-8")
                manifest.append((title, slug, filepath))
                write_index(cache_path, merged)

                time.sleep(CHAPTER_DELAY)
    finally:
        write_index(cache_path, merged)

    return manifest
