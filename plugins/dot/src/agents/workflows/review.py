import json
import re
from dataclasses import dataclass
from typing import Annotated, Any

from agents.context_loader import ContextInput, load_context
from agents.project_root import project_root
from agents.redact import redact_value
from agents.sidecar import add_sidecar_entry, get_sidecar_entry
from agents.workflows.review_strategy import LENSES
from agents.workflows.review_subject import is_stale

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
    findings: list[dict[str, Any]], verification_gaps: list[dict[str, Any]], stale: bool = False
) -> str:
    if stale or any(gap["material"] for gap in verification_gaps):
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
    disposition = finding.get("disposition")
    has_disposition = (
        isinstance(disposition, dict) and _text(disposition.get("authority")) and _text(disposition.get("rationale"))
    )
    if finding["severity"] in {"critical", "high"} and not finding["blocking"]:
        _require(has_disposition, f"{where} is non-blocking {finding['severity']} and needs disposition with authority and rationale")
    if finding["status"] == "deferred":
        _require(has_disposition, f"{where} is deferred and needs disposition with authority and rationale")
    if finding["status"] == "addressed":
        _require(
            any(ref["source"] == "direct" for ref in finding["evidence_refs"]),
            f"{where} is addressed and needs a direct evidence_ref inspected by the reviewer",
        )


SUBJECT_KINDS = {"commit_range", "index", "working_tree", "artifact"}


def _validate_subject(subject: Any, context: dict[str, Any]) -> None:
    _require(isinstance(subject, dict), "subject must be an object")
    kind = subject.get("kind")
    _require(kind in SUBJECT_KINDS, f"subject.kind must be one of {sorted(SUBJECT_KINDS)}")
    _require(_text(subject.get("repo_root")), "subject.repo_root is required")
    _require(subject.get("review_mode") == context["review_mode"], "subject.review_mode must equal review_mode")
    hashes = subject.get("content_hashes")
    _require(isinstance(hashes, list), "subject.content_hashes must be a list")
    for index, entry in enumerate(hashes):
        _require(
            isinstance(entry, dict) and _text(entry.get("path")) and _text(entry.get("sha256")),
            f"subject.content_hashes[{index}] needs path and sha256",
        )
    if kind == "artifact":
        _require(bool(hashes), "an artifact subject needs at least one content hash")
        return
    _require(_text(subject.get("head")), f"a {kind} subject needs head")
    if kind == "commit_range":
        _require(_text(subject.get("base")), "a commit_range subject needs base")
    else:
        _require(_text(subject.get("diff_sha256")), f"a {kind} subject needs diff_sha256; head alone does not identify uncommitted state")
    if context["review_mode"] == "change":
        _require(_text(subject.get("base_justification")), "a change review needs subject.base_justification")


STRATEGIES = {"single", "agents"}
OVERRIDES = {"none", "single", "agents"}
RESEARCH = {"not_needed", "used", "unavailable"}
LENS_STATUSES = {"completed", "failed", "skipped"}


