import logging
import re
from pathlib import Path

import requests

from app.config import HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


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
