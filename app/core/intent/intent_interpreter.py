"""Rule-based and local NLP-assisted intent interpreter for governance requests."""

from app.core.intent.intent_loader import (
    get_intent_definitions,
    get_parameter_definitions,
)
from app.core.intent.intent_nlp_classifier import (
    IntentNlpMatch,
    classify_intent_text,
)
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.interpreted_intent import InterpretedIntent
from app.core.normalize import clean_text
from app.core.orchestrator.profile_loader import get_workflow_profile

FALLBACK_PROFILE_NAME = "metadata_diagnosis_only"
REPLAY_PROFILE_NAME = "diagnosis_mapping_stg_with_review"
QUALITY_REPLAY_PROFILE_NAME = "diagnosis_mapping_stg_quality_with_review"
QUALITY_PACKAGE_PROFILE_NAME = "diagnosis_mapping_stg_quality_package_with_review"
GOVERNANCE_WORK_PACKAGE_PROFILE_NAME = "full_governance_work_package"
GOVERNANCE_BACKLOG_PROFILE_NAME = "full_governance_backlog_package"
GOVERNANCE_PORTFOLIO_PROFILE_NAME = "full_governance_portfolio_package"
GOVERNANCE_DELIVERY_PACKAGE_PROFILE_NAME = "governance_delivery_package_with_review"
CONFIRMATION_WORKBOOK_PROFILE_NAME = "confirmation_workbook_only"
BATCH_GOVERNANCE_PROFILE_NAME = "batch_governance_run"
BATCH_INCREMENTAL_PROFILE_NAME = "batch_incremental_rerun"
BATCH_DELIVERY_PROFILE_NAME = "batch_delivery_package"
IMPORT_WORKBOOK_PROFILE_NAME = "import_confirmation_workbook"
IMPORT_RERUN_PROFILE_NAME = "import_and_rerun_changed_objects"
PROJECT_TEMPLATE_PROFILE_NAME = "run_project_template"

TEMPLATE_KEYWORDS = {
    "metadata_inventory_project": ["metadata inventory", "元数据盘点", "元数据清单"],
    "standard_mapping_confirmation_project": ["standard mapping confirmation", "标准映射确认", "标准映射确认项目"],
    "stg_structure_design_project": ["stg structure design", "stg结构设计", "stg 结构设计"],
    "quality_rule_build_project": ["quality rule build", "质量规则建设", "质量规则建设项目"],
    "full_governance_delivery_project": ["full governance delivery", "全量交付", "全流程", "完整治理交付"],
}

DOMAIN_PACK_KEYWORDS = {
    "customer_domain_pack": ["customer", "cust", "client", "客户域", "客户"],
    "transaction_domain_pack": ["transaction", "txn", "order", "payment", "交易域", "交易", "订单"],
    "reference_code_domain_pack": ["reference code", "lookup", "dictionary", "码表", "字典", "枚举"],
    "supply_chain_finance_domain_pack": ["supply chain finance", "供应链金融", "finance", "invoice", "settlement"],
}

INTAKE_PROFILE_KEYWORDS = {
    "standard_metadata_template": ["标准元数据模板", "standard metadata template"],
    "governance_platform_export_template": ["治理平台导出模板", "治理平台导出", "platform export"],
    "manual_inventory_template": ["盘点表", "手工盘点", "manual inventory"],
}

CONFIRMATION_TEMPLATE_KEYWORDS = {
    "business_mapping_review_template": ["业务映射确认表", "业务确认表", "business mapping review"],
    "stg_design_review_template": ["stg 设计确认表", "stg设计确认表", "stg design review"],
    "quality_rule_review_template": ["质量规则确认表", "quality rule review"],
    "backlog_update_template": ["backlog 更新表", "backlog更新表", "待办更新表"],
}

WORKBOOK_TYPE_KEYWORDS = {
    "mapping_confirmation": ["映射确认表", "mapping confirmation", "业务映射确认表"],
    "stg_confirmation": ["stg确认表", "stg 设计确认表", "stg design"],
    "quality_rule_confirmation": ["质量规则确认表", "quality rule"],
    "backlog_confirmation": ["backlog 更新表", "待办更新表", "backlog"],
}


