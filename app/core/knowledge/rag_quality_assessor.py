"""Local rule-based RAG knowledge-base quality assessment."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime

from app.core.models.rag_quality import (
    RagAnswerEvaluation,
    RagKnowledgeChunk,
    RagKnowledgeDocument,
    RagQualityAssessmentResult,
    RagQualityIssue,
    RagRetrievalLog,
)
from app.core.utils.time_utils import utc_today

DEFAULT_MIN_CHUNK_CHARS = 80
DEFAULT_MAX_CHUNK_CHARS = 2200
DEFAULT_STALE_DAYS = 730
DEFAULT_LOW_RETRIEVAL_SCORE = 0.45
DEFAULT_LOW_FAITHFULNESS = 0.7
SENSITIVE_TOKENS = {
    "secret",
    "confidential",
    "restricted",
    "internal_only",
    "private",
    "sensitive",
}
DEPRECATED_STATUSES = {"deprecated", "obsolete", "retired", "inactive", "expired"}
PUBLIC_LABELS = {"public", "open", "all", "guest"}


def _text(value: object) -> str:
    return str(value or "").strip()


def _lower(value: object) -> str:
    return _text(value).lower()


def _parse_date(value: str | None) -> date | None:
    text = _text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _estimate_tokens(content: str) -> int:
    text = content.strip()
    if not text:
        return 0
    if " " in text:
        return len([token for token in text.split() if token])
    return max(1, len(text) // 2)


def _permission_rank(label: str | None) -> int:
    normalized = _lower(label)
    if not normalized:
        return 0
    if normalized in PUBLIC_LABELS:
        return 1
    if normalized in {"internal", "employee", "company"}:
        return 2
    if normalized in {"restricted", "confidential", "secret", "sensitive"}:
        return 3
    return 2


class RagQualityAssessor:
    """Assess documents, chunks, retrieval logs, answers, and permissions."""

    def __init__(
        self,
        *,
        min_chunk_chars: int = DEFAULT_MIN_CHUNK_CHARS,
        max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
        stale_days: int = DEFAULT_STALE_DAYS,
        low_retrieval_score: float = DEFAULT_LOW_RETRIEVAL_SCORE,
        low_faithfulness_score: float = DEFAULT_LOW_FAITHFULNESS,
    ) -> None:
        self.min_chunk_chars = min_chunk_chars
        self.max_chunk_chars = max_chunk_chars
        self.stale_days = stale_days
        self.low_retrieval_score = low_retrieval_score
        self.low_faithfulness_score = low_faithfulness_score

    @staticmethod
    def _issue(
        *,
        object_type: str,
        object_name: str,
        issue_type: str,
        severity: str,
        evidence: list[str],
        risk: str,
        suggestion: str,
        category: str,
        business_domain: str | None = None,
        requires_manual_review: bool | None = None,
    ) -> RagQualityIssue:
        return RagQualityIssue(
            object_type=object_type,
            object_name=object_name,
            issue_type=issue_type,
            severity=severity,
            evidence=evidence,
            risk=risk,
            suggestion=suggestion,
            category=category,
            business_domain=business_domain,
            requires_manual_review=(
                requires_manual_review if requires_manual_review is not None else severity in {"high", "critical"}
            ),
        )

    def _assess_documents(
        self,
        documents: list[RagKnowledgeDocument],
        latest_version_by_title_source: dict[tuple[str, str], str],
    ) -> list[RagQualityIssue]:
        issues: list[RagQualityIssue] = []
        today = utc_today()
        version_groups = Counter(
            (_lower(doc.title), _lower(doc.source), _lower(doc.version))
            for doc in documents
            if doc.title and doc.source and doc.version
        )
        for doc in documents:
            object_name = doc.document_id
            if not doc.title:
                issues.append(
                    self._issue(
                        object_type="document",
                        object_name=object_name,
                        issue_type="missing_document_title",
                        severity="medium",
                        evidence=["title is blank"],
                        risk="RAG retrieval results are harder to explain and cite.",
                        suggestion="Add a stable document title before indexing.",
                        category="document_quality",
                        business_domain=doc.business_domain,
                    )
                )
            if not doc.source:
                issues.append(
                    self._issue(
                        object_type="document",
                        object_name=object_name,
                        issue_type="missing_document_source",
                        severity="medium",
                        evidence=["source is blank"],
                        risk="Answers cannot reliably cite the authoritative source.",
                        suggestion="Add source system, repository, or issuing organization.",
                        category="document_quality",
                        business_domain=doc.business_domain,
                    )
                )
            if not doc.version:
                issues.append(
                    self._issue(
                        object_type="document",
                        object_name=object_name,
                        issue_type="missing_version",
                        severity="medium",
                        evidence=["version is blank"],
                        risk="Duplicate or outdated policies may be mixed during retrieval.",
                        suggestion="Add a version number or effective release marker.",
                        category="metadata_tags",
                        business_domain=doc.business_domain,
                    )
                )
            updated_at = _parse_date(doc.updated_at)
            if updated_at is None:
                issues.append(
                    self._issue(
                        object_type="document",
                        object_name=object_name,
                        issue_type="missing_updated_at",
                        severity="medium",
                        evidence=["updated_at is blank or not parseable"],
                        risk="RAG may retrieve stale guidance without knowing it.",
                        suggestion="Add a parseable updated_at date.",
                        category="metadata_tags",
                        business_domain=doc.business_domain,
                    )
                )
            elif (today - updated_at).days > self.stale_days:
                issues.append(
                    self._issue(
                        object_type="document",
                        object_name=object_name,
                        issue_type="stale_document",
                        severity="high",
                        evidence=[f"updated_at={doc.updated_at}", f"age_days={(today - updated_at).days}"],
                        risk="Answers may cite outdated standards or policies.",
                        suggestion="Review, refresh, or retire the stale document.",
                        category="document_quality",
                        business_domain=doc.business_domain,
                    )
                )
            if _lower(doc.status) in DEPRECATED_STATUSES:
                issues.append(
                    self._issue(
                        object_type="document",
                        object_name=object_name,
                        issue_type="deprecated_document_indexed",
                        severity="high",
                        evidence=[f"status={doc.status}"],
                        risk="Deprecated policies can be retrieved as if they were active.",
                        suggestion="Remove deprecated documents from the public retrieval index or mark them as excluded.",
                        category="document_quality",
                        business_domain=doc.business_domain,
                    )
                )
            if doc.title and doc.source:
                key = (_lower(doc.title), _lower(doc.source))
                latest_version = latest_version_by_title_source.get(key)
                if doc.version and latest_version and _lower(doc.version) != latest_version:
                    issues.append(
                        self._issue(
                            object_type="document",
                            object_name=object_name,
                            issue_type="outdated_duplicate_version",
                            severity="high",
                            evidence=[f"version={doc.version}", f"latest_version={latest_version}"],
                            risk="RAG can answer with an older version while a newer version exists.",
                            suggestion="Exclude older versions or lower their retrieval priority.",
                            category="document_quality",
                            business_domain=doc.business_domain,
                        )
                    )
                duplicate_count = version_groups.get(
                    (_lower(doc.title), _lower(doc.source), _lower(doc.version)),
                    0,
                )
                if duplicate_count > 1:
                    issues.append(
                        self._issue(
                            object_type="document",
                            object_name=object_name,
                            issue_type="duplicate_document_version",
                            severity="medium",
                            evidence=[f"duplicate_count={duplicate_count}"],
                            risk="Duplicate content can crowd out other relevant retrieval results.",
                            suggestion="Deduplicate identical title/source/version documents before indexing.",
                            category="document_quality",
                            business_domain=doc.business_domain,
                        )
                    )
            issues.extend(self._assess_document_tags(doc))
        return issues

    def _assess_document_tags(self, doc: RagKnowledgeDocument) -> list[RagQualityIssue]:
        issues: list[RagQualityIssue] = []
        tag_checks = [
            ("business_domain", doc.business_domain, "missing_business_domain_tag", "Add business domain metadata."),
            ("permission_label", doc.permission_label, "missing_permission_label", "Add access-control metadata."),
            ("owner_department", doc.owner_department, "missing_owner_department", "Add the responsible department."),
            ("effective_date", doc.effective_date, "missing_effective_date", "Add the effective date."),
            ("category", doc.category, "missing_document_category", "Add document category metadata."),
        ]
        for field_name, value, issue_type, suggestion in tag_checks:
            if value:
                continue
            severity = "high" if field_name == "permission_label" else "medium"
            issues.append(
                self._issue(
                    object_type="document",
                    object_name=doc.document_id,
                    issue_type=issue_type,
                    severity=severity,
                    evidence=[f"{field_name} is blank"],
                    risk="RAG filtering, citation, or authorization can become unreliable.",
                    suggestion=suggestion,
                    category="metadata_tags",
                    business_domain=doc.business_domain,
                )
            )
        return issues

    def _assess_chunks(
        self,
        chunks: list[RagKnowledgeChunk],
        documents_by_id: dict[str, RagKnowledgeDocument],
    ) -> list[RagQualityIssue]:
        issues: list[RagQualityIssue] = []
        for chunk in chunks:
            content = _text(chunk.content)
            char_count = len(content)
            doc = documents_by_id.get(chunk.document_id)
            if chunk.document_id not in documents_by_id:
                issues.append(
                    self._issue(
                        object_type="chunk",
                        object_name=chunk.chunk_id,
                        issue_type="orphan_chunk",
                        severity="high",
                        evidence=[f"document_id={chunk.document_id}"],
                        risk="Retrieved chunk cannot be traced to a governed document.",
                        suggestion="Rebuild the index with valid document references.",
                        category="chunk_quality",
                        business_domain=chunk.business_domain,
                    )
                )
            if char_count < self.min_chunk_chars:
                issues.append(
                    self._issue(
                        object_type="chunk",
                        object_name=chunk.chunk_id,
                        issue_type="chunk_too_short",
                        severity="medium",
                        evidence=[f"char_count={char_count}", f"min_chunk_chars={self.min_chunk_chars}"],
                        risk="The chunk may lack enough context for faithful answers.",
                        suggestion="Merge with neighboring context or include section heading.",
                        category="chunk_quality",
                        business_domain=chunk.business_domain or (doc.business_domain if doc else None),
                    )
                )
            if char_count > self.max_chunk_chars:
                issues.append(
                    self._issue(
                        object_type="chunk",
                        object_name=chunk.chunk_id,
                        issue_type="chunk_too_long",
                        severity="medium",
                        evidence=[f"char_count={char_count}", f"max_chunk_chars={self.max_chunk_chars}"],
                        risk="Long chunks dilute retrieval relevance and can bury the answer.",
                        suggestion="Split by section or table boundaries while preserving headings.",
                        category="chunk_quality",
                        business_domain=chunk.business_domain or (doc.business_domain if doc else None),
                    )
                )
            if not chunk.title and not (doc and doc.title):
                issues.append(
                    self._issue(
                        object_type="chunk",
                        object_name=chunk.chunk_id,
                        issue_type="chunk_missing_title_context",
                        severity="medium",
                        evidence=["chunk title and document title are blank"],
                        risk="Retrieved context may be hard for the model to ground.",
                        suggestion="Attach document and section titles to every chunk.",
                        category="chunk_quality",
                        business_domain=chunk.business_domain or (doc.business_domain if doc else None),
                    )
                )
            if self._looks_like_broken_table(content):
                issues.append(
                    self._issue(
                        object_type="chunk",
                        object_name=chunk.chunk_id,
                        issue_type="table_chunk_fragmented",
                        severity="high",
                        evidence=["table markers detected without enough row or header context"],
                        risk="Answers may miss field definitions or mix table columns incorrectly.",
                        suggestion="Chunk tables as complete logical tables or attach repeated headers.",
                        category="chunk_quality",
                        business_domain=chunk.business_domain or (doc.business_domain if doc else None),
                    )
                )
            if not chunk.embedding_id:
                issues.append(
                    self._issue(
                        object_type="chunk",
                        object_name=chunk.chunk_id,
                        issue_type="missing_embedding_reference",
                        severity="medium",
                        evidence=["embedding_id is blank"],
                        risk="Vector index freshness and traceability cannot be verified.",
                        suggestion="Persist embedding id or index version for each chunk.",
                        category="retrieval_quality",
                        business_domain=chunk.business_domain or (doc.business_domain if doc else None),
                    )
                )
            issues.extend(self._assess_chunk_permissions(chunk, doc))
        return issues

    @staticmethod
    def _looks_like_broken_table(content: str) -> bool:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if len(lines) > 2:
            return False

        first_line = lines[0].lower() if lines else ""
        pipe_cells = [cell.strip() for cell in first_line.split("|") if cell.strip()]
        has_markdown_row = "|" in first_line and len(pipe_cells) >= 3
        has_csv_header = (
            first_line.count(",") >= 3
            and any(token in first_line for token in ["field", "column", "name", "type", "desc"])
        )

        return has_markdown_row or has_csv_header
    def _assess_chunk_permissions(
        self,
        chunk: RagKnowledgeChunk,
        doc: RagKnowledgeDocument | None,
    ) -> list[RagQualityIssue]:
        issues: list[RagQualityIssue] = []
        inherited_label = doc.permission_label if doc else None
        label = chunk.permission_label or inherited_label
        content_lower = chunk.content.lower()
        sensitive_detected = any(token in content_lower for token in SENSITIVE_TOKENS)
        if not label:
            issues.append(
                self._issue(
                    object_type="chunk",
                    object_name=chunk.chunk_id,
                    issue_type="chunk_missing_permission_label",
                    severity="high",
                    evidence=["permission_label is blank on chunk and document"],
                    risk="Users may retrieve content outside their permission boundary.",
                    suggestion="Propagate permission labels from source documents into chunks.",
                    category="permission_risk",
                    business_domain=chunk.business_domain or (doc.business_domain if doc else None),
                )
            )
        if sensitive_detected and _permission_rank(label) <= 1:
            issues.append(
                self._issue(
                    object_type="chunk",
                    object_name=chunk.chunk_id,
                    issue_type="sensitive_chunk_public",
                    severity="critical",
                    evidence=[f"permission_label={label or 'blank'}", "sensitive token detected"],
                    risk="Sensitive content may leak through public retrieval.",
                    suggestion="Move sensitive chunks to a restricted index and add masking or access checks.",
                    category="permission_risk",
                    business_domain=chunk.business_domain or (doc.business_domain if doc else None),
                )
            )
        return issues

    def _assess_retrieval(
        self,
        retrieval_logs: list[RagRetrievalLog],
        documents_by_id: dict[str, RagKnowledgeDocument],
    ) -> list[RagQualityIssue]:
        issues: list[RagQualityIssue] = []
        logs_by_query: dict[str, list[RagRetrievalLog]] = defaultdict(list)
        for log in retrieval_logs:
            logs_by_query[log.query_id].append(log)
            if log.score is not None and log.score < self.low_retrieval_score:
                issues.append(
                    self._issue(
                        object_type="retrieval",
                        object_name=log.query_id,
                        issue_type="low_retrieval_score",
                        severity="medium",
                        evidence=[f"score={log.score}", f"threshold={self.low_retrieval_score}"],
                        risk="Top-k retrieval may not contain enough relevant evidence.",
                        suggestion="Review chunking, metadata filters, and query vocabulary.",
                        category="retrieval_quality",
                    )
                )
            if log.expected_document_id and log.retrieved_document_id and (
                log.expected_document_id != log.retrieved_document_id
            ) and log.rank == 1:
                issues.append(
                    self._issue(
                        object_type="retrieval",
                        object_name=log.query_id,
                        issue_type="top1_wrong_document",
                        severity="high",
                        evidence=[
                            f"expected_document_id={log.expected_document_id}",
                            f"retrieved_document_id={log.retrieved_document_id}",
                        ],
                        risk="The model may answer from the wrong policy or standard.",
                        suggestion="Improve metadata filters, synonyms, and reranking signals.",
                        category="retrieval_quality",
                    )
                )
            if log.retrieved_document_id:
                doc = documents_by_id.get(log.retrieved_document_id)
                if doc and _lower(doc.status) in DEPRECATED_STATUSES:
                    issues.append(
                        self._issue(
                            object_type="retrieval",
                            object_name=log.query_id,
                            issue_type="retrieved_deprecated_document",
                            severity="high",
                            evidence=[f"retrieved_document_id={doc.document_id}", f"status={doc.status}"],
                            risk="Answers may use obsolete policy content.",
                            suggestion="Exclude deprecated documents from retrieval.",
                            category="retrieval_quality",
                            business_domain=doc.business_domain,
                        )
                    )
            if (
                log.user_permission_label
                and log.retrieved_permission_label
                and _permission_rank(log.retrieved_permission_label) > _permission_rank(log.user_permission_label)
            ):
                issues.append(
                    self._issue(
                        object_type="retrieval",
                        object_name=log.query_id,
                        issue_type="retrieval_permission_leak",
                        severity="critical",
                        evidence=[
                            f"user_permission_label={log.user_permission_label}",
                            f"retrieved_permission_label={log.retrieved_permission_label}",
                        ],
                        risk="A user can retrieve documents beyond their permission level.",
                        suggestion="Enforce permission filters before vector retrieval and reranking.",
                        category="permission_risk",
                    )
                )
        for query_id, logs in logs_by_query.items():
            expected_ids = {log.expected_document_id for log in logs if log.expected_document_id}
            retrieved_ids = {log.retrieved_document_id for log in logs if log.retrieved_document_id}
            if expected_ids and not expected_ids.intersection(retrieved_ids):
                issues.append(
                    self._issue(
                        object_type="retrieval",
                        object_name=query_id,
                        issue_type="missing_expected_document_in_topk",
                        severity="high",
                        evidence=[
                            f"expected_document_ids={', '.join(sorted(expected_ids))}",
                            f"retrieved_document_ids={', '.join(sorted(retrieved_ids)) or 'none'}",
                        ],
                        risk="The answer may omit required policy evidence.",
                        suggestion="Tune retrieval filters, chunk titles, and domain tags.",
                        category="retrieval_quality",
                    )
                )
        return issues

    def _assess_answers(
        self,
        answer_evaluations: list[RagAnswerEvaluation],
    ) -> list[RagQualityIssue]:
        issues: list[RagQualityIssue] = []
        for answer in answer_evaluations:
            if not answer.cited_document_ids:
                issues.append(
                    self._issue(
                        object_type="answer",
                        object_name=answer.query_id,
                        issue_type="answer_missing_citation",
                        severity="high",
                        evidence=["cited_document_ids is empty"],
                        risk="Users cannot verify the answer source.",
                        suggestion="Require source citations in generated answers.",
                        category="answer_quality",
                    )
                )
            if answer.expected_document_ids and not set(answer.expected_document_ids).issubset(
                set(answer.cited_document_ids)
            ):
                issues.append(
                    self._issue(
                        object_type="answer",
                        object_name=answer.query_id,
                        issue_type="answer_missing_expected_source",
                        severity="high",
                        evidence=[
                            f"expected_document_ids={', '.join(answer.expected_document_ids)}",
                            f"cited_document_ids={', '.join(answer.cited_document_ids) or 'none'}",
                        ],
                        risk="The answer may be unsupported by the required authoritative document.",
                        suggestion="Improve retrieval grounding and answer citation checks.",
                        category="answer_quality",
                    )
                )
            if (
                answer.faithfulness_score is not None
                and answer.faithfulness_score < self.low_faithfulness_score
            ):
                issues.append(
                    self._issue(
                        object_type="answer",
                        object_name=answer.query_id,
                        issue_type="low_answer_faithfulness",
                        severity="high",
                        evidence=[
                            f"faithfulness_score={answer.faithfulness_score}",
                            f"threshold={self.low_faithfulness_score}",
                        ],
                        risk="The answer may not be faithful to retrieved evidence.",
                        suggestion="Add grounded-answer evaluation and block low-faithfulness responses.",
                        category="answer_quality",
                    )
                )
            flag_checks = [
                (answer.hallucination_flag, "answer_hallucination", "Answer contains unsupported claims."),
                (answer.mixed_policy_flag, "mixed_policy_answer", "Answer mixes multiple policy versions or scopes."),
                (answer.overextended_flag, "answer_overextended", "Answer goes beyond the provided evidence."),
                (answer.exposes_sensitive_content, "answer_sensitive_exposure", "Answer exposes sensitive content."),
            ]
            for flag, issue_type, risk in flag_checks:
                if not flag:
                    continue
                severity = "critical" if "sensitive" in issue_type else "high"
                issues.append(
                    self._issue(
                        object_type="answer",
                        object_name=answer.query_id,
                        issue_type=issue_type,
                        severity=severity,
                        evidence=[f"{issue_type}=true"],
                        risk=risk,
                        suggestion="Review retrieval context, prompt constraints, and answer safety checks.",
                        category="answer_quality" if issue_type != "answer_sensitive_exposure" else "permission_risk",
                    )
                )
        return issues

    @staticmethod
    def summarize(
        *,
        documents: list[RagKnowledgeDocument],
        chunks: list[RagKnowledgeChunk],
        retrieval_logs: list[RagRetrievalLog],
        answer_evaluations: list[RagAnswerEvaluation],
        issues: list[RagQualityIssue],
    ) -> dict[str, object]:
        """Build compact aggregate metrics for reports and dashboards."""
        severity_counts = Counter(issue.severity for issue in issues)
        category_counts = Counter(issue.category or "uncategorized" for issue in issues)
        issue_type_counts = Counter(issue.issue_type for issue in issues)
        critical_or_high = sum(
            count
            for severity, count in severity_counts.items()
            if severity in {"critical", "high"}
        )
        return {
            "document_count": len(documents),
            "chunk_count": len(chunks),
            "retrieval_log_count": len(retrieval_logs),
            "answer_evaluation_count": len(answer_evaluations),
            "issue_count": len(issues),
            "critical_or_high_issue_count": critical_or_high,
            "severity_counts": dict(severity_counts),
            "category_counts": dict(category_counts),
            "top_issue_types": dict(issue_type_counts.most_common(8)),
        }

    @staticmethod
    def _latest_version_by_title_source(
        documents: list[RagKnowledgeDocument],
    ) -> dict[tuple[str, str], str]:
        latest: dict[tuple[str, str], str] = {}
        for doc in documents:
            if not (doc.title and doc.source and doc.version):
                continue
            key = (_lower(doc.title), _lower(doc.source))
            version = _lower(doc.version)
            if key not in latest or version > latest[key]:
                latest[key] = version
        return latest

    def assess(
        self,
        *,
        documents: list[RagKnowledgeDocument] | None = None,
        chunks: list[RagKnowledgeChunk] | None = None,
        retrieval_logs: list[RagRetrievalLog] | None = None,
        answer_evaluations: list[RagAnswerEvaluation] | None = None,
    ) -> RagQualityAssessmentResult:
        """Run all configured RAG quality checks."""
        documents = list(documents or [])
        chunks = list(chunks or [])
        retrieval_logs = list(retrieval_logs or [])
        answer_evaluations = list(answer_evaluations or [])
        documents_by_id = {doc.document_id: doc for doc in documents}
        latest_version_by_title_source = self._latest_version_by_title_source(documents)
        issues: list[RagQualityIssue] = []
        issues.extend(self._assess_documents(documents, latest_version_by_title_source))
        issues.extend(self._assess_chunks(chunks, documents_by_id))
        issues.extend(self._assess_retrieval(retrieval_logs, documents_by_id))
        issues.extend(self._assess_answers(answer_evaluations))
        summary = self.summarize(
            documents=documents,
            chunks=chunks,
            retrieval_logs=retrieval_logs,
            answer_evaluations=answer_evaluations,
            issues=issues,
        )
        return RagQualityAssessmentResult(
            document_count=len(documents),
            chunk_count=len(chunks),
            retrieval_log_count=len(retrieval_logs),
            answer_evaluation_count=len(answer_evaluations),
            issue_count=len(issues),
            issues=issues,
            summary=summary,
        )
