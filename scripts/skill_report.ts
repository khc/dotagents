// Run every skill validator against one skill and print a combined report.
//
// Usage: bun scripts/skill_report.ts --skill <name> [--output json|markdown] [--start-path <path>]
import { join, resolve } from "node:path";
import { parseArgs } from "node:util";

type OutputFormat = "json" | "markdown";
type ToolStatus = "pass" | "warn" | "fail";
type Severity = "error" | "warning" | "info";
type Json = Record<string, any>;

export interface ReportArgs {
  skill: string;
  output: OutputFormat;
  startPath: string;
}

export interface Finding {
  tool: string;
  severity: Severity;
  message: string;
  location: string | null;
  rule: string | null;
}

export interface ToolReport {
  name: string;
  command: string[];
  exit_code: number;
  status: ToolStatus;
  summary: string;
  findings: Finding[];
  stdout: string;
  stderr: string;
}

export interface CombinedReport {
  skill: string;
  skill_path: string;
  overall_status: ToolStatus;
  summary: Record<string, number>;
  tools: ToolReport[];
}

export interface RunResult {
  exitCode: number;
  stdout: string;
  stderr: string;
}

export type Run = (command: string[]) => RunResult;

const finding = (
  tool: string,
  severity: Severity,
  message: string,
  location: string | null = null,
  rule: string | null = null,
): Finding => ({ tool, severity, message, location, rule });

export function projectRoot(startPath: string): string {
  const start = resolve(startPath);
  const result = Bun.spawnSync(["git", "rev-parse", "--show-toplevel"], { cwd: start });
  return result.exitCode === 0 ? result.stdout.toString().trim() : start;
}

export function commandRunner(rootDir: string): Run {
  const env = { ...process.env, UV_CACHE_DIR: join(rootDir, ".task-cache", "uv") };
  return (command) => {
    const result = Bun.spawnSync(command, { cwd: rootDir, env });
    return {
      exitCode: result.exitCode ?? -1,
      stdout: result.stdout.toString(),
      stderr: result.stderr.toString(),
    };
  };
}

export async function generateReport(args: ReportArgs, makeRun = commandRunner): Promise<string> {
  const rootDir = projectRoot(args.startPath);
  const skillDir = join(rootDir, "plugins", "dot", "skills", args.skill);
  const skillFile = join(skillDir, "SKILL.md");
  if (!(await Bun.file(skillFile).exists())) {
    throw new Error(`skill file not found: ${skillFile}`);
  }

  const run = makeRun(rootDir);
  const tools = [
    runSkillcheck(run, skillFile),
    runSkillsValidate(run, skillFile),
    runSkillValidator(run, skillDir),
    runCclint(run, skillFile),
    runMarkdownlint(run, skillFile),
  ];
  const combined: CombinedReport = {
    skill: args.skill,
    skill_path: skillFile,
    overall_status: overallStatus(tools),
    summary: summaryCounts(tools),
    tools,
  };
  return args.output === "markdown" ? toMarkdown(combined) : JSON.stringify(combined, null, 2);
}

function runSkillcheck(run: Run, skillFile: string): ToolReport {
  const command = ["uv", "run", "skillcheck", skillFile, "--strict", "--format", "json"];
  const [result, payload, failure] = runJsonTool(run, command, "skillcheck");
  if (failure) return failure;

  const findings = (payload.results ?? []).flatMap((file: Json) =>
    (file.diagnostics ?? []).map((d: Json) =>
      finding(
        "skillcheck",
        normalizeSeverity(d.severity ?? "info"),
        d.message ?? "",
        formatLocation(file.path, d.line),
        d.rule ?? null,
      ),
    ),
  );
  return {
    name: "skillcheck",
    command,
    exit_code: result.exitCode,
    status: statusFromFindings(findings),
    summary: `${payload.files_passed ?? 0} passed, ${payload.files_failed ?? 0} failed`,
    findings,
    stdout: result.stdout,
    stderr: result.stderr,
  };
}

