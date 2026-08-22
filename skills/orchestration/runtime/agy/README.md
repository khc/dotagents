# Agy / Antigravity Runtime

Agy has a native `invoke_subagent` tool. Use the repository custom agents in
`runtime/agy/agents/` (or copy them to `.agents/agents/`).

## Install

From the project root:

```bash
mkdir -p .agents/agents
cp runtime/agy/agents/*.md .agents/agents/
```

Ensure the six lifecycle skills plus `orchestrate` are discoverable by Agy.

## Run

Ask the main Agy agent:

```text
Invoke $orchestrate.

Workflow: feature
Scope: <path>
Request: <task>

Use invoke_subagent for every lifecycle stage and use the custom roles:
workflow-planner, workflow-builder, workflow-reviewer, workflow-fixer.
Persist handoff artifacts under <scope>/.workflow/<workflow-id>/artifacts/.
Do not pass conversation transcripts between agents.
```

For `planned` or `review`, change the Workflow value.

## Native invocation contract

The parent invokes a fresh custom subagent with `invoke_subagent`, using
workspace `inherit` for this serial workflow. The parent waits for the stage
artifact/result, applies the transition table in `SKILL.md`, then invokes the
next fresh agent.

Reviewer invocations must always be new subagents, including re-review.

Do not use transcript-reading/inter-agent history as a handoff mechanism even
though Agy can expose transcripts; the workflow deliberately uses artifacts.
