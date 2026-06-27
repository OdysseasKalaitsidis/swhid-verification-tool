# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

from fastapi import FastAPI, Query, HTTPException
from swhid_tool.manager import SWHIDManager
from swhid_tool.logging_config import setup_logging
from typing import Dict, Any

setup_logging()
app = FastAPI(title="SWHID Verification API")
manager = SWHIDManager()


@app.get("/resolve")
async def resolve_purl(purl: str = Query(..., description="The Package URL to resolve")):
    """
    Resolves a PURL to a SWHID, returning confidence level and strategy used.
    """
    try:
        result = manager.resolve(purl)
        return {
            "purl": result.get("purl"),
            "swhid": result.get("swhid"),
            "confidence": result.get("confidence"),
            "strategy": result.get("strategy", result.get("name", "unknown")),
            "status": result.get("status", "Done"),
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
