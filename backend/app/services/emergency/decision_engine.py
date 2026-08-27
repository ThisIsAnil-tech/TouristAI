"""
app/services/emergency/decision_engine.py — Emergency Decision Engine.

Patent requirements:
  - Audio distress ALONE can trigger SOS.
  - GPS anomaly ALONE can trigger SOS.
  - Do NOT require both simultaneously.
  - Confidence is evaluated against adaptive threshold.
  - Risk score influences the threshold.
  - All decisions are persisted.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio import AudioDetection
from app.models.gps import GpsReading
from app.models.sos import SosEvent, SosStatus, SosTrigger
from app.services.risk.adaptive_threshold import AdaptiveThresholdController

logger = logging.getLogger(__name__)


class DecisionReason(str, Enum):
    AUDIO_DISTRESS = "AUDIO_DISTRESS"
    GPS_ANOMALY = "GPS_ANOMALY"
    MANUAL = "MANUAL"
    COMBINED_AUDIO_GPS = "COMBINED_AUDIO_GPS"
    THRESHOLD_NOT_MET = "THRESHOLD_NOT_MET"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass
class DecisionInput:
    """All inputs the decision engine may receive."""
    user_id: uuid.UUID
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    zone_id: Optional[uuid.UUID] = None

    # Audio evidence
    audio_detection_id: Optional[uuid.UUID] = None
    audio_confidence: Optional[float] = None
    audio_is_distress: Optional[bool] = None

    # GPS evidence
    gps_reading_id: Optional[uuid.UUID] = None
    gps_is_anomalous: Optional[bool] = None
    gps_consecutive_anomalies: Optional[int] = None

    # Risk context
    risk_score_id: Optional[uuid.UUID] = None
    risk_score: Optional[float] = None

    # Manual trigger
    is_manual: bool = False
    idempotency_key: Optional[str] = None


@dataclass
class DecisionResult:
    """Output of the emergency decision engine."""
    should_trigger_sos: bool
    trigger: Optional[SosTrigger]
    reason: DecisionReason
    confidence: Optional[float]
    adaptive_threshold_used: Optional[float]
    risk_score: Optional[float]
    details: str
    sos_event_id: Optional[uuid.UUID] = None


class DecisionPolicy:
    """
    Configurable decision policy.

    Controls:
      - minimum GPS consecutive anomalies before SOS (from settings)
      - whether to require blockchain verification (optional)
    """

    def __init__(
        self,
        min_gps_anomalies: int = 3,
    ) -> None:
        self.min_gps_anomalies = min_gps_anomalies


class EmergencyDecisionEngine:
    """
    The core emergency decision engine.

    Evaluates incoming evidence and decides whether to create an SOS event.

    Decision logic (from patent):
      1. Manual SOS → always trigger.
      2. Audio distress with confidence ≥ adaptive_threshold → trigger.
      3. GPS anomaly with consecutive_count ≥ limit → trigger.
      4. Both audio + GPS (combined) → trigger with COMBINED reason.
      5. Evidence insufficient → no SOS.
    """

    def __init__(
        self,
        policy: Optional[DecisionPolicy] = None,
        threshold_controller: Optional[AdaptiveThresholdController] = None,
    ) -> None:
        self.policy = policy or DecisionPolicy()
        self._threshold_ctrl = threshold_controller or AdaptiveThresholdController()

    async def evaluate(
        self,
        inp: DecisionInput,
        db: AsyncSession,
    ) -> DecisionResult:
        """
        Evaluate evidence and optionally create an SOS event.

        Args:
            inp: All available evidence.
            db: Async database session.

        Returns:
            DecisionResult describing the decision and any created SOS event.
        """
        # ── Idempotency check ──────────────────────────────────────────────
        if inp.idempotency_key:
            from sqlalchemy import select
            existing = await db.scalar(
                select(SosEvent).where(SosEvent.idempotency_key == inp.idempotency_key)
            )
            if existing:
                logger.info("Idempotent SOS request; returning existing SOS %s", existing.id)
                return DecisionResult(
                    should_trigger_sos=True,
                    trigger=existing.trigger,
                    reason=DecisionReason.MANUAL,
                    confidence=inp.audio_confidence,
                    adaptive_threshold_used=None,
                    risk_score=inp.risk_score,
                    details="Idempotent — SOS already exists",
                    sos_event_id=existing.id,
                )

        # ── 1. Manual trigger ──────────────────────────────────────────────
        if inp.is_manual:
            return await self._create_sos(
                inp, db,
                trigger=SosTrigger.MANUAL,
                reason=DecisionReason.MANUAL,
                confidence=None,
                threshold=None,
                details="Manual SOS triggered by user",
            )

        # ── 2. Compute adaptive threshold ──────────────────────────────────
        risk_score = inp.risk_score or 5.0  # Default mid-range if unknown
        threshold_result = self._threshold_ctrl.calculate(risk_score)
        adaptive_threshold = threshold_result.adaptive_threshold

        # ── 3. Evaluate audio evidence ─────────────────────────────────────
        audio_triggers = (
            inp.audio_is_distress is True
            and inp.audio_confidence is not None
            and inp.audio_confidence >= adaptive_threshold
        )

        # ── 4. Evaluate GPS evidence ───────────────────────────────────────
        gps_triggers = (
            inp.gps_is_anomalous is True
            and (inp.gps_consecutive_anomalies or 0) >= self.policy.min_gps_anomalies
        )

        # ── 5. Decision ────────────────────────────────────────────────────
        if audio_triggers and gps_triggers:
            return await self._create_sos(
                inp, db,
                trigger=SosTrigger.COMBINED,
                reason=DecisionReason.COMBINED_AUDIO_GPS,
                confidence=inp.audio_confidence,
                threshold=adaptive_threshold,
                details=(
                    f"Combined: audio confidence {inp.audio_confidence:.3f} "
                    f">= threshold {adaptive_threshold:.3f} "
                    f"AND GPS {inp.gps_consecutive_anomalies} anomalies"
                ),
            )

        if audio_triggers:
            return await self._create_sos(
                inp, db,
                trigger=SosTrigger.AUDIO_DISTRESS,
                reason=DecisionReason.AUDIO_DISTRESS,
                confidence=inp.audio_confidence,
                threshold=adaptive_threshold,
                details=(
                    f"Audio distress: confidence {inp.audio_confidence:.3f} "
                    f">= adaptive threshold {adaptive_threshold:.3f} "
                    f"(risk={risk_score:.1f})"
                ),
            )

        if gps_triggers:
            return await self._create_sos(
                inp, db,
                trigger=SosTrigger.GPS_ANOMALY,
                reason=DecisionReason.GPS_ANOMALY,
                confidence=None,
                threshold=adaptive_threshold,
                details=(
                    f"GPS anomaly: {inp.gps_consecutive_anomalies} consecutive "
                    f"anomalies >= {self.policy.min_gps_anomalies} limit"
                ),
            )

        # No trigger
        audio_reason = ""
        if inp.audio_confidence is not None:
            audio_reason = (
                f"Audio confidence {inp.audio_confidence:.3f} "
                f"< threshold {adaptive_threshold:.3f}"
            )
        gps_reason = ""
        if inp.gps_is_anomalous:
            gps_reason = (
                f"GPS anomalies {inp.gps_consecutive_anomalies} "
                f"< limit {self.policy.min_gps_anomalies}"
            )

        return DecisionResult(
            should_trigger_sos=False,
            trigger=None,
            reason=DecisionReason.THRESHOLD_NOT_MET,
            confidence=inp.audio_confidence,
            adaptive_threshold_used=adaptive_threshold,
            risk_score=risk_score,
            details=" | ".join(filter(None, [audio_reason, gps_reason])) or "No distress evidence",
        )

    async def _create_sos(
        self,
        inp: DecisionInput,
        db: AsyncSession,
        trigger: SosTrigger,
        reason: DecisionReason,
        confidence: Optional[float],
        threshold: Optional[float],
        details: str,
    ) -> DecisionResult:
        """Persist an SOS event and return the decision result."""
        now = datetime.now(timezone.utc)

        sos = SosEvent(
            user_id=inp.user_id,
            trigger=trigger,
            status=SosStatus.ACTIVE,
            audio_detection_id=inp.audio_detection_id,
            gps_reading_id=inp.gps_reading_id,
            risk_score_id=inp.risk_score_id,
            decision_reason=details,
            confidence=confidence,
            adaptive_threshold=threshold,
            risk_score_at_trigger=inp.risk_score,
            latitude=inp.latitude,
            longitude=inp.longitude,
            zone_id=inp.zone_id,
            triggered_at=now,
            idempotency_key=inp.idempotency_key,
        )
        db.add(sos)
        await db.flush()

        logger.warning(
            "SOS TRIGGERED: user=%s trigger=%s reason=%s sos_id=%s",
            inp.user_id, trigger, reason, sos.id
        )

        return DecisionResult(
            should_trigger_sos=True,
            trigger=trigger,
            reason=reason,
            confidence=confidence,
            adaptive_threshold_used=threshold,
            risk_score=inp.risk_score,
            details=details,
            sos_event_id=sos.id,
        )
