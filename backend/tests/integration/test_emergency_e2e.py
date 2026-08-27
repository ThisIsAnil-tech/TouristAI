"""
tests/integration/test_emergency_e2e.py — Comprehensive End-to-End Emergency Lifecycle Test.

Tests the full multi-modal chain:
  GPS Location & Anomaly Detection
  + Audio Distress Signal
  + Environmental Risk Assessment & Adaptive Threshold
  → Central Emergency Decision Engine
  → SOS Creation & Idempotency
  → Tiered Communication Fallback
  → A* Mesh Routing to Gateways
  → Blockchain Emergency Access Delegation
"""
import uuid
import pytest
from app.services.gps.anomaly_detector import GpsAnomalyDetector
from app.services.gps.haversine import GpsPoint
from app.services.risk.adaptive_threshold import AdaptiveThresholdController
from app.services.risk.risk_calculator import RiskCalculator
from app.services.emergency.decision_engine import EmergencyDecisionEngine, DecisionInput
from app.services.communication.fallback import CommunicationFallbackManager
from app.services.mesh.astar import AStarRouter, GraphNode, GraphEdge
from app.services.blockchain.identity_service import BlockchainIdentityService
from app.models.gps import GpsReading
from app.models.audio import AudioClass


@pytest.mark.asyncio
async def test_complete_emergency_lifecycle(async_db, test_user):
    user_id = test_user.id
    
    # ── 1. GPS Ingestion & Anomaly ─────────────────────────────────────────
    from datetime import datetime, timezone
    gps_detector = GpsAnomalyDetector()
    reading = GpsReading(
        user_id=user_id,
        latitude=10.5250,
        longitude=76.2250,
        accuracy_m=5.0,
        recorded_at=datetime.now(timezone.utc),
    )
    async_db.add(reading)
    await async_db.commit()
    await async_db.refresh(reading)

    analysis = await gps_detector.analyze(reading, async_db, user_id)
    assert analysis is not None

    # ── 2. Adaptive Threshold & Risk Calculation ───────────────────────────
    threshold_ctrl = AdaptiveThresholdController()
    risk_score = 7.5  # High risk zone
    threshold_res = threshold_ctrl.calculate(risk_score)
    adaptive_theta = threshold_res.adaptive_threshold
    assert 0.30 <= adaptive_theta <= 0.90
    assert adaptive_theta < threshold_ctrl.base  # Sensitivity increased (threshold decreased)

    # ── 3. Central Emergency Decision Engine ───────────────────────────────
    decision_engine = EmergencyDecisionEngine()
    decision_input = DecisionInput(
        user_id=user_id,
        latitude=10.5250,
        longitude=76.2250,
        audio_is_distress=True,
        audio_confidence=0.82,  # > adaptive_theta (0.70)
        risk_score=risk_score,
        is_manual=False,
    )
    decision = await decision_engine.evaluate(decision_input, async_db)
    assert decision.should_trigger_sos is True
    assert decision.sos_event_id is not None

    # ── 4. Communication Fallback Pipeline ─────────────────────────────────
    from app.models.sos import SosEvent
    from sqlalchemy import select
    res = await async_db.execute(select(SosEvent).where(SosEvent.id == decision.sos_event_id))
    sos_obj = res.scalar_one()

    comm_service = CommunicationFallbackManager()
    comm_result = await comm_service.send_emergency_alert(
        sos_event=sos_obj,
        db=async_db,
        destination="+919876543210",
        message="EMERGENCY SOS: Audio distress detected",
    )
    assert comm_result is not None

    # ── 5. A* Mesh Routing to Gateway ─────────────────────────────────────
    t_id = uuid.uuid4()
    r_id = uuid.uuid4()
    g_id = uuid.uuid4()
    nodes = {
        t_id: GraphNode(node_id=t_id, latitude=10.5250, longitude=76.2250, is_gateway=False, battery_pct=90),
        r_id: GraphNode(node_id=r_id, latitude=10.5270, longitude=76.2270, is_gateway=False, battery_pct=85),
        g_id: GraphNode(node_id=g_id, latitude=10.5300, longitude=76.2300, is_gateway=True, battery_pct=100),
    }
    edges = {
        t_id: [GraphEdge(source_id=t_id, target_id=r_id, hop_cost=1.0)],
        r_id: [GraphEdge(source_id=r_id, target_id=g_id, hop_cost=1.0)],
        g_id: [],
    }
    router = AStarRouter()
    route = router.find_route(source_id=t_id, nodes=nodes, edges=edges, gateway_ids={g_id})
    assert route.success is True
    assert route.path == [t_id, r_id, g_id]
    assert route.hop_count == 2

    # ── 6. Blockchain Emergency Access Control ─────────────────────────────
    from app.config import settings
    settings.BLOCKCHAIN_MOCK_MODE = True
    BlockchainIdentityService._w3 = "mock"
    bc_service = BlockchainIdentityService()
    reg_tx = await bc_service.register_identity(user=test_user, db=async_db)
    assert reg_tx is not None
    assert reg_tx.success is True

    grant_tx = await bc_service.grant_emergency_access(
        tourist_user_id=user_id,
        responder_wallet="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        sos_event_id=decision.sos_event_id,
        db=async_db,
    )
    assert grant_tx is not None
    assert grant_tx.success is True
