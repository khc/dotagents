import js from "@eslint/js";
import json from "@eslint/json";
import markdown from "@eslint/markdown";
import { defineConfig, globalIgnores } from "eslint/config";
import sonarjs from "eslint-plugin-sonarjs";
import unicorn from "eslint-plugin-unicorn";
import globals from "globals";
import tseslint from "typescript-eslint";

const codeFiles = ["**/*.{js,mjs,cjs,ts,mts,cts}"];
const tsFiles = ["**/*.{ts,mts,cts}"];

export default defineConfig([
  globalIgnores(["dist/**", "build/**", "coverage/**", "node_modules/**"]),

  {
    files: codeFiles,
    languageOptions: {
      globals: globals.node,
    },
  },

  {
    files: codeFiles,
    extends: [
      js.configs.recommended,
      sonarjs.configs.recommended,
      unicorn.configs.recommended,
    ],
    rules: {
      "unicorn/prevent-abbreviations": "off",
      "unicorn/filename-case": "off",

      "sonarjs/cognitive-complexity": ["warn", 15],
    },
  },

  {
    files: tsFiles,
    extends: [tseslint.configs.recommended],
  },

  {
    files: ["**/*.json"],
    plugins: { json },
    language: "json/json",
    extends: ["json/recommended"],
  },

  {
    files: ["**/*.jsonc"],
    plugins: { json },
    language: "json/jsonc",
    extends: ["json/recommended"],
  },

  {
    files: ["**/*.md"],
    plugins: { markdown },
    language: "markdown/commonmark",
    extends: ["markdown/recommended"],
  },
]);
