# Privacy

Last updated: 2026-10-28

The dotagents plugin (`dot`) is a set of skills and local helper scripts. It has no server, account, analytics, or telemetry, and its own code makes no network requests.

## What the plugin stores

All data stays on your machine, inside the project you run it in:

- `.plans/` holds implementation plans.
- `.sidecar/` holds a local SQLite database of saved reviews and fixes.
- `.workflow/<id>/` under the active scope holds workflow requests and stage artifacts.

The plugin does not read credentials from your environment and does not store any. Reviews write `[REDACTED:<type>]` in place of secret values, and the helpers redact common credential shapes before saving. Redaction is a safeguard, not a guarantee, so keep secrets out of reviewed material where you can. The plugin does not look for personal data. If reviewed files contain any (for example names or email addresses in code or comments), a saved review may quote it in these local folders. Delete these folders to remove the data.

## What leaves your machine

The plugin sends nothing to its author. Content leaves your machine only through tools you already use, when a skill tells them to:

- **Agent CLIs.** The workflow runner starts fresh `claude`, `codex`, or `agy` processes and passes them the stage prompt and the files it writes under `.workflow/`. Those tools send that content to their own providers under their own terms and privacy policies.
- **Web research.** `dot:web-research` asks an agent with web access to look up external facts. The skill passes identifiers only (library and API names, versions, error strings). It does not pass repository text unless you authorize an excerpt, and it redacts credentials first.
- **Package downloads.** On first run, `uv` downloads the pinned `tyro==1.0.13` package for the helper scripts.
- **Skills CLI.** `dot:find-skills` runs `npx skills@1.7.4` only when you ask it to find or install a skill.

## Children

The plugin is a developer tool and is not directed at people under 18.

## Changes and contact

Changes to this policy are recorded in this file's git history. For questions, open an issue at https://github.com/khc/agents/issues.
