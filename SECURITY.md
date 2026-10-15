# Security checklist

- [ ] Never commit `.env` or private keys.
- [ ] Use a dedicated Sepolia-only test wallet.
- [ ] Confirm chain ID and contract address before issuing.
- [ ] Keep all personally identifying information off-chain.
- [ ] Review/audit contract and transaction flows before production.
- [ ] Use managed key custody and a public read-only verification service for real deployments.
