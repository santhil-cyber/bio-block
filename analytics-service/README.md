# Bio-Block Analytics Service — POC

> GSoC 2026 Pre-Proposal Prototype

A skeleton FastAPI microservice demonstrating the analytics layer architecture proposed for Bio-Block.

## What This Proves

- **Service isolation**: Runs on port 3003 independently of existing backends (3001, 3002)
- **EIP-712 auth design**: Typed structured data signature verification with nonce + timestamp replay protection
- **CSV upload handling**: Robust `multipart/form-data` parsing with encoding detection and row limits
- **Descriptive analytics**: Basic per-column statistics using pandas

## Quick Start

```bash
cd analytics-service
pip install -r requirements.txt
python main.py
```

Then visit: http://localhost:3003/docs (auto-generated Swagger UI)

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health check |
| `POST` | `/analytics/describe` | Descriptive statistics on uploaded CSV |

## Status

This is a **proof-of-concept skeleton**. The full implementation (inferential statistics, visualization engine, OpenDP integration, on-chain registration, frontend dashboard) will be built during GSoC coding phases.