def _validate_execution(execution: Any, context: dict[str, Any]) -> None:
    _require(isinstance(execution, dict), "execution must be an object")
    _require(execution.get("strategy") in STRATEGIES, f"execution.strategy must be one of {sorted(STRATEGIES)}")
    _require(execution.get("override") in OVERRIDES, f"execution.override must be one of {sorted(OVERRIDES)}")
    _require(_text(execution.get("reason")), "execution.reason is required")
    _require(isinstance(execution.get("signals"), dict), "execution.signals must be an object")
    _require(execution.get("research") in RESEARCH, f"execution.research must be one of {sorted(RESEARCH)}")
    _require(isinstance(execution.get("research_excerpt_authorized"), bool), "execution.research_excerpt_authorized must be a boolean")
    lenses = execution.get("lenses")
    _require(isinstance(lenses, list), "execution.lenses must be a list")
    for index, lens in enumerate(lenses):
        where = f"execution.lenses[{index}]"
        _require(isinstance(lens, dict) and lens.get("name") in LENSES, f"{where}.name must be one of {sorted(LENSES)}")
        _require(lens.get("status") in LENS_STATUSES, f"{where}.status must be one of {sorted(LENS_STATUSES)}")
    names = [lens["name"] for lens in lenses]
    _require(len(names) == len(set(names)), "execution.lenses must not repeat a lens")
    if execution["strategy"] == "single":
        _require(not lenses, "a single-agent review cannot list lenses")
    else:
        _require(bool(lenses), "an agents review must list its lenses")
    override = execution["override"]
    if override == "single":
        _require(execution["strategy"] == "single", "override single requires strategy single")
    if override == "agents" and execution["strategy"] == "single":
        _require(_text(execution.get("fallback")), "override agents ran as single without a recorded fallback")
    gaps = context["verification_gaps"]
    if any(lens["status"] != "completed" for lens in lenses):
        _require(any(gap["material"] for gap in gaps), "a failed or skipped lens needs a material verification gap")
    if execution["research"] == "unavailable":
        _require(bool(gaps), "research unavailable needs a verification gap for the affected finding")
    sources = {ref["source"] for finding in context["findings"] for ref in finding["evidence_refs"]}
    _require("research" not in sources or execution["research"] == "used", "research evidence needs execution.research = used")
    for index, finding in enumerate(context["findings"]):
        lens = finding.get("lens")
        _require(lens is None or lens in names, f"findings[{index}].lens must be null or a listed lens")


def _validate_observation(observation: Any, index: int) -> None:
    where = f"observations[{index}]"
    _require(isinstance(observation, dict), f"{where} must be an object")
    _require(_text(observation.get("location")) and _text(observation.get("description")), f"{where} needs location and description")


def check_continuity(context: dict[str, Any], prior: dict[str, Any]) -> None:
    prior_findings = prior.get("findings")
    if not isinstance(prior_findings, list):
        return
    current = {finding["finding_id"] for finding in context["findings"]}
    for finding in prior_findings:
        finding_id = finding.get("finding_id")
        if finding_id in (None, UNAVAILABLE):
            continue  # legacy finding: no identity to carry
        _require(
            finding.get("status") != "open" or finding_id in current,
            f"prior open finding {finding_id} is missing from the re-review; carry it with a status",
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
    observations = context.get("observations", [])
    _require(isinstance(observations, list), "observations must be a list")
    for index, observation in enumerate(observations):
        _validate_observation(observation, index)
    prior_uuid = context.get("prior_review_uuid")
    _require(prior_uuid is None or _text(prior_uuid), "prior_review_uuid must be a non-empty string")
    ids = [finding["finding_id"] for finding in context["findings"]]
    _require(len(ids) == len(set(ids)), "finding_id values must be unique")
    _validate_subject(context.get("subject"), context)
    _validate_execution(context.get("execution"), context)
    stale = context.get("stale", False)
    _require(isinstance(stale, bool), "stale must be a boolean")
    expected = aggregate_verdict(context["findings"], context["verification_gaps"], stale)
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


def _prior_context(db_path: str, review_uuid: str) -> dict[str, Any]:
    entries = get_sidecar_entry(db_path=db_path, uuid=review_uuid, limit=1)
    _require(bool(entries) and entries[0]["skill"] == "review", f"prior_review_uuid {review_uuid} is not a saved review")
    return read_review_context(json.loads(entries[0]["context"]))


def review_workflow(args: Args) -> str:
    context_json = load_context(args.context, args.context_input)
    context = json.loads(context_json)
    validate_review_context(context)

    root_dir = project_root(args.start_path)
    sidecar_dir = root_dir / ".sidecar"
    db_path = str(sidecar_dir / "sidecar.db")
    if isinstance(context, dict) and context.get("prior_review_uuid"):
        check_continuity(context, _prior_context(db_path, context["prior_review_uuid"]))
    if isinstance(context, dict) and "subject" in context and not context.get("stale"):
        _require(not is_stale(context["subject"]), "reviewed material changed since the subject was captured; re-inspect it or set stale: true")
    sidecar_dir.mkdir(parents=True, exist_ok=True)

    redacted = redact_value(context)
    return add_sidecar_entry(
        db_path=db_path,
        project=root_dir.name,
        skill="review",
        scope=args.scope,
        agent=args.agent,
        model=args.model or f"{args.agent}/unknown",
        context=json.dumps(redacted) if redacted != context else context_json,
    )
