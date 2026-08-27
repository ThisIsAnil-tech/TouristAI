"""
app/services/risk/news_provider.py — News/safety intelligence collection.

Implements:
  - NewsProvider       — HTTP fetch + BeautifulSoup parsing
  - NewsClassifier     — Keyword-based event category classification
  - NewsSeverityScorer — Category + keyword severity scoring
  - NewsDeduplicator   — URL + title deduplication

Does NOT fabricate news. Real collection requires configured RSS/API sources.
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from app.models.news import NewsCategory, NewsSeverity

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    title: str
    url: Optional[str]
    source: Optional[str]
    published_at: Optional[datetime]
    content_snippet: Optional[str]
    category: NewsCategory
    severity: NewsSeverity
    severity_score: float   # 0.0 – 1.0
    raw_metadata: Optional[str] = None
    dedup_hash: str = ""

    def __post_init__(self) -> None:
        # Hash for deduplication
        key = f"{self.url or ''}{self.title}"
        self.dedup_hash = hashlib.sha256(key.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Keyword maps for classification
# ---------------------------------------------------------------------------
_CATEGORY_KEYWORDS: dict[NewsCategory, List[str]] = {
    NewsCategory.FLOOD: ["flood", "flooding", "inundation", "flash flood", "waterlogged"],
    NewsCategory.LANDSLIDE: ["landslide", "mudslide", "rockslide", "landfall"],
    NewsCategory.WILDLIFE: ["wildlife", "animal attack", "snake", "bear", "elephant", "crocodile", "tiger"],
    NewsCategory.CRIME: ["crime", "robbery", "assault", "murder", "kidnapping", "theft", "attack"],
    NewsCategory.ROAD_CLOSURE: ["road closed", "road closure", "highway blocked", "road block"],
    NewsCategory.FIRE: ["fire", "wildfire", "forest fire", "blaze", "burning"],
    NewsCategory.WEATHER_WARNING: ["storm", "cyclone", "typhoon", "hurricane", "tornado", "hail", "blizzard",
                                    "heavy rain", "weather warning", "red alert"],
    NewsCategory.CIVIL_UNREST: ["protest", "riot", "curfew", "unrest", "violence", "shutdown"],
    NewsCategory.ACCIDENT: ["accident", "crash", "collision", "explosion", "blast"],
    NewsCategory.MEDICAL: ["epidemic", "outbreak", "disease", "health alert", "quarantine"],
}

_SEVERITY_SCORES: dict[NewsSeverity, float] = {
    NewsSeverity.LOW: 0.2,
    NewsSeverity.MEDIUM: 0.5,
    NewsSeverity.HIGH: 0.75,
    NewsSeverity.CRITICAL: 0.95,
}

_HIGH_SEVERITY_KEYWORDS = {"critical", "emergency", "disaster", "fatal", "deaths", "killed",
                            "dangerous", "severe", "extreme", "red alert", "evacuate"}
_MEDIUM_SEVERITY_KEYWORDS = {"warning", "alert", "caution", "avoid", "reported", "incident"}


class NewsClassifier:
    """Classify a news headline/snippet into a safety category."""

    def classify(self, title: str, snippet: str = "") -> NewsCategory:
        text = (title + " " + snippet).lower()
        for category, keywords in _CATEGORY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return category
        return NewsCategory.OTHER

    def score_severity(self, title: str, snippet: str = "") -> tuple[NewsSeverity, float]:
        text = (title + " " + snippet).lower()
        if any(kw in text for kw in _HIGH_SEVERITY_KEYWORDS):
            severity = NewsSeverity.HIGH
            # Check for CRITICAL keywords
            if any(kw in text for kw in {"disaster", "fatal", "deaths", "killed", "red alert"}):
                severity = NewsSeverity.CRITICAL
        elif any(kw in text for kw in _MEDIUM_SEVERITY_KEYWORDS):
            severity = NewsSeverity.MEDIUM
        else:
            severity = NewsSeverity.LOW
        return severity, _SEVERITY_SCORES[severity]


class NewsDeduplicator:
    """Track seen news hashes to prevent duplicate storage."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def is_duplicate(self, item: NewsItem) -> bool:
        if item.dedup_hash in self._seen:
            return True
        self._seen.add(item.dedup_hash)
        return False

    def clear(self) -> None:
        self._seen.clear()


