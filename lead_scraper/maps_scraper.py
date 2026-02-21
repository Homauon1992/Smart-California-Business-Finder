from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set
from urllib.parse import urlparse

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from .email_finder import WebsiteEmailFinder
from .models import Lead
from .validators import normalize_us_phone

LOGGER = logging.getLogger(__name__)


@dataclass
class SearchTarget:
    query: str
    org_type: str
    max_items: int


class GoogleMapsLeadScraper:
    def __init__(self, headless: bool = True, timeout_ms: int = 20000) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.email_finder = WebsiteEmailFinder()

    def scrape(self, targets: Iterable[SearchTarget]) -> List[Lead]:
        all_leads: List[Lead] = []
        seen_keys: Set[str] = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.set_default_timeout(self.timeout_ms)
            page.goto("https://www.google.com/maps", wait_until="domcontentloaded")

            for target in targets:
                LOGGER.info("Searching: %s", target.query)
                place_urls = self._collect_place_urls(page, target.query, target.max_items)
                LOGGER.info("Collected %s place URLs for %s", len(place_urls), target.query)

                for place_url in place_urls:
                    try:
                        lead = self._parse_place(page, place_url, target.org_type)
                    except Exception as exc:  # noqa: BLE001
                        LOGGER.warning("Failed parsing place %s: %s", place_url, exc)
                        continue

                    if not lead:
                        continue

                    key = f"{lead.name.lower()}|{lead.phone}|{lead.address.lower()}"
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    all_leads.append(lead)

            browser.close()

        return all_leads

    def _collect_place_urls(self, page: Page, query: str, max_items: int) -> List[str]:
        page.goto("https://www.google.com/maps", wait_until="domcontentloaded")
        self._prepare_maps_home(page)
        search_input = self._get_search_input(page)
        if not search_input:
            LOGGER.error(
                "Google Maps search input was not found. url=%s title=%s",
                page.url,
                page.title(),
            )
            self._save_debug_screenshot(page, "searchbox_missing.png")
            return []

        search_input.click()
        search_input.fill("")
        search_input.fill(query)
        search_input.press("Enter")
        page.wait_for_timeout(3000)

        urls: Set[str] = set()
        stagnant_rounds = 0
        previous_count = 0

        for _ in range(120):
            cards = page.locator("a.hfpxzc")
            count = cards.count()
            for idx in range(count):
                href = cards.nth(idx).get_attribute("href")
                if href and "/maps/place/" in href:
                    urls.add(self._normalize_maps_url(href))

            if len(urls) >= max_items:
                break

            if len(urls) == previous_count:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0
            previous_count = len(urls)

            if stagnant_rounds >= 7:
                break

            feed = page.locator('div[role="feed"]')
            if feed.count() > 0:
                feed.evaluate("(el) => el.scrollBy(0, el.scrollHeight)")
            else:
                page.mouse.wheel(0, 4500)
            page.wait_for_timeout(1500)

        return list(urls)[:max_items]

    def _prepare_maps_home(self, page: Page) -> None:
        self._handle_consent_if_present(page)
        page.wait_for_load_state("domcontentloaded")

    def _get_search_input(self, page: Page):
        candidate_selectors = [
            "input#searchboxinput",
            'input[aria-label*="Search"]',
            'input[aria-label*="search"]',
            'input[name="q"]',
        ]

        for selector in candidate_selectors:
            locator = page.locator(selector).first
            try:
                locator.wait_for(state="visible", timeout=15000)
                return locator
            except PlaywrightTimeoutError:
                continue
        return None

    def _handle_consent_if_present(self, page: Page) -> None:
        consent_buttons = [
            "button:has-text('Accept all')",
            "button:has-text('I agree')",
            "button:has-text('Reject all')",
            "form button:has-text('Accept')",
        ]
        for selector in consent_buttons:
            button = page.locator(selector).first
            try:
                if button.count() == 0:
                    continue
                button.click(timeout=3000)
                page.wait_for_timeout(1000)
                break
            except PlaywrightTimeoutError:
                continue

    @staticmethod
    def _save_debug_screenshot(page: Page, filename: str) -> None:
        try:
            debug_dir = Path("output") / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(debug_dir / filename), full_page=True)
        except Exception:  # noqa: BLE001
            return

    def _parse_place(self, page: Page, place_url: str, org_type: str) -> Optional[Lead]:
        page.goto(place_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        name = self._safe_text(page, "h1.DUwDvf")
        address = self._extract_address(page)
        raw_phone = self._extract_phone(page)
        phone = normalize_us_phone(raw_phone or "")
        website = self._extract_website(page)
        email = self.email_finder.find_email(website)

        if not name or not address or not phone or not email:
            return None

        city, state = self._parse_city_state(address)
        if not city or state != "CA":
            return None

        return Lead(
            name=name,
            org_type=org_type,
            phone=phone,
            email=email,
            address=address,
            city=city,
            state=state,
        )

    @staticmethod
    def _safe_text(page: Page, selector: str) -> str:
        try:
            loc = page.locator(selector).first
            if loc.count() == 0:
                return ""
            return (loc.inner_text() or "").strip()
        except PlaywrightTimeoutError:
            return ""

    def _extract_address(self, page: Page) -> str:
        selectors = [
            'button[data-item-id="address"]',
            'button[data-tooltip="Copy address"]',
            'div[aria-label^="Address:"]',
        ]
        for selector in selectors:
            text = self._safe_text(page, selector)
            if text:
                return re.sub(r"^Address:\s*", "", text).strip()
        return ""

    def _extract_phone(self, page: Page) -> str:
        selectors = [
            'button[data-item-id^="phone:"]',
            'button[data-tooltip="Copy phone number"]',
            'div[aria-label^="Phone:"]',
        ]
        for selector in selectors:
            text = self._safe_text(page, selector)
            if text:
                cleaned = re.sub(r"^(Phone:|Call)\s*", "", text).strip()
                if cleaned:
                    return cleaned
        return ""

    def _extract_website(self, page: Page) -> Optional[str]:
        selectors = ['a[data-item-id="authority"]', 'a[data-tooltip="Open website"]']
        for selector in selectors:
            try:
                loc = page.locator(selector).first
                if loc.count() == 0:
                    continue
                href = loc.get_attribute("href")
                if href and urlparse(href).scheme in ("http", "https"):
                    return href
            except PlaywrightTimeoutError:
                continue
        return None

    @staticmethod
    def _parse_city_state(address: str) -> tuple[str, str]:
        parts = [p.strip() for p in address.split(",") if p.strip()]
        if len(parts) < 2:
            return "", ""

        city = ""
        state = ""

        state_part = parts[-1]
        state_match = re.search(r"\b([A-Z]{2})\b", state_part)
        if state_match:
            state = state_match.group(1)

        if len(parts) >= 3:
            city = parts[-2]
        elif len(parts) == 2:
            city = parts[-1]

        city = re.sub(r"\d+", "", city).strip()
        return city, state

    @staticmethod
    def _normalize_maps_url(url: str) -> str:
        return url.split("&", 1)[0]
