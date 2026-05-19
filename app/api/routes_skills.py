"""Routes for governance skill metadata."""

from fastapi import APIRouter

from app.core.skills.skill_catalog import list_enabled_skills

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("/")
def list_skills() -> dict[str, object]:
    """Return the configured product-level governance skill catalog."""
    skills = list_enabled_skills()
    return {
        "message": "Product-level local governance skill catalog.",
        "items": [skill.model_dump() for skill in skills],
    }
