"""app/api/v1/news/__init__.py — News intelligence API."""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id, require_admin
from app.database import get_db
from app.models.news import NewsEvent, NewsCategory, NewsSeverity

logger = logging.getLogger(__name__)
router = APIRouter()


class NewsEventResponse(BaseModel):
    id: uuid.UUID
    title: str
    category: str
    severity: str
    severity_score: float
    source: Optional[str]
    published_at: Optional[datetime]
    zone_id: Optional[uuid.UUID]
    content_snippet: Optional[str]


@router.get("/", response_model=List[NewsEventResponse], summary="List news/safety events")
async def list_news(
    zone_id: Optional[uuid.UUID] = Query(None),
    category: Optional[NewsCategory] = Query(None),
    severity: Optional[NewsSeverity] = Query(None),
    hours: int = Query(24, description="Look back N hours"),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user_id),
) -> List[NewsEventResponse]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = select(NewsEvent).where(NewsEvent.published_at >= cutoff)
    if zone_id:
        q = q.where(NewsEvent.zone_id == zone_id)
    if category:
        q = q.where(NewsEvent.category == category)
    if severity:
        q = q.where(NewsEvent.severity == severity)
    q = q.order_by(NewsEvent.severity_score.desc(), NewsEvent.published_at.desc()).limit(limit)
    result = await db.scalars(q)
    return [_to_response(n) for n in result.all()]


@router.post("/ingest", summary="Trigger news ingestion from configured sources (admin)")
async def ingest_news(
    zone_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    from app.config import settings
    from app.services.risk.news_provider import NewsProvider
    from app.models.zone import GeographicZone

    provider = NewsProvider(sources=getattr(settings, "NEWS_SOURCES", None) or [])
    items = await provider.fetch_all()

    saved = 0
    for item in items:
        event = NewsEvent(
            zone_id=zone_id,
            title=item.title,
            content_snippet=item.content_snippet,
            source=item.source,
            source_url=item.url,
            published_at=item.published_at,
            category=item.category,
            severity=item.severity,
            severity_score=item.severity_score,
            raw_metadata=item.raw_metadata,
        )
        db.add(event)
        saved += 1

    await db.commit()
    return {"ingested": saved, "from_sources": len(provider._sources)}


@router.get("/{news_id}", response_model=NewsEventResponse, summary="Get a single news event")
async def get_news_event(
    news_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user_id),
) -> NewsEventResponse:
    event = await db.get(NewsEvent, news_id)
    if not event:
        raise HTTPException(status_code=404, detail="News event not found")
    return _to_response(event)


def _to_response(n: NewsEvent) -> NewsEventResponse:
    return NewsEventResponse(
        id=n.id, title=n.title, category=n.category,
        severity=n.severity, severity_score=n.severity_score,
        source=n.source, published_at=n.published_at,
        zone_id=n.zone_id, content_snippet=n.content_snippet,
    )
