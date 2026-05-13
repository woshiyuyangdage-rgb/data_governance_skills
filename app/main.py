"""Minimal FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.routes_jobs import router as jobs_router
from app.api.routes_reports import router as reports_router
from app.api.routes_skills import router as skills_router

app = FastAPI(
    title="Data Governance Skills",
    version="0.14.0",
    description="Local MVP for rule-based metadata governance with workflow profiles, rule-based intent interpretation, session-aware context resolution, agent shell planning, a standard tool contract layer, execution tracing, a lightweight governance control plane, adapter-ready capability export, unified task routing, quality rule recommendation, review replay, confirmed quality rules, execution-ready governance packages, rule/package asset export, and report export.",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return a minimal service health response."""
    return {"status": "ok"}


app.include_router(skills_router)
app.include_router(jobs_router)
app.include_router(reports_router)