function runSkillsValidate(run: Run, skillFile: string): ToolReport {
  const command = ["uv", "run", "skills", "validate", skillFile];
  const result = run(command);
  const failed = result.exitCode !== 0;
  const messages = (result.stdout + result.stderr)
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  return {
    name: "skills:validate",
    command,
    exit_code: result.exitCode,
    status: failed ? "fail" : "pass",
    summary: failed ? "skills validate failed" : "valid skill",
    findings: failed ? messages.map((m) => finding("skills:validate", "error", m)) : [],
    stdout: result.stdout,
    stderr: result.stderr,
  };
}

function runSkillValidator(run: Run, skillDir: string): ToolReport {
  const command = ["skill-validator", "check", skillDir, "-o", "json"];
  const [result, payload, failure] = runJsonTool(run, command, "skill-validator");
  if (failure) return failure;

  const findings = (payload.results ?? [])
    .filter((item: Json) => ["warning", "error", "info"].includes(item.level))
    .map((item: Json) =>
      finding(
        "skill-validator",
        normalizeSeverity(item.level),
        item.message ?? "",
        item.file ?? null,
        item.category ?? null,
      ),
    );
  const errors = payload.errors ?? 0;
  const warnings = payload.warnings ?? 0;
  return {
    name: "skill-validator",
    command,
    exit_code: result.exitCode,
    status: statusFromSummary(errors, warnings),
    summary: `${errors} errors, ${warnings} warnings`,
    findings,
    stdout: result.stdout,
    stderr: result.stderr,
  };
}

function runCclint(run: Run, skillFile: string): ToolReport {
  const command = ["bunx", "cclint", "lint", skillFile, "-f", "json"];
  const [result, payload, failure] = runJsonTool(run, command, "cclint");
  if (failure) return failure;

  const findings = (payload.violations ?? []).map((v: Json) =>
    finding(
      "cclint",
      normalizeSeverity(v.severity ?? "info"),
      v.message ?? "",
      formatLocation(payload.file, v.location?.line, v.location?.column),
      v.ruleId ?? null,
    ),
  );
  const { errors = 0, warnings = 0, infos = 0 } = payload.summary ?? {};
  return {
    name: "cclint",
    command,
    exit_code: result.exitCode,
    status: statusFromSummary(errors, warnings),
    summary: `${errors} errors, ${warnings} warnings, ${infos} info`,
    findings,
    stdout: result.stdout,
    stderr: result.stderr,
  };
}

function runMarkdownlint(run: Run, skillFile: string): ToolReport {
  const command = ["bunx", "markdownlint-cli2", "--config", ".markdownlint-cli2.skills.yaml", skillFile];
  const result = run(command);
  const findings = parseMarkdownlintOutput(result.stdout + result.stderr);
  if (result.exitCode !== 0 && findings.length === 0) {
    const message = failureMessage(result, "validator failed without parseable findings");
    findings.push(finding("markdownlint", "error", message));
  }
  return {
    name: "markdownlint",
    command,
    exit_code: result.exitCode,
    status: statusFromFindings(findings),
    summary: `${findings.length} findings`,
    findings,
    stdout: result.stdout,
    stderr: result.stderr,
  };
}

const MARKDOWNLINT_LINE =
  /^(?<path>.+?):(?<line>\d+)(?::(?<column>\d+))?\s+(?<severity>error|warning)\s+(?<rule>[A-Za-z0-9/.-]+)\s+(?<message>.+)$/;

function parseMarkdownlintOutput(output: string): Finding[] {
  return output.split("\n").flatMap((line) => {
    const groups = MARKDOWNLINT_LINE.exec(line.trim())?.groups;
    if (!groups) return [];
    const column = groups.column ? Number(groups.column) : undefined;
    return [
      finding(
        "markdownlint",
        normalizeSeverity(groups.severity!),
        groups.message!,
        formatLocation(groups.path, Number(groups.line), column),
        groups.rule!,
      ),
    ];
  });
}

