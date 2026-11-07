import logging
import re

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import investigation


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Healthcare Provider Investigation API",
    description="API for investigating unusual healthcare provider activity.",
    version="1.0.0",
)


class InvestigationRequest(BaseModel):
    provider_npi: str


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/investigate")
def investigate_provider(request: InvestigationRequest):
    provider_npi = request.provider_npi.strip()

    if not re.fullmatch(r"\d{10}", provider_npi):
        raise HTTPException(
            status_code=400,
            detail="Provider NPI must contain exactly 10 digits.",
        )

    try:
        result = investigation.investigation_graph.invoke({
            "provider_npi": provider_npi,
            "profile": {},
            "monthly_activity": [],
            "population_comparison": {},
            "hcpcs_activity": {},
            "monthly_trends": {},
            "monthly_consistency": {},
            "report": {},
        })

        profile = result.get("profile", {})
        if "error" in profile:
            raise HTTPException(status_code=404, detail="Provider not found.")

        return {
            "report": result["report"],
            "monthly_activity": result["monthly_activity"]
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Investigation failed for provider NPI %s", provider_npi)
        raise HTTPException(
            status_code=500,
            detail="Investigation workflow failed.",
        )