// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TouristIdentity
 * @notice Blockchain identity registry for the Edge-Based Tourist Safety System.
 *
 * Security architecture:
 *   - Sensitive personal data (passport, medical) is stored ONLY in PostgreSQL (encrypted).
 *   - Only the SHA-256 identity hash (computed from canonical encrypted identity) is stored on-chain.
 *   - Emergency access is granted/revoked per SOS event.
 *   - Only the contract owner (backend deployer) can register identities.
 *   - Only assigned, verified responders may be granted access.
 */
contract TouristIdentity {
    // ── Owner (backend deployer) ─────────────────────────────────────────
    address public owner;

    // ── Identity storage ─────────────────────────────────────────────────
    struct Identity {
        bytes32 identityHash;    // SHA-256 of canonical encrypted identity
        uint256 registeredAt;
        bool exists;
    }

    // userId (bytes32, keccak of UUID string) → Identity
    mapping(bytes32 => Identity) private identities;

    // ── Emergency access ─────────────────────────────────────────────────
    struct AccessGrant {
        address responder;
        bytes32 sosEventId;
        uint256 grantedAt;
        uint256 revokedAt;
        bool isActive;
    }

    // userId → list of access grants
    mapping(bytes32 => AccessGrant[]) private accessGrants;

    // ── Events ────────────────────────────────────────────────────────────
    event IdentityRegistered(bytes32 indexed userId, bytes32 identityHash, uint256 timestamp);
    event AccessGranted(bytes32 indexed userId, address indexed responder, bytes32 sosEventId, uint256 timestamp);
    event AccessRevoked(bytes32 indexed userId, address indexed responder, bytes32 sosEventId, uint256 timestamp);

    // ── Modifiers ─────────────────────────────────────────────────────────
    modifier onlyOwner() {
        require(msg.sender == owner, "TouristIdentity: caller is not owner");
        _;
    }

    modifier identityExists(bytes32 userId) {
        require(identities[userId].exists, "TouristIdentity: identity not registered");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    // ── Identity management ───────────────────────────────────────────────

    /**
     * @notice Register a tourist's identity hash on-chain.
     * @param userId keccak256 of the user's UUID string
     * @param identityHash SHA-256 of canonical encrypted identity blob
     */
    function registerIdentity(bytes32 userId, bytes32 identityHash) external onlyOwner {
        require(!identities[userId].exists, "TouristIdentity: already registered");
        identities[userId] = Identity({
            identityHash: identityHash,
            registeredAt: block.timestamp,
            exists: true
        });
        emit IdentityRegistered(userId, identityHash, block.timestamp);
    }

    /**
     * @notice Look up the identity hash for a user.
     */
    function getIdentityHash(bytes32 userId)
        external
        view
        identityExists(userId)
        returns (bytes32 hash, uint256 registeredAt)
    {
        Identity storage id = identities[userId];
        return (id.identityHash, id.registeredAt);
    }

    /**
     * @notice Check whether an identity is registered.
     */
    function isRegistered(bytes32 userId) external view returns (bool) {
        return identities[userId].exists;
    }

    // ── Emergency access management ───────────────────────────────────────

    /**
     * @notice Grant emergency access to a responder for a specific SOS event.
     * @param userId Tourist's user ID (keccak256 of UUID)
     * @param responder Responder's wallet address
     * @param sosEventId SOS event identifier (keccak256 of UUID)
     */
    function grantEmergencyAccess(
        bytes32 userId,
        address responder,
        bytes32 sosEventId
    ) external onlyOwner identityExists(userId) {
        require(responder != address(0), "TouristIdentity: invalid responder address");

        accessGrants[userId].push(AccessGrant({
            responder: responder,
            sosEventId: sosEventId,
            grantedAt: block.timestamp,
            revokedAt: 0,
            isActive: true
        }));

        emit AccessGranted(userId, responder, sosEventId, block.timestamp);
    }

    /**
     * @notice Revoke emergency access for a specific SOS event.
     */
    function revokeEmergencyAccess(
        bytes32 userId,
        address responder,
        bytes32 sosEventId
    ) external onlyOwner identityExists(userId) {
        AccessGrant[] storage grants = accessGrants[userId];
        bool found = false;
        for (uint i = 0; i < grants.length; i++) {
            if (
                grants[i].responder == responder &&
                grants[i].sosEventId == sosEventId &&
                grants[i].isActive
            ) {
                grants[i].isActive = false;
                grants[i].revokedAt = block.timestamp;
                found = true;
                emit AccessRevoked(userId, responder, sosEventId, block.timestamp);
                break;
            }
        }
        require(found, "TouristIdentity: active grant not found");
    }

    /**
     * @notice Check whether a responder has active emergency access for a user.
     */
    function hasActiveAccess(
        bytes32 userId,
        address responder,
        bytes32 sosEventId
    ) external view returns (bool) {
        AccessGrant[] storage grants = accessGrants[userId];
        for (uint i = 0; i < grants.length; i++) {
            if (
                grants[i].responder == responder &&
                grants[i].sosEventId == sosEventId &&
                grants[i].isActive
            ) {
                return true;
            }
        }
        return false;
    }

    /**
     * @notice Transfer contract ownership (for key rotation).
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "TouristIdentity: invalid address");
        owner = newOwner;
    }
}
