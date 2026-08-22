import {
  cancel,
  confirm,
  intro,
  isCancel,
  log,
  note,
  outro,
  spinner,
} from "@clack/prompts";
import { $ } from "bun";
import { config } from "dotenv";
import OpenAI from "openai";
import { GoogleGenAI } from "@google/genai";

import { OpenRedaction } from "openredaction";
import pc from "picocolors";
import { get_encoding } from "tiktoken";

config({ path: new URL("../.env", import.meta.url).pathname });

interface GitError {
  message: string;
  stderr?: {
    toString(): string;
  };
}

class CleanExitError extends Error {
  constructor(message?: string) {
    super(message);
    this.name = "CleanExitError";
  }
}

const redactor = new OpenRedaction();

const llm_provider = {
  huggingface: {
    api_key: process.env.HF_TOKEN,
    baseURL: "https://router.huggingface.co/v1",
    model: process.env.HF_MODEL || "openai/gpt-oss-20b",
  },
  inceptionlabs: {
    api_key: process.env.INCEPTIONLABS_API_KEY,
    baseURL: "https://api.inceptionlabs.ai/v1",
    model: process.env.INCEPTIONLABS_MODEL || "mercury-2",
  },
  openai: {
    api_key: process.env.OPENAI_API_KEY,
    baseURL: "https://api.openai.com/v1",
    model: process.env.OPENAI_MODEL || "gpt-5-nano",
  },
  openrouter: {
    api_key: process.env.OPENROUTER_API_KEY,
    baseURL: "https://openrouter.ai/api/v1",
    model: process.env.OPENROUTER_MODEL || "google/gemini-3-pro-preview",
  },
  googleai: {
    api_key: process.env.GOOGLEAI_API_KEY,
    baseURL: "https://generativelanguage.googleapis.com/v1beta/openai",
    model: process.env.GOOGLEAI_MODEL || "gemini-3.5-turbo",
  },
} as const;

const getProvider = (): keyof typeof llm_provider => {
  const environmentProvider = process.env.LLM_PROVIDER;
  if (environmentProvider && Object.hasOwn(llm_provider, environmentProvider)) {
    return environmentProvider as keyof typeof llm_provider;
  }
  return "openai";
};

const provider = getProvider();
const emptyTree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904";
let intentToAddPaths: string[] = [];

// Check for changes
async function checkChanges(): Promise<string[]> {
  try {
    const untrackedFiles = await $`git ls-files --others --exclude-standard -z`.quiet();
    intentToAddPaths = untrackedFiles
      .text()
      .split("\0")
      .filter(Boolean);
    await $`git add -N .`;
  } catch (error) {
    throw new Error(
      `Command 'git add -N .' failed: ${(error as GitError).message}`,
      {
        cause: error,
      },
    );
  }

  try {
    const result = await $`git status --porcelain`.quiet();
    const statusOutput = result
      .text()
      .split("\n")
      .map((status) => status.trim())
      .filter(Boolean);
    if (!statusOutput) {
      throw new CleanExitError(
        "No changes detected. Working directory is clean.",
      );
    }
    return statusOutput;
  } catch (error) {
    if (error instanceof CleanExitError) throw error;
    const error_ = error as GitError;
    throw new Error(
      `Command 'git status --porcelain' failed: ${error_.stderr?.toString().trim() || error_.message}`,
      { cause: error },
    );
  }
}

// Craft prompt
function craftPrompt(diffOutput: string): string {
  return `You are an expert software engineer.

Task:
Generate a Git commit message from the diff below.

Rules:

1. Use Conventional Commits format:
    <type>(<scope>): <subject>
2. Choose the most appropriate type:
    feat, fix, refactor, perf, docs, test, build, ci, chore, style
3. Use present tense and imperative mood.
4. Keep the subject line under 72 characters.
5. Focus on the overall purpose of the change, not implementation details.
6. Add a body only when it provides important context.
7. If a body is included:
    * Leave one blank line after the subject.
    * Use concise bullet points.
8. Output only the commit message.
9. Do not use markdown, code fences, labels, or explanations.

Diff:
${diffOutput}`;
}

// Generate commit message
async function generateCommitMessage(
  openai: OpenAI,
  model: string,
  prompt: string,
): Promise<string> {
  const s = spinner();
  s.start("Analyzing diff and generating commit message");

  try {
    const chatCompletion = await openai.chat.completions.create({
      messages: [{ content: prompt, role: "user" }],
      model: model,
    });

    const commitMessage =
      chatCompletion.choices?.[0]?.message?.content?.trim() || "";
    if (!commitMessage) {
      throw new Error("Empty commit message returned from model.");
    }
    if (chatCompletion.usage) {
      const {
        completion_tokens = 0,
        prompt_tokens = 0,
        total_tokens = prompt_tokens + completion_tokens,
      } = chatCompletion.usage;
      log.info(
        `Token Usage: ${prompt_tokens} input + ${completion_tokens} output = ${total_tokens} total tokens`,
      );
    }
    s.stop("Diff analyzed successfully");
    return commitMessage;
  } catch (error) {
    s.stop("Failed to generate commit message");
    throw new Error(
      `Error generating commit message: ${(error as Error).message}`,
      {
        cause: error,
      },
    );
  }
}

