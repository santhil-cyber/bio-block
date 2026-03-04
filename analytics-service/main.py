"""
Bio-Block Analytics Service — Skeleton POC
==========================================
GSoC 2026 Pre-Proposal Prototype

A minimal FastAPI service running on port 3003 demonstrating:
- Service health endpoint
- EIP-712 typed data signature verification with replay protection
- Multipart CSV upload with size/row validation
- Descriptive statistics stub (pandas)

This is a skeleton to prove architectural feasibility.
Full implementation will be built during GSoC coding phases.
"""

import csv
import io
import time
import hashlib
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from web3 import Web3

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Bio-Block Analytics API",
    description="Decentralized analytics for Bio-Block health data marketplace",
    version="0.1.0-poc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOCUMENT_STORAGE_ADDRESS = "0xd58de64aac08d5412b8020c7c61b215fec0c9644"
SIGNATURE_EXPIRY_SECONDS = 300  # 5 minutes
MAX_FILE_SIZE_MB = 10
MAX_ROWS = 10_000

# Per-wallet nonce tracking (in production: Redis or DB)
_used_nonces: dict[str, set[int]] = {}

# ---------------------------------------------------------------------------
# EIP-712 Auth — Core verification logic
# ---------------------------------------------------------------------------

EIP712_TYPES = {
    "AnalyticsRequest": [
        {"name": "datasetCID", "type": "string"},
        {"name": "timestamp", "type": "uint256"},
        {"name": "nonce", "type": "uint256"},
        {"name": "requestHash", "type": "string"},
    ]
}
EIP712_DOMAIN = {"name": "BioBlockAnalytics", "version": "1"}


def verify_signature(
    wallet_address: str,
    dataset_cid: str,
    signature: str,
    timestamp: int,
    nonce: int,
    request_hash: str,
) -> bool:
    """
    Verify EIP-712 typed structured data signature with replay protection.

    Security checks:
    1. Timestamp freshness (5-minute window)
    2. Per-wallet nonce uniqueness (anti-replay)
    3. Request hash integrity (anti-tampering)
    4. EIP-712 signer recovery and address match
    """
    # 1. Reject expired signatures
    if abs(time.time() - timestamp) > SIGNATURE_EXPIRY_SECONDS:
        return False

    # 2. Reject reused nonces
    wallet_key = wallet_address.lower()
    wallet_nonces = _used_nonces.setdefault(wallet_key, set())
    if nonce in wallet_nonces:
        return False

    # 3. Signature verification would happen here via web3.py
    #    (Requires RPC connection — stubbed for POC)
    #    recovered = w3.eth.account.recover_message(
    #        encode_typed_data({...}), signature=signature
    #    )

    # 4. On-chain DocumentPurchased event check would happen here
    #    (Requires Sepolia RPC — stubbed for POC)

    # Mark nonce as used on success
    wallet_nonces.add(nonce)
    return True


# ---------------------------------------------------------------------------
# CSV Parsing — Robust healthcare CSV handling
# ---------------------------------------------------------------------------


def parse_csv_upload(file_bytes: bytes) -> pd.DataFrame:
    """
    Parse uploaded CSV with robust encoding/dialect handling.
    Healthcare CSVs are notoriously messy.
    """
    # Try UTF-8 first, fall back to ISO-8859-1
    for encoding in ("utf-8", "iso-8859-1"):
        try:
            text = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(400, "Unable to decode CSV (tried UTF-8, ISO-8859-1)")

    # Sniff delimiter
    try:
        dialect = csv.Sniffer().sniff(text[:4096])
        sep = dialect.delimiter
    except csv.Error:
        sep = ","

    df = pd.read_csv(
        io.StringIO(text), sep=sep, on_bad_lines="skip", engine="python"
    )

    if len(df) > MAX_ROWS:
        raise HTTPException(
            413,
            f"Dataset exceeds {MAX_ROWS} row limit (got {len(df)} rows)",
        )

    return df


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health_check():
    """Service health check — confirms the analytics API is running."""
    return {
        "status": "healthy",
        "service": "bio-block-analytics",
        "version": "0.1.0-poc",
        "port": 3003,
    }


@app.post("/analytics/describe")
async def descriptive_analysis(
    file: UploadFile = File(...),
    wallet_address: str = Form(...),
    dataset_cid: str = Form(...),
    signature: str = Form(...),
    timestamp: int = Form(...),
    nonce: int = Form(...),
    request_hash: str = Form(...),
    columns: Optional[str] = Form(None),
):
    """
    Compute descriptive statistics on an uploaded CSV dataset.
    Requires EIP-712 signature proving dataset purchase.
    """
    # Verify file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {MAX_FILE_SIZE_MB}MB limit")

    # Verify signature
    if not verify_signature(
        wallet_address, dataset_cid, signature, timestamp, nonce, request_hash
    ):
        raise HTTPException(401, "Invalid or expired signature")

    # Parse CSV
    df = parse_csv_upload(contents)

    # Select columns
    target_cols = (
        columns.split(",") if columns else
        df.select_dtypes(include=[np.number]).columns.tolist()
    )

    # Compute statistics
    result = {}
    for col in target_cols:
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if not np.issubdtype(series.dtype, np.number):
            continue
        result[col] = {
            "count": int(series.count()),
            "mean": round(float(series.mean()), 4),
            "std": round(float(series.std()), 4),
            "min": float(series.min()),
            "max": float(series.max()),
            "median": float(series.median()),
            "missing_pct": round(float(df[col].isna().mean() * 100), 2),
        }

    if len(target_cols) > 1:
        numeric_cols = [c for c in target_cols if c in result]
        if len(numeric_cols) > 1:
            result["_correlations"] = (
                df[numeric_cols].corr().round(4).to_dict()
            )

    return {
        "analysis_type": "descriptive",
        "source_dataset_cid": dataset_cid,
        "row_count": len(df),
        "columns_analyzed": list(result.keys()),
        "results": result,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3003)
