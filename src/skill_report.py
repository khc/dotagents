import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Any, Literal, cast

from agents.project_root import project_root

OutputFormat = Literal["json", "markdown"]
ToolStatus = Literal["pass", "warn", "fail"]
Severity = Literal["error", "warning", "info"]


@dataclass
class ReportArgs:
    skill: Annotated[str, "Skill directory name under plugins/dot/skills/"]
    output: Annotated[OutputFormat, "Combined report output format"] = "json"
    start_path: Annotated[str, "Path used to resolve the project root"] = "."


@dataclass
class Finding:
    tool: str
    severity: Severity
    message: str
    location: str | None = None
    rule: str | None = None


@dataclass
class ToolReport:
    name: str
    command: list[str]
    exit_code: int
    status: ToolStatus
    summary: str
    findings: list[Finding]
    stdout: str
    stderr: str


@dataclass
class CombinedReport:
    skill: str
    skill_path: str
    overall_status: ToolStatus
    summary: dict[str, int]
    tools: list[ToolReport]


def generate_report(args: ReportArgs) -> str:
    root_dir = project_root(args.start_path)
    skill_dir = root_dir / "plugins" / "dot" / "skills" / args.skill
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        raise ValueError(f"skill file not found: {skill_file}")

    reports = [
        _run_skillcheck(root_dir, skill_file),
        _run_skills_validate(root_dir, skill_file),
        _run_skill_validator(root_dir, skill_dir),
        _run_cclint(root_dir, skill_file),
        _run_markdownlint(root_dir, skill_file),
    ]
    combined = CombinedReport(
        skill=args.skill,
        skill_path=str(skill_file),
        overall_status=_overall_status(reports),
        summary=_summary_counts(reports),
        tools=reports,
    )

    if args.output == "markdown":
        return _to_markdown(combined)
    return json.dumps(asdict(combined), indent=2)


