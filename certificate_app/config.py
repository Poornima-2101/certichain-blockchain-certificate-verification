import os
from dotenv import load_dotenv

load_dotenv()

RPC_URL = os.getenv("RPC_URL", "").strip()
CHAIN_ID = int(os.getenv("CHAIN_ID", "11155111"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "").strip()
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "").strip()
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8501").rstrip("/")
ARTIFACT_PATH = os.path.join("build", "CertificateRegistry.json")

def require_rpc():
    if not RPC_URL:
        raise RuntimeError("RPC_URL is missing. Copy .env.example to .env and configure it.")
    return RPC_URL
