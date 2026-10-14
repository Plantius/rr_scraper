import json
import logging
import re

from app.fetch import fetch_page

logger = logging.getLogger(__name__)


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
