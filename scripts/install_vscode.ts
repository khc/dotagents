// Point VS Code's Copilot commit message setting at prompts/commit_message.md.
//
// Usage: bun scripts/install_vscode.ts [settings.json path]
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { setSetting } from "./lib/jsonc_settings";

const INSTRUCTIONS = resolve(import.meta.dir, "../prompts/commit_message.md");
const SETTINGS = process.argv[2] ?? join(homedir(), "Library/Application Support/Code/User/settings.json");

await setSetting(SETTINGS, ["github.copilot.chat.commitMessageGeneration.instructions"], [{ file: INSTRUCTIONS }], 4);
