import io
import time
from datetime import datetime, timezone
import streamlit as st
import qrcode
from PIL import Image
from web3 import Web3
from certificate_app import config
from certificate_app.crypto import sha256_bytes, new_certificate_id, normalize_bytes32, validate_upload
from certificate_app.chain import connect, get_contract, issue, revoke, verify, get_record, history

st.set_page_config(page_title="CertiChain | Certificate Verification", page_icon="🔐", layout="wide")
st.title("🔐 CertiChain")
st.caption("Blockchain-based digital certificate issuance and verification")
st.info("The blockchain stores document hashes and status only. Do not upload sensitive personal information to the chain.")

def explorer_tx(tx_hash):
    return f"https://sepolia.etherscan.io/tx/{tx_hash}"

def display_time(timestamp):
    if not timestamp:
        return "—"
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def make_qr(payload):
    image = qrcode.make(payload)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

with st.sidebar:
    st.subheader("Network")
    try:
        w3 = connect()
        st.success(f"Connected · chain ID {w3.eth.chain_id}")
        if config.CONTRACT_ADDRESS:
            st.code(config.CONTRACT_ADDRESS)
        else:
            st.warning("Set CONTRACT_ADDRESS in .env after deployment.")
    except Exception as exc:
        st.error(str(exc))
        st.caption("You can still read the project UI, but blockchain actions need a valid RPC and deployed contract.")

tabs = st.tabs(["Issue certificate", "Verify certificate", "Revoke certificate", "History"])

with tabs[0]:
    st.subheader("Issue a new certificate")
    st.write("Upload the exact PDF or JSON file you want to issue. The original file is not sent to Ethereum.")
    uploaded = st.file_uploader("Certificate file", type=["pdf", "json"], key="issue_file")
    if uploaded:
        st.write(f"File: **{uploaded.name}** · {uploaded.size:,} bytes")
        if st.button("Generate fingerprint", key="fingerprint"):
            try:
                data = uploaded.getvalue()
                validate_upload(uploaded.name, data)
                st.session_state["issue_data"] = data
                st.session_state["issue_filename"] = uploaded.name
                st.session_state["issue_hash"] = sha256_bytes(data)
                st.session_state["issue_id"] = new_certificate_id()
            except Exception as exc:
                st.error(str(exc))
    if st.session_state.get("issue_hash"):
        st.text_input("SHA-256 hash", value=st.session_state["issue_hash"], disabled=True)
        st.text_input("Certificate ID", value=st.session_state["issue_id"], disabled=True)
        st.warning("Issuing writes a public transaction and costs Sepolia test ETH. Never use a wallet holding real funds for a demo.")
        if st.button("Issue on blockchain", type="primary"):
            try:
                receipt = issue(st.session_state["issue_id"], st.session_state["issue_hash"])
                st.success("Certificate issued successfully.")
                st.markdown(f"[View transaction on Sepolia Etherscan]({explorer_tx(receipt.transactionHash.hex())})")
                payload = f"{config.APP_BASE_URL}/?cert_id={st.session_state['issue_id']}"
                qr = make_qr(payload)
                st.image(qr, caption="Verification QR code", width=220)
                st.download_button("Download QR code", qr, file_name="certificate_qr.png", mime="image/png")
                st.code(payload)
            except Exception as exc:
                st.error(f"Issue failed: {exc}")

with tabs[1]:
    st.subheader("Verify certificate authenticity")
    st.write("Enter a certificate ID, and optionally upload the original file to compare its SHA-256 hash.")
    query_id = st.text_input("Certificate ID (0x + 64 hex characters)", key="verify_id")
    verify_file = st.file_uploader("Original certificate (optional)", type=["pdf", "json"], key="verify_file")
    supplied_hash = ""
    if verify_file:
        try:
            data = verify_file.getvalue()
            validate_upload(verify_file.name, data)
            supplied_hash = sha256_bytes(data)
            st.text_input("Computed SHA-256", value=supplied_hash, disabled=True)
        except Exception as exc:
            st.error(str(exc))
    manual_hash = st.text_input("Or paste SHA-256 hash (0x + 64 hex characters)", key="verify_hash")
    if st.button("Verify certificate", key="verify_btn"):
        try:
            cert_id = normalize_bytes32(query_id)
            document_hash = supplied_hash or normalize_bytes32(manual_hash)
            result = verify(cert_id, document_hash)
            if not result["exists"]:
                st.error("Certificate not found on this contract.")
            elif not result["hash_matches"]:
                st.error("Hash mismatch: the supplied file/hash does not match the issued certificate.")
            elif not result["active"]:
                st.warning("The certificate hash matches, but this certificate has been revoked.")
            else:
                st.success("Verified: hash matches and certificate is active.")
            record = get_record(cert_id)
            if record:
                st.write("**Issuer:**", record["issuer"])
                st.write("**Issued:**", display_time(record["issued_at"]))
                st.write("**Status:**", "Revoked" if record["revoked"] else "Active")
                st.write("**On-chain hash:**")
                st.code(record["document_hash"])
        except Exception as exc:
            st.error(f"Could not verify: {exc}")

with tabs[2]:
    st.subheader("Revoke a certificate")
    st.write("Only an account with ISSUER_ROLE can revoke a certificate.")
    revoke_id = st.text_input("Certificate ID to revoke (0x + 64 hex characters)")
    if st.button("Revoke on blockchain", type="primary"):
        try:
            receipt = revoke(normalize_bytes32(revoke_id))
            st.success("Certificate revoked.")
            st.markdown(f"[View revocation transaction on Sepolia Etherscan]({explorer_tx(receipt.transactionHash.hex())})")
        except Exception as exc:
            st.error(f"Revocation failed: {exc}")

with tabs[3]:
    st.subheader("On-chain verification history")
    start_block = st.number_input("Start block (0 = contract deployment history)", min_value=0, value=0, step=1)
    if st.button("Load history"):
        try:
            events = history(int(start_block))
            if not events:
                st.info("No matching events found in the selected range.")
            else:
                rows = []
                for item in events:
                    rows.append({
                        "Event": item["event"],
                        "Certificate ID": item["certificate_id"],
                        "SHA-256": item["document_hash"],
                        "Actor": item["actor"],
                        "Time (UTC)": display_time(item["timestamp"]),
                        "Transaction": item["tx_hash"],
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)
                st.download_button("Download history as CSV",
                    data=__import__("pandas").DataFrame(rows).to_csv(index=False).encode("utf-8"),
                    file_name="certificate_history.csv", mime="text/csv")
        except Exception as exc:
            st.error(f"Could not load history: {exc}")

st.divider()
st.caption("Demo software. Verify the contract address and network independently. A matching hash proves byte-for-byte integrity, not the truth of the claims inside the certificate.")
