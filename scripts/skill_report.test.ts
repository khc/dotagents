import { expect, test } from "bun:test";
import { join, resolve } from "node:path";
import { generateReport, type Run } from "./skill_report";

const ROOT = resolve(import.meta.dir, "..");
const passingRun: Run = () => ({ exitCode: 0, stdout: "{}", stderr: "" });

test("report uses the plugin skill path", async () => {
  const report = JSON.parse(
    await generateReport({ skill: "scope", output: "json", startPath: ROOT }, () => passingRun),
  );

  expect(report.skill).toBe("scope");
  expect(report.skill_path).toBe(join(ROOT, "plugins/dot/skills/scope/SKILL.md"));
  expect(report.overall_status).toBe("pass");
  expect(Object.keys(report).sort()).toEqual(["overall_status", "skill", "skill_path", "summary", "tools"]);
});

test("report fails when a validator emits no JSON", async () => {
  const silent: Run = () => ({ exitCode: 1, stdout: "", stderr: "boom\nmore" });
  const report = JSON.parse(
    await generateReport({ skill: "scope", output: "json", startPath: ROOT }, () => silent),
  );

  expect(report.overall_status).toBe("fail");
  expect(report.tools[0].findings[0].message).toBe("validator exited without JSON output: boom");
});

test("report rejects an unknown skill", async () => {
  await expect(
    generateReport({ skill: "missing", output: "json", startPath: ROOT }, () => passingRun),
  ).rejects.toThrow("skill file not found");
});
