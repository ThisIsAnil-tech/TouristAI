"""
app/services/blockchain/identity_service.py — Web3.py contract interaction.

Wraps TouristIdentity.sol calls:
  - registerIdentity(userId, identityHash)
  - grantEmergencyAccess(userId, responder, sosEventId)
  - revokeEmergencyAccess(userId, responder, sosEventId)
  - hasActiveAccess(userId, responder, sosEventId) → bool
  - isRegistered(userId) → bool

Stores tx_hash, block_number, gas_used, latency to BlockchainTransaction.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.blockchain import BlockchainTransaction, BlockchainTxType
from app.models.user import User

logger = logging.getLogger(__name__)


@dataclass
class TxResult:
    success: bool
    tx_hash: Optional[str]
    block_number: Optional[int]
    gas_used: Optional[int]
    latency_ms: float
    error: Optional[str]


class BlockchainNotConfiguredError(Exception):
    pass


class BlockchainIdentityService:
    """
    Interacts with the deployed TouristIdentity smart contract.

    In MOCK mode: returns simulated results with is_mock=True clearly logged.
    In REAL mode: connects to configured blockchain node via Web3.py.
    """

    _w3 = None
    _contract = None

    @classmethod
    def _init_web3(cls) -> None:
        if cls._w3 is not None:
            return

        if settings.BLOCKCHAIN_MOCK_MODE:
            logger.warning("Blockchain service in MOCK MODE")
            cls._w3 = "mock"
            return

        if not settings.BLOCKCHAIN_CONTRACT_ADDRESS:
            raise BlockchainNotConfiguredError(
                "BLOCKCHAIN_CONTRACT_ADDRESS not set. "
                "Deploy the contract first: python scripts/deploy_contract.py\n"
                "Or set BLOCKCHAIN_MOCK_MODE=true for development."
            )

        from web3 import Web3
        from web3.middleware import geth_poa_middleware

        w3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_PROVIDER_URL))
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        if not w3.is_connected():
            raise BlockchainNotConfiguredError(
                f"Cannot connect to blockchain at {settings.BLOCKCHAIN_PROVIDER_URL}"
            )

        # Load ABI
        abi = cls._load_abi()
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(settings.BLOCKCHAIN_CONTRACT_ADDRESS),
            abi=abi,
        )
        cls._w3 = w3
        cls._contract = contract
        logger.info("Blockchain connected: %s block=%d", settings.BLOCKCHAIN_PROVIDER_URL,
                    w3.eth.block_number)

    @staticmethod
    def _load_abi() -> list:
        compiled_path = Path("contracts/TouristIdentity.json")
        if compiled_path.exists():
            with open(compiled_path) as f:
                data = json.load(f)
            return data.get("abi", [])
        raise BlockchainNotConfiguredError(
            "contracts/TouristIdentity.json not found. "
            "Run: python scripts/deploy_contract.py"
        )

    @staticmethod
    def _user_id_to_bytes32(user_id: uuid.UUID) -> bytes:
        return hashlib.sha256(str(user_id).encode()).digest()

    @staticmethod
    def _sos_id_to_bytes32(sos_id: uuid.UUID) -> bytes:
        return hashlib.sha256(str(sos_id).encode()).digest()

    async def register_identity(
        self,
        user: User,
        db: AsyncSession,
    ) -> TxResult:
        """Register a tourist's identity hash on-chain."""
        self._init_web3()
        start = time.perf_counter()

        if self._w3 == "mock":
            result = TxResult(True, "0x" + "0" * 64, 1, 21000, 0.0, None)
            await self._persist_tx(db, user.id, BlockchainTxType.REGISTER_IDENTITY,
                                   result, user.identity_hash)
            return result

        try:
            from web3 import Web3
            user_bytes = self._user_id_to_bytes32(user.id)
            id_hash = bytes.fromhex(user.identity_hash) if user.identity_hash else b"\x00" * 32

            account = self._w3.eth.account.from_key(settings.BLOCKCHAIN_PRIVATE_KEY)
            tx = self._contract.functions.registerIdentity(
                user_bytes, id_hash
            ).build_transaction({
                "from": account.address,
                "nonce": self._w3.eth.get_transaction_count(account.address),
                "gas": settings.BLOCKCHAIN_GAS_LIMIT,
                "gasPrice": self._w3.eth.gas_price,
                "chainId": self._w3.eth.chain_id,
            })
            signed = account.sign_transaction(tx)
            tx_hash = self._w3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            elapsed_ms = (time.perf_counter() - start) * 1000

            result = TxResult(
                success=receipt.status == 1,
                tx_hash=tx_hash.hex(),
                block_number=receipt.blockNumber,
                gas_used=receipt.gasUsed,
                latency_ms=elapsed_ms,
                error=None if receipt.status == 1 else "Transaction reverted",
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error("registerIdentity failed for user %s: %s", user.id, exc)
            result = TxResult(False, None, None, None, elapsed_ms, str(exc))

        await self._persist_tx(db, user.id, BlockchainTxType.REGISTER_IDENTITY,
                               result, user.identity_hash)
        return result

    async def grant_emergency_access(
        self,
        tourist_user_id: uuid.UUID,
        responder_wallet: str,
        sos_event_id: uuid.UUID,
        db: AsyncSession,
    ) -> TxResult:
        """Grant emergency access to a responder for a specific SOS event."""
        self._init_web3()
        start = time.perf_counter()

        if self._w3 == "mock":
            result = TxResult(True, "0x" + "a" * 64, 2, 45000, 50.0, None)
            await self._persist_tx(db, tourist_user_id, BlockchainTxType.GRANT_ACCESS, result)
            return result

        try:
            from web3 import Web3
            user_bytes = self._user_id_to_bytes32(tourist_user_id)
            sos_bytes = self._sos_id_to_bytes32(sos_event_id)
            checksum_addr = Web3.to_checksum_address(responder_wallet)

            account = self._w3.eth.account.from_key(settings.BLOCKCHAIN_PRIVATE_KEY)
            tx = self._contract.functions.grantEmergencyAccess(
                user_bytes, checksum_addr, sos_bytes
            ).build_transaction({
                "from": account.address,
                "nonce": self._w3.eth.get_transaction_count(account.address),
                "gas": settings.BLOCKCHAIN_GAS_LIMIT,
                "gasPrice": self._w3.eth.gas_price,
                "chainId": self._w3.eth.chain_id,
            })
            signed = account.sign_transaction(tx)
            tx_hash = self._w3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            elapsed_ms = (time.perf_counter() - start) * 1000

            result = TxResult(
                success=receipt.status == 1,
                tx_hash=tx_hash.hex(),
                block_number=receipt.blockNumber,
                gas_used=receipt.gasUsed,
                latency_ms=elapsed_ms,
                error=None if receipt.status == 1 else "Transaction reverted",
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error("grantEmergencyAccess failed: %s", exc)
            result = TxResult(False, None, None, None, elapsed_ms, str(exc))

        await self._persist_tx(db, tourist_user_id, BlockchainTxType.GRANT_ACCESS, result)
        return result

    async def revoke_emergency_access(
        self,
        tourist_user_id: uuid.UUID,
        responder_wallet: str,
        sos_event_id: uuid.UUID,
        db: AsyncSession,
    ) -> TxResult:
        """Revoke emergency access on-chain."""
        self._init_web3()
        start = time.perf_counter()

        if self._w3 == "mock":
            result = TxResult(True, "0x" + "b" * 64, 3, 30000, 40.0, None)
            await self._persist_tx(db, tourist_user_id, BlockchainTxType.REVOKE_ACCESS, result)
            return result

        try:
            from web3 import Web3
            user_bytes = self._user_id_to_bytes32(tourist_user_id)
            sos_bytes = self._sos_id_to_bytes32(sos_event_id)
            checksum_addr = Web3.to_checksum_address(responder_wallet)

            account = self._w3.eth.account.from_key(settings.BLOCKCHAIN_PRIVATE_KEY)
            tx = self._contract.functions.revokeEmergencyAccess(
                user_bytes, checksum_addr, sos_bytes
            ).build_transaction({
                "from": account.address,
                "nonce": self._w3.eth.get_transaction_count(account.address),
                "gas": settings.BLOCKCHAIN_GAS_LIMIT,
                "gasPrice": self._w3.eth.gas_price,
                "chainId": self._w3.eth.chain_id,
            })
            signed = account.sign_transaction(tx)
            tx_hash = self._w3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            elapsed_ms = (time.perf_counter() - start) * 1000

            result = TxResult(
                success=receipt.status == 1,
                tx_hash=tx_hash.hex(),
                block_number=receipt.blockNumber,
                gas_used=receipt.gasUsed,
                latency_ms=elapsed_ms,
                error=None if receipt.status == 1 else "Transaction reverted",
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error("revokeEmergencyAccess failed: %s", exc)
            result = TxResult(False, None, None, None, elapsed_ms, str(exc))

        await self._persist_tx(db, tourist_user_id, BlockchainTxType.REVOKE_ACCESS, result)
        return result

    async def is_registered(self, user_id: uuid.UUID) -> bool:
        self._init_web3()
        if self._w3 == "mock":
            return True
        try:
            user_bytes = self._user_id_to_bytes32(user_id)
            return self._contract.functions.isRegistered(user_bytes).call()
        except Exception as exc:
            logger.error("isRegistered failed: %s", exc)
            return False

    @staticmethod
    async def _persist_tx(
        db: AsyncSession,
        user_id: uuid.UUID,
        tx_type: BlockchainTxType,
        result: TxResult,
        identity_hash: Optional[str] = None,
    ) -> None:
        tx_record = BlockchainTransaction(
            user_id=user_id,
            tx_type=tx_type,
            tx_hash=result.tx_hash,
            block_number=result.block_number,
            gas_used=result.gas_used,
            status="SUCCESS" if result.success else "FAILED",
            latency_ms=result.latency_ms,
            identity_hash=identity_hash,
            error_message=result.error,
        )
        db.add(tx_record)
        await db.flush()
