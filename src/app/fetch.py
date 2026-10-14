import logging

import requests
from bs4 import BeautifulSoup

from app.config import HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def fetch_page(url: str):
    """Fetch the HTML content of a page."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Cannot fetch {url}: {e}")
        return None
    return BeautifulSoup(response.content, "html.parser")
