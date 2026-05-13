"""Routes for governance skill metadata."""

from fastapi import APIRouter

from app.core.orchestrator.workflow_engine import WorkflowEngine

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("/")
def list_skills() -> dict[str, object]:
    """Return the rule-based v1 P0 skill catalog."""
    engine = WorkflowEngine()
    skills = [
        engine.metadata_completeness_check,
        engine.technical_object_identification,
        engine.naming_standard_check,
        engine.metadata_quality_diagnosis,
        engine.governance_task_packaging,
        engine.standard_mapping_recommendation,
        engine.stg_structure_suggestion,
        engine.quality_rule_recommendation,
    ]
    return {
        "message": "Rule-based local governance skill catalog for the current MVP scaffold.",
        "items": [
            {
                "name": skill.skill_name,
                "version": skill.version,
                "description": skill.description,
            }
            for skill in skills
        ],
    }
