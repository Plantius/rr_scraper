import argparse
import logging
from pathlib import Path

from app.config import PDF_BATCH_SIZE
from app.royalroad import extract_chapters
from app.scraper import scrape_chapters
from app.utils import slugify, url_slug
from export.markdown import save_as_markdown
from export.pdf import convert_md_to_pdf, save_as_pdf

logger = logging.getLogger(__name__)


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
    scrape_parser.add_argument(
        "-z",
        "--compress",
        action="store_true",
        help="Gzip the Markdown output (.md.gz).",
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
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    args = parse_arguments()

    if args.command == "convert":
        convert_md_to_pdf(args.input, args.output, batch_size=args.batch_size)
        return

    title, chapters = extract_chapters(args.url)
    slug = slugify(title) or url_slug(args.url)
    cache_dir = args.cache_dir or str(Path("chapters") / slug)

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
        ext = ".md.gz" if args.compress else ".md"
        save_as_markdown(title, manifest, f"{slug}{ext}")
    if args.pdf:
        save_as_pdf(title, manifest, f"{slug}.pdf", batch_size=args.batch_size)


if __name__ == "__main__":
    main()
