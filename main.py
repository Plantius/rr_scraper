import argparse
import json
import logging
import re
from pathlib import Path

import html2text
import requests
from bs4 import BeautifulSoup
from markdown_pdf import MarkdownPdf, Section

h = html2text.HTML2Text()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

BASE_URL = "https://www.royalroad.com"


def fetch_page(url: str):
    """Fetch the HTML content of a page."""
    try:
        response = requests.get(url)
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
    title = soup.title
    try:
        if script_tag is not None and title is not None:
            script_content = script_tag.string
            match = re.search(r"window\.chapters\s*=\s*(\[[\s\S]*?\]);", script_content)
            if match is None:
                raise Exception("No chapters found.")

            chapters = json.loads(match.group(1))
            return title.string, chapters
    except Exception as e:
        logger.error(f"Chapters not found on {url}: {e}")
        return "", []


def process_chapters(chapter_list, num_chapters):
    """Process and clean the specified number of chapters."""
    processed_chapters = []
    chapter_titles = []

    for count, chapter in enumerate(chapter_list):
        print(f"Processing {chapter['title']}")

        if count >= num_chapters:
            break
        page = fetch_page(f"{BASE_URL}{chapter['url']}")
        if page is None:
            continue

        soup = page.find("div", class_="chapter-content")
        if soup is None:
            continue
        slug = chapter["slug"]
        title = chapter["title"]
        text = h.handle(soup.prettify())

        text = f'<a id="{slug}"></a>\n\n## {title}\n\n{text}'

        processed_chapters.append(text)
        chapter_titles.append((title, slug))

    toc_lines = ["## Table of Contents\n"]
    for title, slug in chapter_titles:
        toc_lines.append(f"- [{title}](#{slug})")

    toc = "\n".join(toc_lines)
    return processed_chapters, toc


def save_as_markdown(processed_chapters: list[str], output_path: str = "book.md"):
    """Combine all chapters into a single markdown file."""
    content: str = "\n\n---\n\n".join(processed_chapters)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Markdown file saved to {output_path}")


def embed_images_locally(markdown_text: str, img_dir: str = "images") -> str:
    """Download all remote images and replace URLs with local paths."""
    Path(img_dir).mkdir(exist_ok=True)
    pattern = re.compile(r"!\[[^\]]*\]\((https?://[^\)]+)\)")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.5993.70 Safari/537.36"
        )
    }

    for match in pattern.finditer(markdown_text):
        url = match.group(1)
        filename = Path(img_dir) / Path(url.split("/")[-1].split("?")[0])

        if not filename.exists():
            try:
                r = requests.get(url, headers=headers)
                if r.status_code == 200:
                    with open(filename, "wb") as f:
                        f.write(r.content)
            except Exception as e:
                logger.error(f"Coumsg=ld not download image {url}: {e}")
                continue

        markdown_text = markdown_text.replace(url, str(filename))
    return markdown_text


def save_as_pdf(processed_chapters: list[str], output_path: str = "book.pdf"):
    """Convert a list of markdown strings to a PDF using the markdown-pdf Python package."""

    pdf = MarkdownPdf()
    combined_md = "\n\n---\n\n".join(processed_chapters)
    combined_md = embed_images_locally(combined_md)

    pdf.add_section(Section(combined_md))
    pdf.save(output_path)

    logger.info(f"PDF file saved to {output_path}")


def convert_md_to_pdf(input_file: str, output_file: str | None = None):
    """Convert an existing Markdown file to a PDF."""
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(f"File {input_path} does not exist.")
        return

    output_path = Path(output_file) if output_file else input_path.with_suffix(".pdf")

    pdf = MarkdownPdf()
    input_text = embed_images_locally(input_path.read_text(encoding="utf-8"))
    pdf.add_section(Section(input_text))
    pdf.save(output_path)
    logger.info(f"PDF file saved to {output_path}")


def parse_arguments():
    """Parse command-line arguments using argparse."""
    parser = argparse.ArgumentParser(
        description="Scrape and convert Royal Road stories to PDF or Markdown."
    )

    subparsers = parser.add_subparsers(dest="command", required=False)

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
        type=bool,
        default=True,
        help="Save output as a Markdown file (.md).",
    )
    scrape_parser.add_argument(
        "-p",
        "--pdf",
        action="store_true",
        help="Save output as a PDF file (.pdf).",
    )

    convert_parser = subparsers.add_parser(
        "convert", help="Convert an existing Markdown file to PDF."
    )
    convert_parser.add_argument("input", help="Path to the Markdown file.")
    convert_parser.add_argument(
        "-o", "--output", help="Output PDF file name.", default=None
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.command == "convert":
        convert_md_to_pdf(args.input, args.output)
        return

    title, chapters = extract_chapters(args.url)
    if args.title:
        title = args.title
    num_chapters = args.chapters or len(chapters)
    processed_chapters, toc = process_chapters(chapters, num_chapters)
    full_content = [f"# {title}", toc, *processed_chapters]

    if args.markdown:
        save_as_markdown(full_content, f"{title}.md")
    if args.pdf:
        save_as_pdf(full_content, f"{title}.pdf")


if __name__ == "__main__":
    main()
