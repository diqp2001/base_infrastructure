"""
Wikipedia pages of the S&P 500 constituents, as raw wikitext (MediaWiki ``action=raw``): today's list and the history
of changes. A public read with a generic User-Agent (Wikipedia asks automated clients for one); nothing is sent but
the page titles. Parsing is application/services/universe/sp500_membership.
"""

from __future__ import annotations

import requests

URL = "https://en.wikipedia.org/w/index.php"
CURRENT = "List of S&P 500 companies"
HISTORY = "Historical components of the S&P 500"
USER_AGENT = "base_infrastructure-research/1.0 (python-requests)"


def wikitext(title: str, timeout: float = 60.0) -> str:
    response = requests.get(URL, params={"title": title, "action": "raw"}, headers={"User-Agent": USER_AGENT},
                            timeout=timeout)
    response.raise_for_status()
    return response.text


def sp500_pages() -> tuple:
    """(today's constituents wikitext, history of changes wikitext)."""
    return wikitext(CURRENT), wikitext(HISTORY)
