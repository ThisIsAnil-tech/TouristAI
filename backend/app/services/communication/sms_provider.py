"""
app/services/communication/sms_provider.py — SMS delivery via Twilio or AWS SNS.

Real HTTP calls using the configured provider. Never silently returns success.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SmsResult:
    success: bool
    provider_message_id: Optional[str]
    error: Optional[str]


class SmsProviderNotConfiguredError(Exception):
    pass


class TwilioSmsProvider:
    """Real Twilio SMS delivery."""

    def __init__(self) -> None:
        self._sid = settings.SMS_ACCOUNT_SID
        self._token = settings.SMS_AUTH_TOKEN
        self._from = settings.SMS_FROM_NUMBER
        self._mock = settings.SMS_MOCK_MODE

    async def send_sms(self, to: str, body: str) -> SmsResult:
        if self._mock:
            logger.warning("SMS MOCK MODE — not sending real SMS to %s", to)
            return SmsResult(True, "mock-sid-001", None)

        if not all([self._sid, self._token, self._from]):
            raise SmsProviderNotConfiguredError(
                "Twilio credentials not configured (SMS_ACCOUNT_SID, SMS_AUTH_TOKEN, SMS_FROM_NUMBER). "
                "Set SMS_MOCK_MODE=true for development."
            )

        try:
            from twilio.rest import Client
            client = Client(self._sid, self._token)
            message = client.messages.create(
                body=body[:1600],   # Twilio SMS length limit
                from_=self._from,
                to=to,
            )
            logger.info("SMS sent via Twilio: sid=%s to=%s", message.sid, to)
            return SmsResult(True, message.sid, None)
        except Exception as exc:
            logger.error("Twilio SMS failed to %s: %s", to, exc)
            return SmsResult(False, None, str(exc))


class AwsSnsSmsProvider:
    """AWS SNS SMS delivery."""

    def __init__(self) -> None:
        self._mock = settings.SMS_MOCK_MODE

    async def send_sms(self, to: str, body: str) -> SmsResult:
        if self._mock:
            logger.warning("SNS MOCK MODE — not sending real SMS to %s", to)
            return SmsResult(True, "mock-sns-001", None)

        try:
            import boto3
            client = boto3.client("sns")
            response = client.publish(
                PhoneNumber=to,
                Message=body[:1600],
                MessageAttributes={
                    "AWS.SNS.SMS.SMSType": {
                        "DataType": "String",
                        "StringValue": "Transactional",
                    }
                },
            )
            msg_id = response.get("MessageId")
            logger.info("SMS sent via AWS SNS: message_id=%s to=%s", msg_id, to)
            return SmsResult(True, msg_id, None)
        except Exception as exc:
            logger.error("AWS SNS SMS failed to %s: %s", to, exc)
            return SmsResult(False, None, str(exc))


def get_sms_provider():
    """Return the configured SMS provider instance."""
    provider = settings.SMS_PROVIDER.lower()
    if provider == "twilio":
        return TwilioSmsProvider()
    elif provider in ("sns", "aws_sns"):
        return AwsSnsSmsProvider()
    else:
        raise ValueError(f"Unknown SMS provider: {provider}")
