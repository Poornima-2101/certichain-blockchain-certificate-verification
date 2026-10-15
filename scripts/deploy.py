import json
import os
import sys
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from certificate_app import config
from certificate_app.chain import connect, load_artifact

def main():
    load_dotenv(os.path.join(ROOT, ".env"))
    w3 = connect()
    if not config.PRIVATE_KEY:
        raise SystemExit("Set PRIVATE_KEY in .env to a dedicated Sepolia test wallet.")
    account = Account.from_key(config.PRIVATE_KEY)
    if w3.eth.get_balance(account.address) == 0:
        raise SystemExit(f"Deployer {account.address} has no test ETH. Fund it with Sepolia test ETH.")
    artifact = load_artifact()
    factory = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
    tx = factory.constructor(account.address).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address, "pending"),
        "chainId": w3.eth.chain_id,
        "gas": 6000000,
        "maxFeePerGas": w3.eth.get_block("latest").get("baseFeePerGas", w3.eth.gas_price) * 2 + w3.to_wei(1, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print("Deployment transaction:", tx_hash.hex())
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)
    if receipt.status != 1 or not receipt.contractAddress:
        raise SystemExit("Deployment failed. Check the transaction on Sepolia explorer.")
    print("Contract address:", receipt.contractAddress)
    print("Add this line to .env:")
    print("CONTRACT_ADDRESS=" + receipt.contractAddress)

if __name__ == "__main__":
    main()
