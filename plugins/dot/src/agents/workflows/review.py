import json
import re
from dataclasses import dataclass
from typing import Annotated, Any

from agents.context_loader import ContextInput, load_context
from agents.project_root import project_root
from agents.sidecar import add_sidecar_entry

SCHEMA_VERSION = 2
UNAVAILABLE = "unavailable"

CATEGORIES = {
    "Security",
    "Bugs",
    "Design",
    "Performance",
    "Maintainability",
    "Observability",
    "Testing",
    "Requirements / Plan",
    "Production Readiness",
    "Documentation",
    "Library / Reuse",
}
SEVERITIES = {"critical", "high", "medium", "low"}
CONFIDENCES = {"confirmed", "likely"}
STATUSES = {"open", "addressed", "deferred"}
EVIDENCE_SOURCES = {"direct", "lens", "research"}
REVIEW_MODES = {"change", "path", "symbol"}
SOURCE_WORKFLOWS = {"feature", "implement", "bug", "refactor", "fix", "standalone"}
VERDICTS = {"ready", "ready-with-fixes", "not-ready"}
FINDING_ID = re.compile(r"F[0-9]+")


@dataclass
class Args:
    agent: Annotated[str, "Agent runtime identifier"]
    context: Annotated[str, "Review context JSON payload, file path, or - for stdin"]
    scope: Annotated[str | None, "Active scope path within the project"] = None
    model: Annotated[str | None, "Model name used by the agent"] = None
    start_path: Annotated[str, "Path used to resolve the project root"] = "."
    context_input: Annotated[
        ContextInput,
        "How to interpret --context: inline JSON, a file path, or stdin",
    ] = "inline"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f"invalid review context: {message}")


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _open_blocking(finding: dict[str, Any]) -> bool:
    return finding["status"] == "open" and finding["blocking"]


def aggregate_verdict(
    findings: list[dict[str, Any]], verification_gaps: list[dict[str, Any]]
) -> str:
    if any(gap["material"] for gap in verification_gaps):
        return "not-ready"
    blocking = [f for f in findings if _open_blocking(f)]
    if any(f["severity"] in {"critical", "high"} for f in blocking):
        return "not-ready"
    return "ready-with-fixes" if blocking else "ready"


def _validate_evidence_ref(ref: Any, where: str) -> None:
    _require(isinstance(ref, dict), f"{where} must be an object")
    _require(ref.get("source") in EVIDENCE_SOURCES, f"{where}.source must be one of {sorted(EVIDENCE_SOURCES)}")
    _require(_text(ref.get("location")), f"{where}.location is required")
    if ref["source"] == "research":
        _require(_text(ref.get("url")) and _text(ref.get("quote")), f"{where} needs url and quote for research")


def _validate_finding(finding: Any, index: int) -> None:
    where = f"findings[{index}]"
    _require(isinstance(finding, dict), f"{where} must be an object")
    _require(FINDING_ID.fullmatch(str(finding.get("finding_id", ""))) is not None, f"{where}.finding_id must look like F<n>")
    _require(finding.get("category") in CATEGORIES, f"{where}.category must be one of {sorted(CATEGORIES)}")
    _require(finding.get("severity") in SEVERITIES, f"{where}.severity must be one of {sorted(SEVERITIES)}")
    _require(finding.get("confidence") in CONFIDENCES, f"{where}.confidence must be one of {sorted(CONFIDENCES)}")
    _require(finding.get("status") in STATUSES, f"{where}.status must be one of {sorted(STATUSES)}")
    _require(isinstance(finding.get("blocking"), bool), f"{where}.blocking must be a boolean")
    for key in ("location", "description", "fix_direction"):
        _require(_text(finding.get(key)), f"{where}.{key} is required")
    _require(isinstance(finding.get("evidence_refs"), list), f"{where}.evidence_refs must be a list")
    for ref_index, ref in enumerate(finding["evidence_refs"]):
        _validate_evidence_ref(ref, f"{where}.evidence_refs[{ref_index}]")
    if finding["severity"] in {"critical", "high"} and not finding["blocking"]:
        disposition = finding.get("disposition")
        _require(
            isinstance(disposition, dict) and _text(disposition.get("authority")) and _text(disposition.get("rationale")),
            f"{where} is non-blocking {finding['severity']} and needs disposition with authority and rationale",
        )


def _validate_gap(gap: Any, index: int) -> None:
    where = f"verification_gaps[{index}]"
    _require(isinstance(gap, dict), f"{where} must be an object")
    _require(_text(gap.get("description")), f"{where}.description is required")
    _require(isinstance(gap.get("material"), bool), f"{where}.material must be a boolean")
    _require(_text(gap.get("effect")), f"{where}.effect is required")


def validate_review_context(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict) or "schema_version" not in context:
        return context  # legacy v1: stored as written
    _require(context["schema_version"] == SCHEMA_VERSION, f"schema_version must be {SCHEMA_VERSION}")
    _require(context.get("review_mode") in REVIEW_MODES, f"review_mode must be one of {sorted(REVIEW_MODES)}")
    _require(context.get("source_workflow") in SOURCE_WORKFLOWS, f"source_workflow must be one of {sorted(SOURCE_WORKFLOWS)}")
    for key in ("target", "summary", "reasoning"):
        _require(_text(context.get(key)), f"{key} is required")
    _require(isinstance(context.get("findings"), list), "findings must be a list")
    _require(isinstance(context.get("verification_gaps"), list), "verification_gaps must be a list")
    for index, finding in enumerate(context["findings"]):
        _validate_finding(finding, index)
    for index, gap in enumerate(context["verification_gaps"]):
        _validate_gap(gap, index)
    ids = [finding["finding_id"] for finding in context["findings"]]
    _require(len(ids) == len(set(ids)), "finding_id values must be unique")
    expected = aggregate_verdict(context["findings"], context["verification_gaps"])
    _require(
        context.get("verdict") == expected,
        f"verdict {context.get('verdict')!r} disagrees with the findings and gaps, which give {expected!r}",
    )
    return context


def read_review_context(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict) or context.get("schema_version") == SCHEMA_VERSION:
        return context
    legacy_fields = {"finding_id": UNAVAILABLE, "blocking": UNAVAILABLE, "evidence_refs": UNAVAILABLE}
    findings = [{**legacy_fields, **finding} for finding in context.get("findings", [])]
    return {
        **context,
        "schema_version": 1,
        "findings": findings,
        "verification_gaps": UNAVAILABLE,
        "subject": UNAVAILABLE,
    }


def review_workflow(args: Args) -> str:
    context_json = load_context(args.context, args.context_input)
    validate_review_context(json.loads(context_json))

    root_dir = project_root(args.start_path)
    sidecar_dir = root_dir / ".sidecar"
    sidecar_dir.mkdir(parents=True, exist_ok=True)

    return add_sidecar_entry(
        db_path=str(sidecar_dir / "sidecar.db"),
        project=root_dir.name,
        skill="review",
        scope=args.scope,
        agent=args.agent,
        model=args.model or f"{args.agent}/unknown",
        context=context_json,
    )
