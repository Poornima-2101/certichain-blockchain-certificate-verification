import json
import os
from web3 import Web3
from eth_account import Account
from . import config

def connect():
    rpc = config.require_rpc()
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        raise RuntimeError("Could not connect to the RPC endpoint. Check RPC_URL and network access.")
    if w3.eth.chain_id != config.CHAIN_ID:
        raise RuntimeError(f"Wrong network: connected chain ID {w3.eth.chain_id}, expected {config.CHAIN_ID}.")
    return w3

def load_artifact():
    path = config.ARTIFACT_PATH
    if not os.path.isfile(path):
        raise RuntimeError("Contract artifact missing. Run: python scripts/compile_contract.py")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_contract(w3=None):
    w3 = w3 or connect()
    address = config.CONTRACT_ADDRESS
    if not address or not Web3.is_address(address):
        raise RuntimeError("CONTRACT_ADDRESS is missing/invalid. Deploy the contract and set it in .env.")
    artifact = load_artifact()
    contract = w3.eth.contract(address=Web3.to_checksum_address(address), abi=artifact["abi"])
    if len(w3.eth.get_code(contract.address)) == 0:
        raise RuntimeError("No contract bytecode found at CONTRACT_ADDRESS on this network.")
    return w3, contract

def signer(w3):
    if not config.PRIVATE_KEY or "YOUR_TEST_WALLET" in config.PRIVATE_KEY:
        raise RuntimeError("PRIVATE_KEY is not configured in .env.")
    account = Account.from_key(config.PRIVATE_KEY)
    if account.address == "0x0000000000000000000000000000000000000000":
        raise RuntimeError("Invalid signer account.")
    return account

def send_transaction(w3, contract_function):
    account = signer(w3)
    tx = contract_function.build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address, "pending"),
        "chainId": w3.eth.chain_id,
        "gas": 500000,
        "maxFeePerGas": w3.eth.get_block("latest").get("baseFeePerGas", w3.eth.gas_price) * 2 + w3.to_wei(1, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
    })
    # Simulate before broadcasting to catch common reverts.
    contract_function.call({"from": account.address})
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt.status != 1:
        raise RuntimeError(f"Transaction failed: {tx_hash.hex()}")
    return receipt

def issue(certificate_id, document_hash):
    w3, contract = get_contract()
    receipt = send_transaction(w3, contract.functions.issueCertificate(
        bytes.fromhex(certificate_id[2:]), bytes.fromhex(document_hash[2:])
    ))
    return receipt

def revoke(certificate_id):
    w3, contract = get_contract()
    receipt = send_transaction(w3, contract.functions.revokeCertificate(
        bytes.fromhex(certificate_id[2:])
    ))
    return receipt

def get_record(certificate_id):
    w3, contract = get_contract()
    try:
        result = contract.functions.getCertificate(bytes.fromhex(certificate_id[2:])).call()
    except Exception:
        return None
    return {
        "document_hash": "0x" + result[0].hex(),
        "issuer": result[1],
        "issued_at": int(result[2]),
        "revoked_at": int(result[3]),
        "revoked": bool(result[4]),
    }

def verify(certificate_id, document_hash):
    w3, contract = get_contract()
    result = contract.functions.verifyCertificate(
        bytes.fromhex(certificate_id[2:]), bytes.fromhex(document_hash[2:])
    ).call()
    return {"exists": bool(result[0]), "hash_matches": bool(result[1]), "active": bool(result[2])}

def history(from_block=0):
    w3, contract = get_contract()
    latest = w3.eth.block_number
    events = []
    # Bounded chunks avoid provider log-range limits on longer histories.
    chunk_size = 2000
    for start in range(max(0, int(from_block)), latest + 1, chunk_size):
        end = min(start + chunk_size - 1, latest)
        issued = contract.events.CertificateIssued().get_logs(from_block=start, to_block=end)
        revoked = contract.events.CertificateRevoked().get_logs(from_block=start, to_block=end)
        for event in issued:
            a = event["args"]
            events.append({
                "event": "ISSUED", "certificate_id": "0x" + a["certificateId"].hex(),
                "document_hash": "0x" + a["documentHash"].hex(), "actor": a["issuer"],
                "timestamp": int(a["issuedAt"]), "tx_hash": event["transactionHash"].hex()
            })
        for event in revoked:
            a = event["args"]
            events.append({
                "event": "REVOKED", "certificate_id": "0x" + a["certificateId"].hex(),
                "document_hash": "0x" + a["documentHash"].hex(), "actor": a["revoker"],
                "timestamp": int(a["revokedAt"]), "tx_hash": event["transactionHash"].hex()
            })
    return sorted(events, key=lambda x: (x["timestamp"], x["tx_hash"]), reverse=True)
