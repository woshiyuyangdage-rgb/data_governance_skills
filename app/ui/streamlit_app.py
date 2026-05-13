"""Streamlit workbench homepage."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    INPUT_TEMPLATE_DOC_PATH,
    SAMPLE_METADATA_PATH,
    ensure_project_root_on_path,
    initialize_session_state,
)

ensure_project_root_on_path()
st.set_page_config(page_title="Data Governance Skills Workbench", layout="wide")
initialize_session_state()

st.title("Data Governance Skills Workbench")
st.write(
    "Local MVP for rule-based metadata diagnosis, knowledge-pack enhancement, "
    "workflow profile routing, natural-language intent interpretation, session-aware "
    "context resolution, agent shell planning, quality rule recommendation, a "
    "standard tool contract layer, execution tracing, a lightweight governance "
    "control plane, an adapter-ready capability export layer, human review memory, "
    "confirmed quality rules, execution-ready packages, and confirmed report export."
)

st.subheader("Workflow")
st.markdown(
    """
    1. Upload metadata file
    2. Optionally use Intent Runner to convert natural language into a workflow task
    3. Optionally use Agent Shell to preview a plan and validate required parameters
    4. Select a workflow profile and run the governance task
    5. Optionally replay saved review overrides
    6. Review mapping, STG, and quality rule suggestions
    7. Re-run with saved overrides
    8. Build execution-ready packages from confirmed quality rules
    9. Export JSON / Markdown / Excel reports
    10. Use Control Plane to maintain dictionaries, profiles, intents, and tool registry
    11. Use Adapter Console to inspect exported schemas and local adapter invocation
    """
)

st.subheader("Current Deliverables")
st.markdown(
    """
    - CSV / Excel metadata file parsing
    - Rule-based P0 metadata diagnosis
    - Knowledge-pack-driven naming enhancement
    - Optional P1 standard mapping recommendation
    - Optional P1.5 STG structure suggestion
    - Optional P2 quality rule recommendation
    - Execution-ready governance package build from confirmed quality rules
    - Workflow profile router with unified task entry
    - Natural-language intent interpreter with rule-based fallback
    - Context resolver with session-based parameter autofill
    - Agent Shell v1 with plan preview and confirmation-aware execution
    - Standard tool contract layer with local execution trace
    - Governance Control Plane for managed config assets
    - Adapter Layer v1 for capability manifest, schema export, and local invocation
    - Human-in-the-loop review and local override memory
    - Governance task packaging
    - Confirmed local report export
    """
)

st.subheader("Working Notes")
st.markdown(
    f"""
    - Input template spec: `{INPUT_TEMPLATE_DOC_PATH}`
    - Sample metadata file: `{SAMPLE_METADATA_PATH}`
    - Preferred template: `table + field-level`
    - Knowledge packs: `abbreviation_dict.csv`, `root_word_dict.csv`, `standard_fields.csv`
    - STG spec: `docs/stg_structure_spec.md`
    - Quality rule spec: `docs/quality_rule_recommendation_spec.md`
    - Execution-ready package spec: `docs/execution_ready_package_spec.md`
    - Review spec: `docs/review_override_spec.md`
    - Workflow profile spec: `docs/workflow_profile_spec.md`
    - Intent spec: `docs/intent_interpreter_spec.md`
    - Context resolver spec: `docs/context_resolver_spec.md`
    - Agent shell spec: `docs/agent_shell_spec.md`
    - Tool contract spec: `docs/tool_contract_spec.md`
    - Control plane spec: `docs/control_plane_spec.md`
    - Adapter layer spec: `docs/adapter_layer_spec.md`
    """
)

st.info(
    "Use the left sidebar pages in order: Upload -> Intent Runner or Agent Shell or Diagnosis -> Review -> Reports, then use Tool Console, Control Plane, or Adapter Console when you need direct operational or integration debugging."
)
