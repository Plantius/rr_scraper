import argparse
import json
import logging
import re
import time
from pathlib import Path

import html2text
import requests
from bs4 import BeautifulSoup
from markdown_pdf import MarkdownPdf, Section

h = html2text.HTML2Text()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

BASE_URL = "https://www.royalroad.com"
REQUEST_TIMEOUT = 15
CHAPTER_DELAY = 1.0
PDF_BATCH_SIZE = 50
INDEX_FILE = "index.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.5993.70 Safari/537.36"
    )
}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


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


def fetch_page(url: str):
    """Fetch the HTML content of a page."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Cannot fetch {url}: {e}")
        return None
    return BeautifulSoup(response.content, "html.parser")


def extract_chapters(url: str):
    """Extract the story title and chapters list from the story URL."""
    soup = fetch_page(url)
    if soup is None:
        return "", []

    script_tag = soup.find("script", string=re.compile(r"window\.chapters\s*="))
    title_tag = soup.find("h1", class_="font-white") or soup.find("h1")
    try:
        if script_tag is not None and title_tag is not None:
            script_content = script_tag.string
            match = re.search(r"window\.chapters\s*=\s*(\[[\s\S]*?\]);", script_content)
            if match is None:
                raise Exception("No chapters found.")

            chapters = json.loads(match.group(1))
            return title_tag.get_text(strip=True), chapters
    except Exception as e:
        logger.error(f"Chapters not found on {url}: {e}")
        return "", []

    return "", []


def scrape_chapters(chapter_list, num_chapters, cache_dir: str = "chapters"):
    """
    Fetch chapters one at a time and cache each to its own file. Cached
    chapters are skipped, so interrupted runs resume. Chapters cached earlier
    but since deleted online are retained in their original position.

    Returns the ordered list of (title, slug, filepath).
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(exist_ok=True)

    merged = merge_with_cache(chapter_list, load_index(cache_path))
    manifest = []

    try:
        for position, entry in merged:
            if position >= num_chapters:
                continue

            title, slug = entry["title"], entry["slug"]
            filepath = cache_path / entry["file"]

            if filepath.exists():
                note = "" if entry.get("url") else ", deleted online"
                logger.info(f"Skipping '{title}' (already cached{note})")
                manifest.append((title, slug, filepath))
                continue

            if not entry.get("url"):
                logger.warning(f"Cached file for deleted chapter '{title}' is missing")
                continue

            logger.info(f"Processing {title}")
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

            time.sleep(CHAPTER_DELAY)
    finally:
        # Persist order of everything on disk (incl. entries beyond the
        # --chapters limit) so deleted chapters keep their position next run.
        index = [
            {k: v for k, v in e.items() if k != "url"}
            for _, e in merged
            if (cache_path / e["file"]).exists()
        ]
        (cache_path / INDEX_FILE).write_text(
            json.dumps(index, indent=2), encoding="utf-8"
        )

    return manifest


def build_toc(manifest) -> str:
    toc_lines = ["## Table of Contents\n"]
    for title, slug, _ in manifest:
        toc_lines.append(f"- [{title}](#{slug})")
    return "\n".join(toc_lines)


def save_as_markdown(title: str, manifest, output_path: str):
    """Stream cached chapter files into a single markdown file without
    holding the whole book in memory at once."""
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(f"# {title}\n\n")
        out.write(build_toc(manifest))
        for _, _, filepath in manifest:
            out.write("\n\n---\n\n")
            out.write(filepath.read_text(encoding="utf-8"))
    logger.info(f"Markdown file saved to {output_path}")


def embed_images_locally(markdown_text: str, img_dir: str = "images") -> str:
    """Download all remote images and replace URLs with local paths."""
    Path(img_dir).mkdir(exist_ok=True)
    pattern = re.compile(r"!\[[^\]]*\]\((https?://[^\)]+)\)")

    for match in pattern.finditer(markdown_text):
        url = match.group(1)
        filename = Path(img_dir) / Path(url.split("/")[-1].split("?")[0])

        if not filename.exists():
            try:
                r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
                if r.status_code == 200:
                    with open(filename, "wb") as f:
                        f.write(r.content)
            except Exception as e:
                logger.error(f"Could not download image {url}: {e}")
                continue

        markdown_text = markdown_text.replace(url, str(filename))
    return markdown_text


