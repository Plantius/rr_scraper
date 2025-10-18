import argparse
import json
import logging
import re
import subprocess

import html2text
import numpy as np
import requests
from bs4 import BeautifulSoup

h = html2text.HTML2Text()
logger = logging.getLogger(__name__)

BASE_URL = "https://www.royalroad.com"
TAG_REMOVE = ["p", "span", "em", "hr", "a", "br", "img"]
REPLACE_LIST = [
    ["$", "\\$"],
    ["\u200b", ""],
    ["\xa0", ""],
    ["\n", "\\par\n"],
    ["%", "\\%"],
    ["#", "\\#"],
    ["&", "\\&"],
    ["_", "\\textunderscore"],
    ["<strong>", "\\textbf{"],
    ["</strong>", "}"],
    ["<sup>", "$^{"],
    ["</sup>", "}$"],
    ["\\&gt;", "\\textgreater"],
    ["\\&lt;", "\\textless"],
    [
        "The author's content has been appropriated; report any instances of this story on Amazon.",
        "",
    ],
    [
        "Taken from Royal Road, this narrative should be reported if found on Amazon.",
        "",
    ],
    [
        "Unauthorized usage: this narrative is on Amazon without the author’s consent. Report any sightings.",
        "",
    ],
]


def replace_invalid_chars(content: str):
    for old, new in REPLACE_LIST:
        content = content.replace(old, new)
    return content


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
            if match:
                chapters = json.loads(match.group(1))
                return title.string, chapters
    except Exception as e:
        logger.error(f"Chapters not found on {url}: {e}")
        return "", []


def process_chapters(chapter_list, num_chapters):
    """Process and clean the specified number of chapters."""
    processed_chapters = []
    for count, chapter in enumerate(chapter_list):
        print(f"Processing {chapter['title']}")
        
        if count >= num_chapters:
            break

        page = fetch_page(f"{BASE_URL}{chapter['url']}")
        
        print(h.handle(page))
        # for tag in TAG_REMOVE:
        #     for element in page.find_all(tag):
        #         element.unwrap()

        # content_div = page.find("div", class_="chapter-inner chapter-content")
        # if not content_div:
        #     continue

        # for div in content_div.find_all("div"):
        #     div.unwrap()

        # raw_content = replace_invalid_chars(
        #     "".join(str(item) for item in content_div.contents if item)
        # )

        # chapter["chapter_content"] = raw_content
        # processed_chapters.append(chapter)
        # print("Done processing.")
    return processed_chapters


def generate_latex(chapter_list, title):
    """Generate a LaTeX file from the processed chapters."""
    template = np.loadtxt("latex_template.tex", dtype=str)
    latex = [line.replace("TITLE", title) for line in template]

    for chapter in chapter_list:
        latex_section = (
            f"\\section*{{{replace_invalid_chars(chapter['title'])}}}\n"
            f"\\addcontentsline{{toc}}{{section}}{{{chapter['title']}}}\n"
            f"{chapter['chapter_content']}\n"
        )
        latex.insert(-1, latex_section)

    tex_file = f"{title}.tex"
    with open(tex_file, "w", encoding="utf-8") as file:
        file.write("\n".join(latex))

    return tex_file


def compile_pdf(tex_file: str):
    """Compile a LaTeX file into a PDF."""
    file_name = tex_file.split(".")[0]
    subprocess.run(["pdflatex", "-interaction=nonstopmode", tex_file], check=True)
    subprocess.run(
        ["rm", "-f", f"{file_name}.aux", f"{file_name}.log", f"{file_name}.out"]
    )


def parse_arguments():
    """Parse command-line arguments using argparse."""
    parser = argparse.ArgumentParser(
        description="Scrape and convert Royal Road stories to PDF."
    )
    parser.add_argument("url", help="The URL of the story on Royal Road.")
    parser.add_argument("-l", "--title", help="Specify the title for the PDF output.")
    parser.add_argument(
        "-c",
        "--chapters",
        type=int,
        help="Number of chapters to scrape (default: all).",
        default=None,
    )
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
    processed_chapters = process_chapters(chapters, num_chapters)

    # Generate LaTeX and compile PDF
    tex_file = generate_latex(processed_chapters, title)
    compile_pdf(tex_file)


if __name__ == "__main__":
    main()
