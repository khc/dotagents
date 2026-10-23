// Set one key in an editor settings.json (JSONC: comments, trailing commas).
//
// Only that key is edited via jsonc-parser, which preserves comments and
// formatting. A missing settings file is created.
import { applyEdits, modify } from "jsonc-parser";

export async function setSetting(path: string, key: string[], value: unknown, tabSize: number) {
  const file = Bun.file(path);
  const text = (await file.exists()) ? await file.text() : "{}\n";
  const edits = modify(text, key, value, {
    formattingOptions: { insertSpaces: true, tabSize },
    getInsertionIndex: () => 0, // insert first so existing properties are not reformatted
  });

  await Bun.write(path, applyEdits(text, edits));
  console.log(`Updated ${key.join(".")} in ${path}`);
}