def save_as_pdf(
    title: str, manifest, output_path: str, batch_size: int = PDF_BATCH_SIZE
):
    """
    Convert cached chapters to a PDF. Chapters are grouped into batches and
    added as separate fitz Sections so the whole book's markdown/HTML is
    never held in memory at once - important for 100k+ line books.
    """
    pdf = MarkdownPdf()

    header_md = f"# {title}\n\n{build_toc(manifest)}"
    pdf.add_section(Section(embed_images_locally(header_md)))

    batch = []
    for i, (_, _, filepath) in enumerate(manifest, start=1):
        chapter_md = embed_images_locally(filepath.read_text(encoding="utf-8"))
        batch.append(chapter_md)

        if len(batch) >= batch_size or i == len(manifest):
            section_md = "\n\n---\n\n".join(batch)
            pdf.add_section(Section(section_md))
            logger.info(f"Added batch ending at chapter {i}/{len(manifest)} to PDF")
            batch = []

    pdf.save(output_path)
    logger.info(f"PDF file saved to {output_path}")


def convert_md_to_pdf(
    input_file: str, output_file: str | None = None, batch_size: int = PDF_BATCH_SIZE
):
    """Convert an existing Markdown file to a PDF, splitting on chapter/section
    breaks ('---' on its own line) so large files aren't loaded as one giant
    Section."""
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(f"File {input_path} does not exist.")
        return

    output_path = Path(output_file) if output_file else input_path.with_suffix(".pdf")

    pdf = MarkdownPdf()
    full_text = input_path.read_text(encoding="utf-8")
    parts = re.split(r"\n---\n", full_text)

    batch = []
    for i, part in enumerate(parts, start=1):
        batch.append(embed_images_locally(part))
        if len(batch) >= batch_size or i == len(parts):
            pdf.add_section(Section("\n\n---\n\n".join(batch)))
            logger.info(f"Added batch ending at part {i}/{len(parts)} to PDF")
            batch = []

    pdf.save(output_path)
    logger.info(f"PDF file saved to {output_path}")


def parse_arguments():
    """Parse command-line arguments using argparse."""
    parser = argparse.ArgumentParser(
        description="Scrape and convert Royal Road stories to PDF or Markdown."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape_parser = subparsers.add_parser(
        "scrape", help="Scrape a Royal Road story into Markdown or PDF."
    )
    scrape_parser.add_argument("url", help="The URL of the story on Royal Road.")
    scrape_parser.add_argument(
        "-t", "--title", help="Specify the title for the output file."
    )
    scrape_parser.add_argument(
        "-c",
        "--chapters",
        type=int,
        default=None,
        help="Number of chapters to scrape (default: all).",
    )
    scrape_parser.add_argument(
        "-m",
        "--markdown",
        action="store_true",
        default=True,
        help="Save output as a Markdown file (.md). Enabled by default.",
    )
    scrape_parser.add_argument(
        "--no-markdown",
        dest="markdown",
        action="store_false",
        help="Do not save output as a Markdown file.",
    )
    scrape_parser.add_argument(
        "-p",
        "--pdf",
        action="store_true",
        help="Save output as a PDF file (.pdf).",
    )
    scrape_parser.add_argument(
        "--cache-dir",
        default=None,
        help="Directory to store per-chapter files for caching/resuming (default: chapters/<story-title>).",
    )
    scrape_parser.add_argument(
        "--batch-size",
        type=int,
        default=PDF_BATCH_SIZE,
        help=f"Chapters per PDF section batch, controls memory use (default: {PDF_BATCH_SIZE}).",
    )

    convert_parser = subparsers.add_parser(
        "convert", help="Convert an existing Markdown file to PDF."
    )
    convert_parser.add_argument("input", help="Path to the Markdown file.")
    convert_parser.add_argument(
        "-o", "--output", help="Output PDF file name.", default=None
    )
    convert_parser.add_argument(
        "--batch-size",
        type=int,
        default=PDF_BATCH_SIZE,
        help=f"Sections per PDF batch, controls memory use (default: {PDF_BATCH_SIZE}).",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.command == "convert":
        convert_md_to_pdf(args.input, args.output, batch_size=args.batch_size)
        return

    title, chapters = extract_chapters(args.url)
    cache_dir = args.cache_dir or str(Path("chapters") / slugify(title))

    if not title or not chapters:
        logger.error("Failed to extract story title/chapters. Aborting.")
        return

    if args.title:
        title = args.title
    num_chapters = args.chapters or len(chapters)

    manifest = scrape_chapters(chapters, num_chapters, cache_dir=cache_dir)
    if not manifest:
        logger.error("No chapters were successfully scraped. Aborting.")
        return

    if args.markdown:
        save_as_markdown(title, manifest, f"{title}.md")
    if args.pdf:
        save_as_pdf(title, manifest, f"{title}.pdf", batch_size=args.batch_size)


if __name__ == "__main__":
    main()