// Get the diff of all changes (staged and unstaged)
async function getDiff(): Promise<string> {
  let rawDiff: string;
  try {
    let baseRevision = "HEAD";
    try {
      await $`git rev-parse --verify HEAD`.quiet();
    } catch {
      baseRevision = emptyTree;
    }
    const result =
      await $`git diff ${baseRevision} --no-color --no-ext-diff -- . ${":(exclude)bun.lock"} ${":(exclude)package-lock.json"} ${":(exclude)Pipfile.lock"} ${":(exclude)pnpm-lock.yaml"} ${":(exclude)uv.lock"} ${":(exclude)yarn.lock"}`.quiet();
    rawDiff = result.text().trim();
  } catch (error) {
    const error_ = error as GitError;
    throw new Error(
      `Command 'git diff HEAD' failed: ${error_.stderr?.toString().trim() || error_.message}`,
      { cause: error },
    );
  }

  if (!rawDiff) {
    throw new CleanExitError("No changes found to generate a commit message.");
  }

  try {
    const detectionResult = await redactor.detect(rawDiff);
    return detectionResult.redacted;
  } catch (error) {
    throw new Error(`Redaction failed: ${(error as Error).message}`, {
      cause: error,
    });
  }
}

// Get token count
function getTokenCount(prompt: string): number {
  const encoding = get_encoding("o200k_base");
  const promptTokenCount = encoding.encode(prompt).length;
  encoding.free();
  return promptTokenCount;
}

async function main() {
  console.log();
  intro(pc.bgCyan(pc.black(" Git Commit Generator ")));

  const apiKey = validateConfig(provider);
  const statusOutput = await checkChanges();

  note(statusOutput.join("\n"), "Git Status Output");

  const diffOutput = await getDiff();
  const prompt = craftPrompt(diffOutput);

  const promptTokenCount = getTokenCount(prompt);
  log.info(`Prompt Token Estimate: ${promptTokenCount} tokens`);

  const shouldGenerate = await confirm({
    message: "Generate a commit message with the remote LLM?",
  });

  if (isCancel(shouldGenerate)) {
    throw new CleanExitError("Commit aborted.");
  }

  if (!shouldGenerate) {
    throw new CleanExitError("Commit aborted.");
  }

  const openai = new OpenAI({
    apiKey: apiKey,
    baseURL: llm_provider[provider].baseURL,
  });

  const commitMessage = await generateCommitMessage(
    openai,
    llm_provider[provider].model,
    prompt,
  );

  note(commitMessage, "Proposed Commit Message");

  const committed = await promptAndCommit(commitMessage);
  if (committed) {
    await promptAndPush();
    outro("Session complete.");
  }
}

// Prompt and commit
async function promptAndCommit(commitMessage: string): Promise<boolean> {
  const shouldCommit = await confirm({
    message: "Do you want to stage all changes and commit?",
  });

  if (isCancel(shouldCommit)) {
    throw new CleanExitError("Commit aborted.");
  }

  if (shouldCommit) {
    try {
      await $`git add -A`;
      await $`git commit -m ${commitMessage}`;
      log.success("Staged and committed successfully!");
      return true;
    } catch (error) {
      const error_ = error as GitError;
      throw new Error(
        `Staging or committing failed: ${error_.stderr?.toString().trim() || error_.message}`,
        { cause: error },
      );
    }
  }
  throw new CleanExitError("Commit aborted.");
}

// Prompt and push
async function promptAndPush(): Promise<void> {
  const shouldPush = await confirm({
    message: "Do you want to push to remote repository?",
  });

  if (isCancel(shouldPush)) {
    throw new CleanExitError("Push aborted.");
  }

  if (shouldPush) {
    const s = spinner();
    s.start("Pushing to remote repository");
    try {
      await $`git push`.quiet();
      s.stop("Pushed successfully!");
    } catch (error) {
      s.stop("Failed to push");
      const error_ = error as GitError;
      throw new Error(
        `Push failed: ${error_.stderr?.toString().trim() || error_.message}`,
        {
          cause: error,
        },
      );
    }
  }
}

// Config validation
function validateConfig(prov: keyof typeof llm_provider): string {
  const apiKey = llm_provider[prov].api_key;
  if (!apiKey) {
    throw new Error(
      `API key for provider "${prov}" is not set in environment.`,
    );
  }
  return apiKey;
}

try {
  await main();
} catch (error) {
  if (error instanceof CleanExitError) {
    if (intentToAddPaths.length > 0) {
      try {
        await $`git reset -- ${intentToAddPaths}`.quiet();
      } catch {}
    }
    if (error.message) {
      outro(error.message);
    }
  } else {
    cancel(
      `An unexpected error occurred: ${error instanceof Error ? error.message : String(error)}`,
    );
    process.exitCode = 1;
  }
}
