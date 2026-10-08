// Point VS Code's Copilot commit message setting at config/*.md.
//
// settings.json is JSONC (comments, trailing commas), so only this one key is
// edited via jsonc-parser, which preserves comments and formatting.
//
// Usage: bun scripts/install_copilot_commit_instructions.ts
import { applyEdits, modify } from "jsonc-parser";
import { homedir } from "node:os";
import { join, resolve } from "node:path";

const KEY = "github.copilot.chat.commitMessageGeneration.instructions";
const INSTRUCTIONS = resolve(import.meta.dir, "../config/github_copilot_chat_commitMessageGeneration_instructions.md");
const SETTINGS = join(homedir(), "Library/Application Support/Code/User/settings.json");

const settings = Bun.file(SETTINGS);
const text = (await settings.exists()) ? await settings.text() : "{}\n";
const edits = modify(text, [KEY], [{ file: INSTRUCTIONS }], {
  formattingOptions: { insertSpaces: true, tabSize: 4 },
  getInsertionIndex: () => 0, // insert first so existing properties are not reformatted
});

await Bun.write(SETTINGS, applyEdits(text, edits));
console.log(`Updated ${KEY} in ${SETTINGS}`);
