// Copy prompts/commit_message.md into Zed's commit message instructions.
//
// Usage: bun scripts/install_zed.ts [settings.json path]
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { setSetting } from "./lib/jsonc_settings";

const INSTRUCTIONS = resolve(import.meta.dir, "../prompts/commit_message.md");
const SETTINGS = process.argv[2] ?? join(homedir(), ".config/zed/settings.json");

const instructions = (await Bun.file(INSTRUCTIONS).text()).trim();
await setSetting(SETTINGS, ["agent", "commit_message_instructions"], instructions, 2);
