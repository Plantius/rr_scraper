import argparse
import json
import logging
import re

import html2text
import requests
from bs4 import BeautifulSoup

h = html2text.HTML2Text()
logger = logging.getLogger(__name__)

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

        text = h.handle(soup.prettify())
        text = f"## {chapter['title']}\n\n" + text
        processed_chapters.append(text)
        chapter_titles.append(chapter["title"])

    toc_lines = ["## Table of Contents\n"]
    for title in chapter_titles:
        anchor = title.lower().replace(" ", "-")
        toc_lines.append(f"- [{title}](#{anchor})")

    toc = "\n".join(toc_lines)
    return processed_chapters, toc


def generate_index(chapters: list[str], num_chapters: int) -> str:
    """
    Generate a Markdown index (table of contents) linking to all chapter titles.
    """
    index_lines = ["## Table of Contents\n"]
    for i in range(min(num_chapters, len(chapters))):
        # Try to extract a title from the chapter text (first line)
        lines = chapters[i].splitlines()
        title = next(
            (
                line.strip("# ").strip()
                for line in lines
                if line.strip().startswith("#")
            ),
            f"Chapter {i + 1}",
        )
        # Create an internal markdown link anchor (GitHub-style)
        anchor = title.lower().replace(" ", "-")
        index_lines.append(f"- [{title}](#{anchor})")
    return "\n".join(index_lines)


def save_as_markdown(processed_chapters: list[str], output_path: str = "book.md"):
    """Combine all chapters into a single markdown file."""
    content = "\n\n---\n\n".join(processed_chapters)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"File saved to {output_path}")


def parse_arguments():
    """Parse command-line arguments using argparse."""
    parser = argparse.ArgumentParser(
        description="Scrape and convert Royal Road stories to PDF or Markdown."
    )
    parser.add_argument("url", help="The URL of the story on Royal Road.")
    parser.add_argument("-t", "--title", help="Specify the title for the output file.")
    parser.add_argument(
        "-c",
        "--chapters",
        type=int,
        default=None,
        help="Number of chapters to scrape (default: all).",
    )
    parser.add_argument(
        "-m",
        "--markdown",
        type=bool,
        default=True,
        help="Save output as a Markdown file (.md).",
    )
    # parser.add_argument(
    #     "-p",
    #     "--pdf",
    #     action="store_true",
    #     default=False,
    #     help="Save output as a PDF file (.pdf).",
    # )
    return parser.parse_args()


def main():
    args = parse_arguments()
    url = args.url
    title, chapters = extract_chapters(url)

    # Use the provided title or fallback to the story title
    if args.title:
        title = args.title

    # Use the specified number of chapters or all chapters
    num_chapters = args.chapters or len(chapters)
    processed_chapters, toc = process_chapters(chapters, num_chapters)
    full_content = [f"# {title}", toc, *processed_chapters]

    if args.markdown:
        save_as_markdown(full_content, f"{title}.md")


if __name__ == "__main__":
    main()
