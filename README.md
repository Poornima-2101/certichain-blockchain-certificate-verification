# CertiChain — Blockchain Certificate Verification

A modular demo for issuing, verifying, and revoking certificate fingerprints on Ethereum Sepolia using Solidity, Web3.py, and Streamlit.

## Architecture

- `contracts/CertificateRegistry.sol`: role-protected contract with issue/revoke events.
- `scripts/compile_contract.py`: compiles Solidity using `py-solc-x` and OpenZeppelin imports.
- `scripts/deploy.py`: deploys to the configured chain.
- `certificate_app/crypto.py`: SHA-256, IDs, file validation.
- `certificate_app/chain.py`: Web3 provider, signing, contract calls, and event history.
- `app.py`: Streamlit interface for issue, verify, revoke, QR generation, and history.

The contract stores only a SHA-256 digest, a random certificate ID, issuer address, timestamps, and revocation status. It does not store certificate files or student details.

## Prerequisites

- Python 3.10+ (Python 3.11 or 3.12 recommended for package compatibility)
- Node.js and npm
- An Infura or Alchemy Sepolia RPC endpoint
- A dedicated test wallet and Sepolia test ETH
- Internet access for downloading dependencies and the Solidity compiler

## Windows setup (PowerShell)

Open PowerShell in the project directory.

1. Create and activate a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. Install the OpenZeppelin Solidity dependency:

   ```powershell
   npm init -y
   npm install @openzeppelin/contracts@5
   ```

3. Configure the RPC and wallet:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   Set `RPC_URL` to your Infura/Alchemy Sepolia HTTPS endpoint, `CHAIN_ID=11155111`, and `PRIVATE_KEY` to a dedicated test wallet's private key. Keep the private key only in the local `.env`; never commit it, paste it into source control, or use a wallet holding real assets. Obtain test ETH from a reputable Sepolia faucet.

4. Compile the contract:

   ```powershell
   python scripts/compile_contract.py
   ```

   The first compile downloads Solidity compiler 0.8.24. Ensure `node_modules/@openzeppelin/contracts` exists if compilation reports an import error.

5. Deploy to Sepolia:

   ```powershell
   python scripts/deploy.py
   ```

   Copy the printed contract address into `.env` as `CONTRACT_ADDRESS=0x...`. Confirm the deployment transaction and address on Sepolia Etherscan before using the app.

6. Run the interface:

   ```powershell
   streamlit run app.py
   ```

   Open the local URL Streamlit prints (normally `http://localhost:8501`).

## macOS/Linux setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
npm init -y
npm install @openzeppelin/contracts@5
cp .env.example .env
# Edit .env with RPC_URL, CHAIN_ID, PRIVATE_KEY.
python scripts/compile_contract.py
python scripts/deploy.py
# Add printed contract address to .env, then:
streamlit run app.py
```

## Using the app

1. **Issue certificate**: upload a PDF/JSON, generate a SHA-256 fingerprint, then issue it. The wallet configured in `.env` pays gas and must have `ISSUER_ROLE`.
2. **Verify certificate**: enter the full certificate ID and upload the original file, or paste its exact SHA-256 digest. A changed byte (including a PDF re-save) normally changes the hash.
3. **Revoke certificate**: enter its certificate ID. A wallet with `ISSUER_ROLE` is required.
4. **History**: query `CertificateIssued` and `CertificateRevoked` events from the configured contract.

The generated QR code contains a URL with a `cert_id` query parameter. For this local demo, the app displays the identifier but does not automatically trust a QR's contents. A public deployment should provide a stable public verification URL and implement safe parsing of QR input.

## Smart contract administration

The deploying account receives `DEFAULT_ADMIN_ROLE` and `ISSUER_ROLE`. To authorize another issuer, call `addIssuer(address)` from the admin account using a wallet client or a dedicated admin script. The UI deliberately does not provide unrestricted issuer administration.

## Important limitations and security notes

- **Not audited / not production certified.** Have the contract independently reviewed before handling institutional records.
- Use a separate test wallet, minimum permissions, RPC endpoint restrictions where available, and secret management in production.
- Never put personal data, grades, names, or certificate contents on-chain.
- Hashes prove byte-level integrity, not that the certificate was legitimately awarded or that its claims are true.
- A SHA-256 hash of a predictable document may be susceptible to guessing. For sensitive certificates, design a privacy-preserving commitment scheme and review it with a security professional.
- Revocation is permanent in this contract; reissue a corrected certificate with a new ID/hash.
- Event history may require multiple RPC requests. Large-scale production history should use an indexed event service.
- The app signs transactions server-side with `PRIVATE_KEY`. Do not expose it to users or deploy this configuration as a public multi-user service. For production, use a wallet-signing flow, HSM/KMS, or institutional transaction service.
- `ReentrancyGuard` is included as defense in depth; the current contract has no external value transfers.
- Set up monitoring, backups, admin-key rotation, transaction alerts, rate limits, and privacy/legal review before production use.

## Troubleshooting

- `RPC_URL is missing`: edit `.env`; restart Streamlit after changing environment variables.
- `Wrong network`: ensure the endpoint is Sepolia and `CHAIN_ID=11155111`.
- `No contract bytecode`: check `CONTRACT_ADDRESS` against the deployed address and network.
- `execution reverted` on issue/revoke: verify the configured wallet has `ISSUER_ROLE`, test ETH, and the correct contract address.
- `Import not found`: run `npm install @openzeppelin/contracts@5` from the project root.
- Provider log range errors: lower `chunk_size` in `certificate_app/chain.py` or start history at a later block.
