"""app/api/v1/mesh/__init__.py — Mesh network API endpoints."""
from __future__ import annotations

import uuid
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id, require_admin
from app.database import get_db
from app.models.mesh import MeshNode, MeshEdge, MeshPacket, MeshNodeType
from app.services.mesh.routing import MeshRoutingService

logger = logging.getLogger(__name__)
router = APIRouter()
_routing_service = MeshRoutingService()


class MeshNodeCreate(BaseModel):
    device_id: str
    node_type: MeshNodeType = MeshNodeType.TOURIST_DEVICE
    is_gateway: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    battery_pct: Optional[int] = None


class MeshNodeResponse(BaseModel):
    id: uuid.UUID
    device_id: str
    node_type: str
    is_gateway: bool
    is_active: bool
    latitude: Optional[float]
    longitude: Optional[float]
    battery_pct: Optional[int]
    last_seen_at: Optional[datetime]


class MeshEdgeCreate(BaseModel):
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    hop_cost: float = 1.0
    signal_quality: Optional[float] = None
    link_reliability: Optional[float] = None


@router.get("/nodes", response_model=List[MeshNodeResponse], summary="List all active mesh nodes")
async def list_nodes(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user_id),
) -> List[MeshNodeResponse]:
    result = await db.scalars(select(MeshNode).where(MeshNode.is_active == True).limit(200))
    return [_node_to_response(n) for n in result.all()]


@router.post("/nodes", response_model=MeshNodeResponse, status_code=status.HTTP_201_CREATED,
             summary="Register a mesh node")
async def register_node(
    body: MeshNodeCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user_id),
) -> MeshNodeResponse:
    # Check for duplicate device_id
    existing = await db.scalar(select(MeshNode).where(MeshNode.device_id == body.device_id))
    if existing:
        # Update heartbeat instead
        from datetime import timezone
        existing.last_seen_at = datetime.now(timezone.utc)
        if body.battery_pct is not None:
            existing.battery_pct = body.battery_pct
        if body.latitude is not None:
            existing.latitude = body.latitude
            existing.longitude = body.longitude
        await db.commit()
        await db.refresh(existing)
        return _node_to_response(existing)

    node = MeshNode(**body.model_dump())
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return _node_to_response(node)


@router.patch("/nodes/{node_id}/heartbeat", summary="Update node heartbeat")
async def node_heartbeat(
    node_id: uuid.UUID,
    battery_pct: Optional[int] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user_id),
):
    from datetime import timezone
    node = await db.get(MeshNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Mesh node not found")
    node.last_seen_at = datetime.now(timezone.utc)
    if battery_pct is not None:
        node.battery_pct = battery_pct
    if latitude is not None:
        node.latitude = latitude
        node.longitude = longitude
    await db.commit()
    return {"node_id": str(node_id), "last_seen_at": node.last_seen_at.isoformat()}


@router.post("/edges", summary="Register a mesh edge (link between nodes)")
async def register_edge(
    body: MeshEdgeCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    edge = MeshEdge(**body.model_dump())
    db.add(edge)
    await db.commit()
    await db.refresh(edge)
    return {"edge_id": str(edge.id), "source": str(body.source_node_id),
            "target": str(body.target_node_id)}


@router.get("/route/{source_node_id}", summary="Find best route from a node to any gateway (A*)")
async def find_route(
    source_node_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user_id),
):
    nodes, edges, gateway_ids = await _routing_service._load_graph(db)
    if not nodes:
        raise HTTPException(status_code=503, detail="No mesh nodes available")
    from app.services.mesh.astar import AStarRouter
    result = AStarRouter().find_route(source_node_id, nodes, edges, gateway_ids)
    return {
        "success": result.success,
        "hop_count": result.hop_count,
        "total_cost": result.total_cost,
        "route_quality": result.route_quality,
        "path": [str(n) for n in result.path],
        "gateway_id": str(result.gateway_id) if result.gateway_id else None,
        "details": result.details,
    }


@router.get("/stats", summary="Mesh network statistics")
async def mesh_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user_id)):
    return await _routing_service.get_graph_stats(db)


def _node_to_response(n: MeshNode) -> MeshNodeResponse:
    return MeshNodeResponse(
        id=n.id, device_id=n.device_id, node_type=n.node_type,
        is_gateway=n.is_gateway, is_active=n.is_active,
        latitude=n.latitude, longitude=n.longitude,
        battery_pct=n.battery_pct, last_seen_at=n.last_seen_at,
    )
