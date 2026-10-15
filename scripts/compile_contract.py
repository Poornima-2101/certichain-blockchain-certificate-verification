
import json
import os
from pathlib import Path
from solcx import compile_files, install_solc

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

OUTPUT_DIR = ROOT / "build"
OUTPUT_DIR.mkdir(exist_ok=True)

# Confirm the OpenZeppelin dependency exists
openzeppelin = Path("node_modules/@openzeppelin/contracts")
if not openzeppelin.is_dir():
    raise FileNotFoundError(
        "OpenZeppelin is missing. Run npm.cmd install @openzeppelin/contracts@5"
    )

install_solc("0.8.24")

compiled = compile_files(
    ["contracts/CertificateRegistry.sol"],
    output_values=["abi", "bin", "bin-runtime"],
    import_remappings=[
        "@openzeppelin/=node_modules/@openzeppelin/"
    ],
    solc_version="0.8.24",
    optimize=True,
    optimize_runs=200,
    base_path=".",
    allow_paths=".,node_modules",
)

contract_key = next(
    (key for key in compiled if key.endswith(":CertificateRegistry")),
    None,
)

if contract_key is None:
    raise RuntimeError("CertificateRegistry was not found in compiler output.")

artifact = compiled[contract_key]

output = {
    "contractName": "CertificateRegistry",
    "abi": artifact["abi"],
    "bytecode": artifact["bin"],
    "deployedBytecode": artifact["bin-runtime"],
}

output_file = OUTPUT_DIR / "CertificateRegistry.json"
output_file.write_text(json.dumps(output, indent=2), encoding="utf-8")

print(f"Compiled CertificateRegistry: {output_file}")
print("Compilation successful!")
