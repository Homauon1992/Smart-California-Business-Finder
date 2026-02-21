from __future__ import annotations

from collections import deque
from typing import Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .validators import extract_first_valid_email, is_valid_email

CONTACT_KEYWORDS = ("contact", "impressum", "about", "support")


class WebsiteEmailFinder:
    def __init__(self, timeout: int = 10, max_pages: int = 6) -> None:
        self.timeout = timeout
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            }
        )

    def find_email(self, website_url: Optional[str]) -> Optional[str]:
        if not website_url:
            return None

        normalized = self._normalize_url(website_url)
        if not normalized:
            return None

        return self._crawl_for_email(normalized)

    def _crawl_for_email(self, base_url: str) -> Optional[str]:
        visited: Set[str] = set()
        queue = deque([base_url])
        pages_visited = 0
        netloc = urlparse(base_url).netloc

        while queue and pages_visited < self.max_pages:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            html = self._fetch_html(url)
            if not html:
                continue

            pages_visited += 1
            email = extract_first_valid_email(html)
            if email and is_valid_email(email):
                return email

            soup = BeautifulSoup(html, "html.parser")
            for link in soup.select("a[href]"):
                href = link.get("href", "").strip()
                if not href:
                    continue

                if href.lower().startswith("mailto:"):
                    mail = href.split(":", 1)[-1].split("?")[0].strip().lower()
                    if is_valid_email(mail):
                        return mail

                next_url = urljoin(url, href)
                parsed = urlparse(next_url)
                if parsed.netloc != netloc:
                    continue

                anchor_text = (link.get_text(" ", strip=True) or "").lower()
                target = f"{parsed.path} {anchor_text}".lower()
                if any(keyword in target for keyword in CONTACT_KEYWORDS):
                    queue.append(next_url)

        return None

    def _fetch_html(self, url: str) -> Optional[str]:
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code >= 400:
                return None
            return resp.text
        except requests.RequestException:
            return None

    @staticmethod
    def _normalize_url(url: str) -> Optional[str]:
        candidate = url.strip()
        if not candidate:
            return None
        if not candidate.startswith(("http://", "https://")):
            candidate = f"https://{candidate}"
        return candidate