def _run(
    root_dir: Path,
    command: list[str],
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(root_dir / ".task-cache" / "uv")
    return subprocess.run(
        command,
        cwd=root_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _run_skillcheck(root_dir: Path, skill_file: Path) -> ToolReport:
    command = [
        "uv",
        "run",
        "skillcheck",
        str(skill_file),
        "--strict",
        "--format",
        "json",
    ]
    result, payload, failure = _run_json_tool(root_dir, command, "skillcheck")
    if failure is not None:
        return failure
    payload = cast(dict[str, Any], payload)
    findings: list[Finding] = []
    for file_result in payload.get("results", []):
        for diagnostic in file_result.get("diagnostics", []):
            findings.append(
                Finding(
                    tool="skillcheck",
                    severity=_normalize_severity(diagnostic.get("severity", "info")),
                    message=diagnostic.get("message", ""),
                    location=_format_location(
                        file_result.get("path"),
                        diagnostic.get("line"),
                    ),
                    rule=diagnostic.get("rule"),
                )
            )
    status = _status_from_findings(findings)
    return ToolReport(
        name="skillcheck",
        command=command,
        exit_code=result.returncode,
        status=status,
        summary=f"{payload.get('files_passed', 0)} passed, {payload.get('files_failed', 0)} failed",
        findings=findings,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _run_skills_validate(root_dir: Path, skill_file: Path) -> ToolReport:
    command = ["uv", "run", "skills", "validate", str(skill_file)]
    result = _run(root_dir, command)
    output = (result.stdout + result.stderr).strip()
    findings: list[Finding] = []
    status: ToolStatus = "pass"
    summary = "valid skill"
    if result.returncode != 0:
        status = "fail"
        summary = "skills validate failed"
        messages = [line.strip() for line in output.splitlines() if line.strip()]
        findings = [
            Finding(tool="skills:validate", severity="error", message=message)
            for message in messages
        ]
    return ToolReport(
        name="skills:validate",
        command=command,
        exit_code=result.returncode,
        status=status,
        summary=summary,
        findings=findings,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _run_skill_validator(root_dir: Path, skill_dir: Path) -> ToolReport:
    command = ["skill-validator", "check", str(skill_dir), "-o", "json"]
    result, payload, failure = _run_json_tool(root_dir, command, "skill-validator")
    if failure is not None:
        return failure
    payload = cast(dict[str, Any], payload)
    findings: list[Finding] = []
    for item in payload.get("results", []):
        level = item.get("level")
        if level not in {"warning", "error", "info"}:
            continue
        findings.append(
            Finding(
                tool="skill-validator",
                severity=_normalize_severity(level),
                message=item.get("message", ""),
                location=item.get("file"),
                rule=item.get("category"),
            )
        )
    if payload.get("errors", 0) > 0:
        status: ToolStatus = "fail"
    elif payload.get("warnings", 0) > 0:
        status = "warn"
    else:
        status = "pass"
    summary = (
        f"{payload.get('errors', 0)} errors, {payload.get('warnings', 0)} warnings"
    )
    return ToolReport(
        name="skill-validator",
        command=command,
        exit_code=result.returncode,
        status=status,
        summary=summary,
        findings=findings,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _run_cclint(root_dir: Path, skill_file: Path) -> ToolReport:
    command = ["npx", "cclint", "lint", str(skill_file), "-f", "json"]
    result, payload, failure = _run_json_tool(root_dir, command, "cclint")
    if failure is not None:
        return failure
    payload = cast(dict[str, Any], payload)
    findings = [
        Finding(
            tool="cclint",
            severity=_normalize_severity(item.get("severity", "info")),
            message=item.get("message", ""),
            location=_format_location(
                payload.get("file"),
                item.get("location", {}).get("line"),
                item.get("location", {}).get("column"),
            ),
            rule=item.get("ruleId"),
        )
        for item in payload.get("violations", [])
    ]
    summary_data = payload.get("summary", {})
    status = _status_from_summary(
        errors=summary_data.get("errors", 0),
        warnings=summary_data.get("warnings", 0),
    )
    summary = (
        f"{summary_data.get('errors', 0)} errors, "
        f"{summary_data.get('warnings', 0)} warnings, "
        f"{summary_data.get('infos', 0)} info"
    )
    return ToolReport(
        name="cclint",
        command=command,
        exit_code=result.returncode,
        status=status,
        summary=summary,
        findings=findings,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _run_markdownlint(root_dir: Path, skill_file: Path) -> ToolReport:
    command = [
        "npx",
        "markdownlint-cli2",
        "--config",
        ".markdownlint-cli2.skills.yaml",
        str(skill_file),
    ]
    result = _run(root_dir, command)
    findings = _parse_markdownlint_output(result.stdout + result.stderr)
    if result.returncode != 0 and not findings:
        findings.append(
            Finding(
                tool="markdownlint",
                severity="error",
                message=_failure_message(
                    "markdownlint",
                    result,
                    "validator failed without parseable findings",
                ),
            )
        )
    status = _status_from_findings(findings)
    summary = f"{len(findings)} findings"
    return ToolReport(
        name="markdownlint",
        command=command,
        exit_code=result.returncode,
        status=status,
        summary=summary,
        findings=findings,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _parse_markdownlint_output(output: str) -> list[Finding]:
    findings: list[Finding] = []
    pattern = re.compile(
        r"^(?P<path>.+?):(?P<line>\d+)(?::(?P<column>\d+))?\s+"
        + r"(?P<severity>error|warning)\s+"
        + r"(?P<rule>[A-Za-z0-9/.-]+)\s+"
        + r"(?P<message>.+)$"
    )
    for line in output.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        findings.append(
            Finding(
                tool="markdownlint",
                severity=_normalize_severity(match.group("severity")),
                message=match.group("message"),
                location=_format_location(
                    match.group("path"),
                    int(match.group("line")),
                    int(match.group("column")) if match.group("column") else None,
                ),
                rule=match.group("rule"),
            )
        )
    return findings


def _run_json_tool(
    root_dir: Path,
    command: list[str],
    tool_name: str,
) -> tuple[
    subprocess.CompletedProcess[str], dict[str, object] | None, ToolReport | None
]:
    result = _run(root_dir, command)
    if not result.stdout.strip():
        return (
            result,
            None,
            _failure_report(
                tool_name,
                command,
                result,
                "validator exited without JSON output",
            ),
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return (
            result,
            None,
            _failure_report(
                tool_name,
                command,
                result,
                f"invalid JSON output: {exc.msg}",
            ),
        )
    return result, payload, None


def _failure_report(
    tool_name: str,
    command: list[str],
    result: subprocess.CompletedProcess[str],
    message: str,
) -> ToolReport:
    return ToolReport(
        name=tool_name,
        command=command,
        exit_code=result.returncode,
        status="fail",
        summary=message,
        findings=[
            Finding(
                tool=tool_name,
                severity="error",
                message=_failure_message(tool_name, result, message),
            )
        ],
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _failure_message(
    _tool_name: str,
    result: subprocess.CompletedProcess[str],
    message: str,
) -> str:
    details = (result.stderr or result.stdout).strip()
    if details:
        first_line = details.splitlines()[0]
        return f"{message}: {first_line}"
    return f"{message} (exit {result.returncode})"


def _normalize_severity(value: str) -> Severity:
    lowered = value.lower()
    if lowered in {"warning", "warn"}:
        return "warning"
    if lowered == "error":
        return "error"
    return "info"


def _status_from_findings(findings: list[Finding]) -> ToolStatus:
    if any(finding.severity == "error" for finding in findings):
        return "fail"
    if any(finding.severity == "warning" for finding in findings):
        return "warn"
    return "pass"


def _status_from_summary(errors: int, warnings: int) -> ToolStatus:
    if errors > 0:
        return "fail"
    if warnings > 0:
        return "warn"
    return "pass"


def _overall_status(reports: list[ToolReport]) -> ToolStatus:
    if any(report.status == "fail" for report in reports):
        return "fail"
    if any(report.status == "warn" for report in reports):
        return "warn"
    return "pass"


def _summary_counts(reports: list[ToolReport]) -> dict[str, int]:
    errors = 0
    warnings = 0
    infos = 0
    for report in reports:
        for finding in report.findings:
            if finding.severity == "error":
                errors += 1
            elif finding.severity == "warning":
                warnings += 1
            else:
                infos += 1
    return {
        "errors": errors,
        "warnings": warnings,
        "infos": infos,
        "tools_pass": sum(report.status == "pass" for report in reports),
        "tools_warn": sum(report.status == "warn" for report in reports),
        "tools_fail": sum(report.status == "fail" for report in reports),
    }


def _format_location(
    path: str | None,
    line: int | None,
    column: int | None = None,
) -> str | None:
    if path is None:
        return None
    if line is None:
        return path
    if column is None:
        return f"{path}:{line}"
    return f"{path}:{line}:{column}"


def _to_markdown(report: CombinedReport) -> str:
    lines = [
        "# Skill Report",
        "",
        f"- Skill: `{report.skill}`",
        f"- Path: `{report.skill_path}`",
        f"- Overall status: `{report.overall_status}`",
        (
            f"- Totals: {report.summary['errors']} errors, "
            f"{report.summary['warnings']} warnings, {report.summary['infos']} info"
        ),
        "",
    ]
    for tool in report.tools:
        lines.extend(
            [
                f"## {tool.name}",
                "",
                f"- Status: `{tool.status}`",
                f"- Exit code: `{tool.exit_code}`",
                f"- Summary: {tool.summary}",
                "",
            ]
        )
        if not tool.findings:
            lines.append("No findings.")
            lines.append("")
            continue
        for finding in tool.findings:
            location = f" `{finding.location}`" if finding.location else ""
            rule = f" [{finding.rule}]" if finding.rule else ""
            lines.append(f"- `{finding.severity}`{rule}{location} {finding.message}")
        lines.append("")
    return "\n".join(lines)