function runJsonTool(run: Run, command: string[], tool: string): [RunResult, Json, null] | [RunResult, null, ToolReport] {
  const result = run(command);
  if (!result.stdout.trim()) {
    return [result, null, failureReport(tool, command, result, "validator exited without JSON output")];
  }
  try {
    return [result, JSON.parse(result.stdout), null];
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    return [result, null, failureReport(tool, command, result, `invalid JSON output: ${reason}`)];
  }
}

function failureReport(tool: string, command: string[], result: RunResult, message: string): ToolReport {
  return {
    name: tool,
    command,
    exit_code: result.exitCode,
    status: "fail",
    summary: message,
    findings: [finding(tool, "error", failureMessage(result, message))],
    stdout: result.stdout,
    stderr: result.stderr,
  };
}

function failureMessage(result: RunResult, message: string): string {
  const details = (result.stderr || result.stdout).trim();
  return details ? `${message}: ${details.split("\n")[0]}` : `${message} (exit ${result.exitCode})`;
}

function normalizeSeverity(value: string): Severity {
  const lowered = value.toLowerCase();
  if (lowered === "warning" || lowered === "warn") return "warning";
  return lowered === "error" ? "error" : "info";
}

function statusFromSummary(errors: number, warnings: number): ToolStatus {
  if (errors > 0) return "fail";
  return warnings > 0 ? "warn" : "pass";
}

function statusFromFindings(findings: Finding[]): ToolStatus {
  return statusFromSummary(
    findings.filter((f) => f.severity === "error").length,
    findings.filter((f) => f.severity === "warning").length,
  );
}

function overallStatus(tools: ToolReport[]): ToolStatus {
  if (tools.some((t) => t.status === "fail")) return "fail";
  return tools.some((t) => t.status === "warn") ? "warn" : "pass";
}

function summaryCounts(tools: ToolReport[]): Record<string, number> {
  const findings = tools.flatMap((t) => t.findings);
  const count = (severity: Severity) => findings.filter((f) => f.severity === severity).length;
  const toolsWith = (status: ToolStatus) => tools.filter((t) => t.status === status).length;
  return {
    errors: count("error"),
    warnings: count("warning"),
    infos: count("info"),
    tools_pass: toolsWith("pass"),
    tools_warn: toolsWith("warn"),
    tools_fail: toolsWith("fail"),
  };
}

function formatLocation(path?: string | null, line?: number | null, column?: number | null): string | null {
  if (path == null) return null;
  if (line == null) return path;
  return column == null ? `${path}:${line}` : `${path}:${line}:${column}`;
}

function toMarkdown(report: CombinedReport): string {
  const { errors, warnings, infos } = report.summary;
  const lines = [
    "# Skill Report",
    "",
    `- Skill: \`${report.skill}\``,
    `- Path: \`${report.skill_path}\``,
    `- Overall status: \`${report.overall_status}\``,
    `- Totals: ${errors} errors, ${warnings} warnings, ${infos} info`,
    "",
  ];
  for (const tool of report.tools) {
    lines.push(
      `## ${tool.name}`,
      "",
      `- Status: \`${tool.status}\``,
      `- Exit code: \`${tool.exit_code}\``,
      `- Summary: ${tool.summary}`,
      "",
    );
    if (tool.findings.length === 0) {
      lines.push("No findings.", "");
      continue;
    }
    for (const f of tool.findings) {
      const location = f.location ? ` \`${f.location}\`` : "";
      const rule = f.rule ? ` [${f.rule}]` : "";
      lines.push(`- \`${f.severity}\`${rule}${location} ${f.message}`);
    }
    lines.push("");
  }
  return lines.join("\n");
}

if (import.meta.main) {
  const { values } = parseArgs({
    options: {
      skill: { type: "string" },
      output: { type: "string", default: "json" },
      "start-path": { type: "string", default: "." },
    },
  });
  if (!values.skill) throw new Error("--skill is required");
  if (values.output !== "json" && values.output !== "markdown") {
    throw new Error("--output must be json or markdown");
  }
  console.log(await generateReport({ skill: values.skill, output: values.output, startPath: values["start-path"]! }));
}
