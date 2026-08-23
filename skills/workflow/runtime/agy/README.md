# Agy / Antigravity Runtime

Agy has a native `invoke_subagent` tool. Use the repository custom agents in
`runtime/agy/agents/` (or copy them to `.agents/agents/`).

## Install

From the project root:

```bash
mkdir -p .agents/agents
cp runtime/agy/agents/*.md .agents/agents/
```

Ensure the six lifecycle skills plus `workflow` are discoverable by Agy.

## Run

Ask the main Agy agent:

```text
Invoke $workflow.

Workflow: feature
Scope: <path>
Request: <task>

Use invoke_subagent for every lifecycle stage and use the custom roles:
workflow-planner, workflow-builder, workflow-reviewer, workflow-fixer.
Persist handoff artifacts under <scope>/.workflow/<workflow-id>/artifacts/.
Do not pass conversation transcripts between agents.
```

For `refactor`, `bug`, `planned`, or `review`, change the Workflow value.

## Native invocation contract

The parent invokes a fresh custom subagent with `invoke_subagent`, using
workspace `inherit` for this serial workflow. The parent waits for the stage
artifact/result, applies the transition table in `SKILL.md`, then invokes the
next fresh agent.

Reviewer invocations must always be new subagents, including re-review.

Do not use transcript-reading/inter-agent history as a handoff mechanism even
though Agy can expose transcripts; the workflow deliberately uses artifacts.


## Mandatory result normalization

For every subagent, the parent must read the final `<ORCHESTRATION_RESULT>` envelope and apply the transition table.

For review specifically:

```text
verdict = ready && findings_count = 0
    → status = ready
    → DONE

verdict = ready-with-fixes && findings_count > 0
    → status = findings
    → invoke_subagent(workflow-fixer)

verdict = not-ready && findings_count > 0
    → status = findings
    → invoke_subagent(workflow-fixer)
```

Do not use the English word `ready` inside `ready-with-fixes` as a completion signal.

If the envelope is absent, malformed, or inconsistent with the normal review output, use the stricter interpretation and do not terminate the workflow:
- any concrete findings → invoke fixer
- any blocker → stop blocked
- only exact verdict `ready` with no findings may complete
