# Development

The `dot` plugin lives in `plugins/dot/` and is exposed to each host through a marketplace catalog:

| Host | Catalog | Plugin manifest |
| --- | --- | --- |
| Claude Code | `.claude-plugin/marketplace.json` | `plugins/dot/.claude-plugin/plugin.json` |
| Codex | `.agents/plugins/marketplace.json` | `plugins/dot/plugin.json` |
| Antigravity | none (installs from a directory) | `plugins/dot/plugin.json` |

Both catalogs resolve `./plugins/dot` from the repository root. Registering or installing changes host settings; editing the repo does not.

## Claude Code

### Load from source (development)

```sh
claude --plugin-dir ~/.agents/plugins/dot
```

- Loads for that session only; nothing is installed or written to settings.
- Point it at the plugin root (the directory containing `.claude-plugin/plugin.json`), not at the marketplace root.
- After editing files, run `/reload-plugins` in the session.
- Skills are namespaced: `/dot:scope`, `/dot:plan`.

### Install via the local marketplace

```sh
claude plugin marketplace add ~/.agents
claude plugin install dot@dotagents
claude plugin list
```

Inside a session, `/plugin marketplace add ~/.agents` does the same.

- A local marketplace with a relative-path `source` is read directly from disk, not copied. Edits take effect on the next session start or `/reload-plugins`.
- Remove with `claude plugin marketplace remove dotagents`, which also uninstalls its plugins.

### Validate

```sh
claude plugin validate ~/.agents/plugins/dot
claude plugin validate ~/.agents
```

### Do not symlink into `~/.claude`

`~/.claude/plugins/` is Claude's own state (`cache/`, `installed_plugins.json`, `known_marketplaces.json`). Dropping a plugin there does not register it. Use `--plugin-dir` or the marketplace.

Sources: [Create a plugin](https://code.claude.com/docs/en/plugins/create), [Create a marketplace](https://code.claude.com/docs/en/plugin-marketplaces), [Plugins overview](https://code.claude.com/docs/en/plugins)

## Codex

```sh
codex plugin marketplace add ~/.agents
codex plugin marketplace list
```

Open `/plugins` (CLI) or Plugins (desktop app), select `dotagents`, and install `dot`. Invoke skills as `$dot:scope`, `$dot:plan`.

- There is no `--plugin-dir` equivalent.
- Codex copies the plugin to `~/.codex/plugins/cache/dotagents/dot/local/`. After editing the source, run `codex plugin marketplace upgrade` and restart Codex.
- Remove with `codex plugin marketplace remove dotagents`.

Sources: [Codex: package your plugin](https://developers.openai.com/plugins/build/plugins), [Codex CLI plugin marketplace guide](https://codex.danielvaughan.com/2026/04/24/codex-cli-plugin-marketplace-building-distributing-extending/)

## Antigravity

```sh
agy plugin install ~/.agents/plugins/dot
agy plugin list
```

Or run `/plugin` in a session and choose "Install from local directory". Manage with `agy plugin enable|disable|uninstall dot`.

- Installs globally to `~/.gemini/config/plugins/`. A workspace-level install goes in `<project>/.agents/plugins/`.
- The docs do not say whether a local install is copied or linked; reinstall if edits don't appear.

Sources: [Antigravity: plugins](https://antigravity.google/docs/plugins/), [Install a plugin in Antigravity (codelab)](https://codelabs.developers.google.com/cloud-dev-plugin-agy)
