// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title CertificateRegistry
 * @notice Stores document fingerprints, not certificate files or personal data.
 * @dev ISSUER_ROLE can issue/revoke. DEFAULT_ADMIN_ROLE manages issuer permissions.
 */
contract CertificateRegistry is AccessControl, ReentrancyGuard {
    bytes32 public constant ISSUER_ROLE = keccak256("ISSUER_ROLE");

    struct Certificate {
        bytes32 documentHash; // SHA-256 digest of the exact uploaded bytes
        address issuer;
        uint64 issuedAt;
        uint64 revokedAt;
        bool revoked;
    }

    mapping(bytes32 => Certificate) private certificates;
    mapping(bytes32 => bool) public certificateExists;
    mapping(bytes32 => bytes32) public certificateIdByDocumentHash;

    event CertificateIssued(
        bytes32 indexed certificateId,
        bytes32 indexed documentHash,
        address indexed issuer,
        uint256 issuedAt
    );
    event CertificateRevoked(
        bytes32 indexed certificateId,
        bytes32 indexed documentHash,
        address indexed revoker,
        uint256 revokedAt
    );

    error InvalidCertificateId();
    error InvalidDocumentHash();
    error CertificateAlreadyExists();
    error DocumentHashAlreadyIssued();
    error CertificateNotFound();
    error CertificateAlreadyRevoked();

    constructor(address initialAdmin) {
        require(initialAdmin != address(0), "Admin cannot be zero");
        _grantRole(DEFAULT_ADMIN_ROLE, initialAdmin);
        _grantRole(ISSUER_ROLE, initialAdmin);
    }

    /// @notice Give an account permission to issue and revoke certificates.
    function addIssuer(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(account != address(0), "Issuer cannot be zero");
        grantRole(ISSUER_ROLE, account);
    }

    /// @notice Remove an issuer's permission. Does not alter past certificates.
    function removeIssuer(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        revokeRole(ISSUER_ROLE, account);
    }

    function issueCertificate(
        bytes32 certificateId,
        bytes32 documentHash
    ) external onlyRole(ISSUER_ROLE) nonReentrant {
        if (certificateId == bytes32(0)) revert InvalidCertificateId();
        if (documentHash == bytes32(0)) revert InvalidDocumentHash();
        if (certificateExists[certificateId]) revert CertificateAlreadyExists();
        if (certificateIdByDocumentHash[documentHash] != bytes32(0)) {
            revert DocumentHashAlreadyIssued();
        }

        certificates[certificateId] = Certificate({
            documentHash: documentHash,
            issuer: msg.sender,
            issuedAt: uint64(block.timestamp),
            revokedAt: 0,
            revoked: false
        });
        certificateExists[certificateId] = true;
        certificateIdByDocumentHash[documentHash] = certificateId;

        emit CertificateIssued(certificateId, documentHash, msg.sender, block.timestamp);
    }

    function revokeCertificate(
        bytes32 certificateId
    ) external onlyRole(ISSUER_ROLE) nonReentrant {
        if (!certificateExists[certificateId]) revert CertificateNotFound();
        Certificate storage cert = certificates[certificateId];
        if (cert.revoked) revert CertificateAlreadyRevoked();

        cert.revoked = true;
        cert.revokedAt = uint64(block.timestamp);
        emit CertificateRevoked(certificateId, cert.documentHash, msg.sender, block.timestamp);
    }

    /// @notice Returns certificate record. A zero hash indicates no record.
    function getCertificate(
        bytes32 certificateId
    ) external view returns (
        bytes32 documentHash,
        address issuer,
        uint64 issuedAt,
        uint64 revokedAt,
        bool revoked
    ) {
        if (!certificateExists[certificateId]) revert CertificateNotFound();
        Certificate memory cert = certificates[certificateId];
        return (cert.documentHash, cert.issuer, cert.issuedAt, cert.revokedAt, cert.revoked);
    }

    function verifyCertificate(
        bytes32 certificateId,
        bytes32 suppliedDocumentHash
    ) external view returns (bool exists, bool hashMatches, bool active) {
        if (!certificateExists[certificateId]) return (false, false, false);
        Certificate memory cert = certificates[certificateId];
        bool matches = cert.documentHash == suppliedDocumentHash;
        return (true, matches, matches && !cert.revoked);
    }
}