class IntentInterpreter:
    """Interpret short natural-language requests into governance task requests."""

    @staticmethod
    def clean_intent_text(text: str) -> str:
        """Normalize raw user intent text before keyword matching."""
        return clean_text(text or "")

    @staticmethod
    def _match_keyword(cleaned_text: str, keyword: str) -> bool:
        normalized_keyword = clean_text(keyword or "")
        return bool(normalized_keyword) and normalized_keyword in cleaned_text

    def score_intent(
        self,
        cleaned_text: str,
        keywords: list[str],
    ) -> tuple[float, list[str]]:
        """Score one intent by counting matched configured keywords."""
        matched_keywords = [
            keyword for keyword in keywords if self._match_keyword(cleaned_text, keyword)
        ]
        score = 0.0
        for keyword in matched_keywords:
            normalized_keyword = clean_text(keyword)
            score += 1.0 + min(1.0, len(normalized_keyword) / 20)
        return round(score, 2), matched_keywords

    def extract_parameters(self, cleaned_text: str) -> dict[str, object]:
        """Extract additional execution parameters from configured keywords."""
        parameter_definitions = get_parameter_definitions()
        inferred_parameters: dict[str, object] = {}

        for parameter_name, payload in parameter_definitions.items():
            keywords = list(payload.get("keywords", []))
            matched_keywords = [
                keyword for keyword in keywords if self._match_keyword(cleaned_text, keyword)
            ]
            if matched_keywords:
                inferred_parameters[parameter_name] = True
                inferred_parameters[f"{parameter_name}_keywords"] = matched_keywords

        for template_name, keywords in TEMPLATE_KEYWORDS.items():
            matched_keywords = [
                keyword for keyword in keywords if self._match_keyword(cleaned_text, keyword)
            ]
            if matched_keywords:
                inferred_parameters["template_name"] = template_name
                inferred_parameters["template_keywords"] = matched_keywords
                break

        for domain_pack_name, keywords in DOMAIN_PACK_KEYWORDS.items():
            matched_keywords = [
                keyword for keyword in keywords if self._match_keyword(cleaned_text, keyword)
            ]
            if matched_keywords:
                inferred_parameters["domain_pack_name"] = domain_pack_name
                inferred_parameters["domain_pack_keywords"] = matched_keywords
                break

        for intake_profile_name, keywords in INTAKE_PROFILE_KEYWORDS.items():
            matched_keywords = [
                keyword for keyword in keywords if self._match_keyword(cleaned_text, keyword)
            ]
            if matched_keywords:
                inferred_parameters["intake_profile_name"] = intake_profile_name
                inferred_parameters["intake_profile_keywords"] = matched_keywords
                break
        if any(
            self._match_keyword(cleaned_text, keyword)
            for keyword in ["识别这个模板", "诊断导入模板", "自动识别元数据模板"]
        ):
            inferred_parameters["auto_match_template"] = True

        for template_name, keywords in CONFIRMATION_TEMPLATE_KEYWORDS.items():
            matched_keywords = [
                keyword for keyword in keywords if self._match_keyword(cleaned_text, keyword)
            ]
            if matched_keywords:
                inferred_parameters["confirmation_template_name"] = template_name
                inferred_parameters["confirmation_template_keywords"] = matched_keywords
                break
        for workbook_type, keywords in WORKBOOK_TYPE_KEYWORDS.items():
            matched_keywords = [
                keyword for keyword in keywords if self._match_keyword(cleaned_text, keyword)
            ]
            if matched_keywords:
                inferred_parameters["workbook_type"] = workbook_type
                inferred_parameters["workbook_type_keywords"] = matched_keywords
                break

        return inferred_parameters

    def choose_best_intent(
        self,
        cleaned_text: str,
        nlp_match: IntentNlpMatch | None = None,
    ) -> tuple[str | None, dict[str, object] | None, list[str], float, str, float | None]:
        """Choose the best scoring intent from configured definitions."""
        best_intent_name: str | None = None
        best_payload: dict[str, object] | None = None
        best_keywords: list[str] = []
        best_score = 0.0
        second_best_score = 0.0

        for intent_name, payload in get_intent_definitions().items():
            score, matched_keywords = self.score_intent(
                cleaned_text,
                list(payload.get("keywords", [])),
            )
            if score > best_score:
                second_best_score = best_score
                best_score = score
                best_intent_name = intent_name
                best_payload = payload
                best_keywords = matched_keywords
            elif score > second_best_score:
                second_best_score = score

        nlp_match = nlp_match or classify_intent_text(cleaned_text)
        if best_intent_name is None or best_payload is None or best_score == 0:
            if nlp_match is None:
                return None, None, [], 0.0, "fallback", None
            nlp_payload = get_intent_definitions().get(nlp_match.intent_name)
            if nlp_payload is None:
                return None, None, [], 0.0, "fallback", None
            confidence = round(min(0.95, max(0.3, nlp_match.similarity)), 2)
            return (
                nlp_match.intent_name,
                nlp_payload,
                [f"nlp:{nlp_match.matched_text}"],
                confidence,
                "local_nlp",
                nlp_match.similarity,
            )

        keyword_count = max(1, len(best_payload.get("keywords", [])))
        coverage = len(best_keywords) / keyword_count
        separation = 0.0 if best_score == 0 else (best_score - second_best_score) / best_score
        confidence = round(min(1.0, max(0.3, (coverage * 0.6) + (separation * 0.4))), 2)
        match_source = "keyword"
        nlp_similarity: float | None = None
        if nlp_match is not None and nlp_match.intent_name == best_intent_name:
            confidence = round(max(confidence, min(0.95, nlp_match.similarity)), 2)
            best_keywords = list(dict.fromkeys([*best_keywords, f"nlp:{nlp_match.matched_text}"]))
            match_source = "keyword+local_nlp"
            nlp_similarity = nlp_match.similarity
        return (
            best_intent_name,
            best_payload,
            best_keywords,
            confidence,
            match_source,
            nlp_similarity,
        )

    @staticmethod
    def build_fallback_intent(raw_text: str) -> InterpretedIntent:
        """Return a safe fallback interpretation when no intent matches."""
        return InterpretedIntent(
            raw_text=raw_text,
            matched_intent_name=None,
            matched_profile_name=FALLBACK_PROFILE_NAME,
            confidence=0.0,
            matched_keywords=[],
            inferred_parameters={},
            fallback_used=True,
            match_source="fallback",
            nlp_similarity=None,
            message=(
                "No clear workflow intent was matched, so the interpreter fell back "
                "to metadata_diagnosis_only."
            ),
        )

    def interpret(self, text: str, file_path: str | None = None) -> InterpretedIntent:
        """Interpret a natural-language request into an explainable intent object."""
        cleaned_text = self.clean_intent_text(text)
        if not cleaned_text:
            fallback_intent = self.build_fallback_intent(text)
            fallback_intent.message = (
                "No task text was provided, so the interpreter fell back to "
                "metadata_diagnosis_only."
            )
            return fallback_intent

        inferred_parameters = self.extract_parameters(cleaned_text)
        nlp_match = classify_intent_text(cleaned_text)
        (
            intent_name,
            intent_payload,
            matched_keywords,
            confidence,
            match_source,
            nlp_similarity,
        ) = self.choose_best_intent(cleaned_text, nlp_match=nlp_match)
        if intent_name is None or intent_payload is None:
            fallback_intent = self.build_fallback_intent(text)
            fallback_intent.inferred_parameters = inferred_parameters
            return fallback_intent

        if nlp_match is not None and nlp_match.intent_name == intent_name:
            inferred_parameters = {
                **nlp_match.inferred_parameters,
                **inferred_parameters,
            }

        profile_name = str(intent_payload.get("profile_name", FALLBACK_PROFILE_NAME))
        parameter_flags = [
            key
            for key, value in inferred_parameters.items()
            if isinstance(value, bool) and value
        ]
        parameter_message = (
            f" Detected parameters: {', '.join(parameter_flags)}."
            if parameter_flags
            else ""
        )
        file_message = " File path was also provided." if file_path else ""
        nlp_message = ""
        if match_source == "local_nlp" and nlp_similarity is not None and nlp_match is not None:
            nlp_message = (
                f" Local NLP matched sample '{nlp_match.matched_text}'"
                f" with similarity {nlp_similarity:.2f}."
            )
        elif match_source == "keyword+local_nlp" and nlp_similarity is not None and nlp_match is not None:
            nlp_message = (
                f" Local NLP also matched sample '{nlp_match.matched_text}'"
                f" with similarity {nlp_similarity:.2f}."
            )

        return InterpretedIntent(
            raw_text=text,
            matched_intent_name=intent_name,
            matched_profile_name=profile_name,
            confidence=confidence,
            matched_keywords=matched_keywords,
            inferred_parameters=inferred_parameters,
            fallback_used=False,
            match_source=match_source,
            nlp_similarity=nlp_similarity,
            message=(
                f"Matched intent '{intent_name}' and mapped it to profile "
                f"'{profile_name}'.{parameter_message}{file_message}{nlp_message}"
            ),
        )

    def build_task_request(
        self,
        intent: InterpretedIntent,
        file_path: str | None = None,
    ) -> GovernanceTaskRequest:
        """Build a standard governance task request from an interpreted intent."""
        profile_name = intent.matched_profile_name or FALLBACK_PROFILE_NAME
        inferred_parameters = dict(intent.inferred_parameters)

        apply_review_replay = bool(inferred_parameters.get("apply_review_replay", False))
        export_reports = bool(inferred_parameters.get("export_reports", False))
        auto_match_template = bool(inferred_parameters.get("auto_match_template", False))
        preferred_result_mode = (
            "confirmed" if bool(inferred_parameters.get("confirmed_mode", False)) else None
        )

        if inferred_parameters.get("template_name"):
            profile_name = PROJECT_TEMPLATE_PROFILE_NAME
            apply_review_replay = True
            preferred_result_mode = "template"
        elif intent.matched_intent_name == "replay_confirmed":
            profile_name = REPLAY_PROFILE_NAME
            apply_review_replay = True
        elif intent.matched_intent_name == "execution_ready_package":
            profile_name = QUALITY_PACKAGE_PROFILE_NAME
            apply_review_replay = True
            preferred_result_mode = "package"
        elif intent.matched_intent_name == "full_governance_work_package":
            profile_name = GOVERNANCE_WORK_PACKAGE_PROFILE_NAME
            apply_review_replay = True
            preferred_result_mode = "remediation"
        elif intent.matched_intent_name == "full_governance_backlog_package":
            profile_name = GOVERNANCE_BACKLOG_PROFILE_NAME
            apply_review_replay = True
            preferred_result_mode = "backlog"
        elif intent.matched_intent_name == "full_governance_portfolio_package":
            profile_name = GOVERNANCE_PORTFOLIO_PROFILE_NAME
            apply_review_replay = True
            preferred_result_mode = "portfolio"
        elif intent.matched_intent_name == "governance_delivery_package":
            profile_name = GOVERNANCE_DELIVERY_PACKAGE_PROFILE_NAME
            apply_review_replay = True
            preferred_result_mode = "package"
        elif intent.matched_intent_name == "confirmation_workbook_only":
            profile_name = CONFIRMATION_WORKBOOK_PROFILE_NAME
            apply_review_replay = True
            preferred_result_mode = "workbook"
        elif intent.matched_intent_name == "batch_governance_run":
            profile_name = BATCH_GOVERNANCE_PROFILE_NAME
            apply_review_replay = True
            preferred_result_mode = "batch"
        elif intent.matched_intent_name == "batch_incremental_rerun":
            profile_name = BATCH_INCREMENTAL_PROFILE_NAME
            apply_review_replay = True
            preferred_result_mode = "incremental"
        elif intent.matched_intent_name == "batch_delivery_package":
            profile_name = BATCH_DELIVERY_PROFILE_NAME
            apply_review_replay = True
            preferred_result_mode = "delivery"
        elif intent.matched_intent_name == "import_confirmation_workbook":
            profile_name = IMPORT_WORKBOOK_PROFILE_NAME
            preferred_result_mode = "import"
        elif intent.matched_intent_name == "import_and_rerun_changed_objects":
            profile_name = IMPORT_RERUN_PROFILE_NAME
            preferred_result_mode = "rerun"
        elif intent.matched_intent_name == "project_template_run":
            profile_name = PROJECT_TEMPLATE_PROFILE_NAME
            apply_review_replay = True
            preferred_result_mode = "template"
        elif intent.matched_intent_name == "governance_portfolio_assessment":
            preferred_result_mode = "portfolio"
        elif intent.matched_intent_name == "governance_readiness_assessment":
            preferred_result_mode = "readiness"
        elif apply_review_replay and profile_name == "diagnosis_mapping_stg":
            profile_name = REPLAY_PROFILE_NAME
        elif apply_review_replay and profile_name == "diagnosis_mapping_stg_quality":
            profile_name = QUALITY_REPLAY_PROFILE_NAME
        elif apply_review_replay and profile_name == "diagnosis_mapping_stg_quality_package":
            profile_name = QUALITY_PACKAGE_PROFILE_NAME
        elif apply_review_replay and profile_name == "governance_readiness_assessment":
            profile_name = "governance_readiness_assessment_with_review"

        if profile_name in {
            "diagnosis_mapping_stg_quality_package",
            "diagnosis_mapping_stg_quality_package_with_review",
            "quality_package_only_from_confirmed",
        }:
            preferred_result_mode = "package"
        if profile_name in {
            "governance_readiness_assessment",
            "governance_readiness_assessment_with_review",
        }:
            preferred_result_mode = "readiness"
        if profile_name == "full_governance_work_package":
            preferred_result_mode = "remediation"
        if profile_name in {
            "governance_backlog_build",
            "governance_backlog_build_with_review",
            "full_governance_backlog_package",
        }:
            preferred_result_mode = "backlog"
        if profile_name in {
            "governance_portfolio_assessment",
            "full_governance_portfolio_package",
        }:
            preferred_result_mode = "portfolio"
        if profile_name in {
            "governance_delivery_package",
            "governance_delivery_package_with_review",
        }:
            preferred_result_mode = "package"
        if profile_name == "confirmation_workbook_only":
            preferred_result_mode = "workbook"
        if profile_name == "batch_governance_run":
            preferred_result_mode = "batch"
        if profile_name == "batch_incremental_rerun":
            preferred_result_mode = "incremental"
        if profile_name == "batch_delivery_package":
            preferred_result_mode = "delivery"
        if profile_name == "import_confirmation_workbook":
            preferred_result_mode = "import"
        if profile_name == "import_and_rerun_changed_objects":
            preferred_result_mode = "rerun"
        if profile_name == "run_project_template":
            preferred_result_mode = "template"
        if auto_match_template or inferred_parameters.get("intake_profile_name"):
            preferred_result_mode = "intake"
        if (
            inferred_parameters.get("confirmation_template_name")
            or inferred_parameters.get("workbook_type")
        ) and profile_name in {
            FALLBACK_PROFILE_NAME,
            "import_confirmation_workbook",
            "import_and_rerun_changed_objects",
            "import_confirmation_with_template",
            "import_confirmation_template_and_rerun",
            "diagnose_confirmation_template",
        }:
            preferred_result_mode = "import"
            if profile_name == FALLBACK_PROFILE_NAME:
                profile_name = "import_confirmation_with_template"

        profile = get_workflow_profile(profile_name)
        if apply_review_replay and not profile.supports_review_replay:
            apply_review_replay = False

        return GovernanceTaskRequest(
            file_path=file_path,
            profile_name=profile_name,
            template_name=str(inferred_parameters.get("template_name") or "") or None,
            domain_pack_name=str(inferred_parameters.get("domain_pack_name") or "") or None,
            intake_profile_name=str(inferred_parameters.get("intake_profile_name") or "") or None,
            auto_match_template=auto_match_template,
            workbook_type=str(inferred_parameters.get("workbook_type") or "") or None,
            confirmation_template_name=str(inferred_parameters.get("confirmation_template_name") or "") or None,
            apply_review_replay=apply_review_replay,
            export_reports=export_reports,
            preferred_result_mode=preferred_result_mode,
        )


# TODO: extend rule-based interpretation with optional LLM parsing and multi-turn parameter clarification.
