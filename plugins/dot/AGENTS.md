# dot plugin

## Versioning

- Every change to this plugin requires a [semver](https://semver.org) bump of `version`.
- Bump `version` in both manifests and keep them identical:
  - `plugin.json`
  - `.claude-plugin/plugin.json`
- Patch: fixes, wording, docs, evals. Minor: new or changed skill behavior, new skills, scripts. Major: breaking changes (renamed or removed skills, changed handoff contracts).

## Skills

- Every skill under `skills/` must comply with the [Agent Skills specification](https://agentskills.io/specification).
- Each skill is a directory `skills/<name>/` containing `SKILL.md`; the `name` frontmatter field must equal the directory name.
- Frontmatter requirements:
  - `name`: 1-64 chars, lowercase letters, digits, and hyphens only; no leading/trailing/consecutive hyphens.
  - `description`: 1-1024 chars; states what the skill does and when to use it.
  - Optional: `license`, `compatibility` (max 500 chars), `metadata`, `allowed-tools`.
- Keep `SKILL.md` under 500 lines; move detail into `references/`, `scripts/`, or `assets/` and reference them by relative path.
- Validate with `skills-ref validate skills/<name>` when changing a skill.