class NewsProvider:
    """
    Fetches and parses safety news from configured RSS/web sources.

    Does NOT fabricate news items. If no sources are configured,
    returns an empty list and logs a warning.
    """

    def __init__(self, sources: Optional[List[str]] = None) -> None:
        self._sources = sources or []
        self._classifier = NewsClassifier()
        self._dedup = NewsDeduplicator()

    async def fetch_all(self) -> List[NewsItem]:
        """Fetch news from all configured sources. Returns deduplicated list."""
        if not self._sources:
            logger.warning(
                "No news sources configured. "
                "Set NEWS_SOURCES in configuration to enable news intelligence."
            )
            return []

        all_items: List[NewsItem] = []
        async with httpx.AsyncClient(timeout=15) as client:
            for source_url in self._sources:
                try:
                    items = await self._fetch_source(client, source_url)
                    for item in items:
                        if not self._dedup.is_duplicate(item):
                            all_items.append(item)
                except Exception as exc:
                    logger.error("Failed to fetch news from %s: %s", source_url, exc)

        logger.info("Fetched %d news items from %d sources", len(all_items), len(self._sources))
        return all_items

    async def _fetch_source(self, client: httpx.AsyncClient, url: str) -> List[NewsItem]:
        """Fetch and parse a single RSS/HTML news source."""
        response = await client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "xml" in content_type or url.endswith(".xml") or url.endswith(".rss"):
            return self._parse_rss(response.text, source=url)
        else:
            return self._parse_html(response.text, source=url)

    def _parse_rss(self, content: str, source: str) -> List[NewsItem]:
        """Parse an RSS feed for safety-relevant items."""
        soup = BeautifulSoup(content, features="xml")
        items = []

        for entry in soup.find_all("item"):
            title = entry.find("title")
            link = entry.find("link")
            description = entry.find("description")
            pub_date = entry.find("pubDate")

            title_text = title.get_text(strip=True) if title else ""
            if not title_text:
                continue

            snippet = description.get_text(strip=True)[:500] if description else ""
            category = self._classifier.classify(title_text, snippet)
            severity, score = self._classifier.score_severity(title_text, snippet)

            pub_dt: Optional[datetime] = None
            if pub_date:
                try:
                    from email.utils import parsedate_to_datetime
                    pub_dt = parsedate_to_datetime(pub_date.get_text(strip=True))
                except Exception:
                    pass

            items.append(NewsItem(
                title=title_text[:1000],
                url=link.get_text(strip=True) if link else None,
                source=source,
                published_at=pub_dt,
                content_snippet=snippet,
                category=category,
                severity=severity,
                severity_score=score,
            ))

        return items

    def _parse_html(self, content: str, source: str) -> List[NewsItem]:
        """Parse a generic HTML news page — headline extraction."""
        soup = BeautifulSoup(content, "lxml")
        items = []

        # Try common headline selectors
        for tag in soup.find_all(["h1", "h2", "h3"], limit=30):
            text = tag.get_text(strip=True)
            if len(text) < 10:
                continue

            category = self._classifier.classify(text)
            if category == NewsCategory.OTHER:
                continue  # Skip non-safety headlines

            severity, score = self._classifier.score_severity(text)
            items.append(NewsItem(
                title=text[:1000],
                url=source,
                source=source,
                published_at=datetime.now(timezone.utc),
                content_snippet=None,
                category=category,
                severity=severity,
                severity_score=score,
            ))

        return items
