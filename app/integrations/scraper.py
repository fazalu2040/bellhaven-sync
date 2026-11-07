from __future__ import annotations

import re
from typing import Any

import requests
from bs4 import BeautifulSoup

from app.models import ScrapedLocation


class BellhavenScraper:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def fetch_page(self) -> str:
        response = requests.get(self.base_url, timeout=30)
        response.raise_for_status()
        return response.text

    def parse_locations(self, html: str) -> list[ScrapedLocation]:
        soup = BeautifulSoup(html, "html.parser")
        locations: list[ScrapedLocation] = []

        for block in soup.select("article, li, div, section"):
            text = " ".join(block.stripped_strings)
            if len(text) < 20:
                continue
            if not any(keyword in text.lower() for keyword in ["care", "nursing", "rehabilitation", "assisted", "memory"]):
                continue

            location_name = self._first_match(block, ["h1", "h2", "h3", "h4", "strong", "b"]) or "Location"
            address_text = self._extract_address(block)
            location = ScrapedLocation(
                source_name=str(location_name).strip(),
                name=str(location_name).strip(),
                address=address_text.get("address", ""),
                city=address_text.get("city", ""),
                state=address_text.get("state", ""),
                zip_code=address_text.get("zip_code", ""),
                care_offerings=self._care_offerings(block),
                raw={
                    "name": str(location_name).strip(),
                    "address": address_text.get("address", ""),
                    "city": address_text.get("city", ""),
                    "state": address_text.get("state", ""),
                    "zip": address_text.get("zip_code", ""),
                    "zip_code": address_text.get("zip_code", ""),
                    "care_offerings": self._care_offerings(block),
                    "text": text,
                },
            )
            if location.name:
                locations.append(location)

        if not locations:
            locations = self._fallback_parse_from_text(soup.get_text(" ", strip=True))

        unique: dict[str, ScrapedLocation] = {}
        for location in locations:
            key = (location.name, location.address, location.city, location.state, location.zip_code)
            unique[key] = location
        return list(unique.values())

    @staticmethod
    def _first_match(block: Any, selectors: list[str]) -> str:
        for selector in selectors:
            node = block.select_one(selector)
            if node and node.get_text(strip=True):
                return node.get_text(" ", strip=True)
        return ""

    @staticmethod
    def _extract_address(block: Any) -> dict[str, str]:
        text = " ".join(block.stripped_strings)
        pieces = [part.strip() for part in re.split(r"[,\n]+", text) if part.strip()]
        if len(pieces) >= 3:
            city = pieces[-2].split()[-1] if len(pieces[-2].split()) > 1 else pieces[-2]
            state = pieces[-2].split()[-2] if len(pieces[-2].split()) > 1 else ""
            zip_code = pieces[-1].split()[-1] if pieces[-1].split() else ""
            address = ", ".join(pieces[:-2])
            return {"address": address, "city": city, "state": state, "zip_code": zip_code}
        return {"address": "", "city": "", "state": "", "zip_code": ""}

    @staticmethod
    def _care_offerings(block: Any) -> list[str]:
        text = " ".join(block.stripped_strings).lower()
        offers = []
        keywords = [
            "skilled nursing",
            "rehabilitation",
            "assisted living",
            "memory care",
            "short-term rehab",
            "long-term care",
        ]
        for keyword in keywords:
            if keyword in text:
                offers.append(keyword.title())
        return offers or ["General Care"]

    @staticmethod
    def _fallback_parse_from_text(raw_text: str) -> list[ScrapedLocation]:
        if not raw_text:
            return []
        text = raw_text.strip()
        location = ScrapedLocation(
            source_name="Bellhaven Location",
            name="Bellhaven Location",
            address="",
            city="",
            state="",
            zip_code="",
            care_offerings=["General Care"],
            raw={
                "name": "Bellhaven Location",
                "address": "",
                "city": "",
                "state": "",
                "zip": "",
                "zip_code": "",
                "care_offerings": ["General Care"],
                "raw_text": text[:500],
            },
        )
        return [location]


if __name__ == "__main__":
    scraper = BellhavenScraper("https://analyst-assessment-production.up.railway.app")
    print(scraper.parse_locations(scraper.fetch_page())[:3])
