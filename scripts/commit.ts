#!/usr/bin/env bun
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
import OpenAI from "openai";
import { OpenRedaction } from "openredaction";
import { get_encoding } from "tiktoken";

interface GitError {
	message: string;
	stderr?: {
		toString(): string;
	};
}

const redactor = new OpenRedaction();
const lockfileNames = new Set([
	"bun.lock",
	"package-lock.json",
	"yarn.lock",
	"pnpm-lock.yaml",
	"uv.lock",
	"Pipfile.lock",
]);

const isLockfileDiff = (chunk: string) => {
	const match = chunk.match(/^diff --git a\/(.+?) b\/(.+?)(?:\n|$)/);
	return lockfileNames.has(match?.[1] || "");
};

const llm_provider = {
	inceptionlabs: {
		api_key: process.env.INCEPTIONLABS_API_KEY,
		baseURL: "https://api.inceptionlabs.ai/v1",
		model: process.env.INCEPTIONLABS_MODEL || "mercury-2",
	},
	openrouter: {
		api_key: process.env.OPENROUTER_API_KEY,
		baseURL: "https://openrouter.ai/api/v1",
		model: process.env.OPENROUTER_MODEL || "google/gemini-3-pro-preview",
	},
} as const;

const provider = "openrouter";

// 1. Config validation
function validateConfig(prov: keyof typeof llm_provider): string {
	const apiKey = llm_provider[prov].api_key;
	if (!apiKey) {
		cancel(`Error: API key for provider "${prov}" is not set in environment.`);
		process.exit(1);
	}
	return apiKey;
}

// 2. Check for changes
async function checkChanges(): Promise<string> {
	try {
		await $`git add -N .`;
		const result = await $`git status --porcelain`.quiet();
		const statusOutput = result.text().trim();
		if (!statusOutput) {
			outro("No changes detected. Working directory is clean.");
			process.exit(0);
		}
		return statusOutput;
	} catch (error) {
		const err = error as GitError;
		cancel(
			`Error: Command 'git status --porcelain' failed: ${err.stderr?.toString().trim() || err.message}`,
		);
		process.exit(1);
	}
}

// 3. Get the diff of all changes (staged and unstaged)
async function getDiff(): Promise<string> {
	try {
		const result = await $`git diff HEAD --no-color --no-ext-diff`.quiet();
		const rawDiff = result.text().trim();

		// Filter out lockfiles before running redaction for performance
		const filteredDiff = rawDiff
			.split("\ndiff --git ")
			.reduce((acc, chunk, index) => {
				const diffChunk = index === 0 ? chunk : `diff --git ${chunk}`;
				if (!diffChunk.trim() || isLockfileDiff(diffChunk)) {
					return acc;
				}
				return acc ? `${acc}\n${diffChunk}` : diffChunk;
			}, "");

		if (!filteredDiff) {
			cancel("No changes found to generate a commit message.");
			process.exit(0);
		}

		const detectionResult = await redactor.detect(filteredDiff);
		return detectionResult.redacted;
	} catch (error) {
		const err = error as GitError;
		cancel(
			`Error: Command 'git diff HEAD' failed: ${err.stderr?.toString().trim() || err.message}`,
		);
		process.exit(1);
	}
}

// 4. Craft prompt
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

// 5. Get token count
function getTokenCount(prompt: string): number {
	const encoding = get_encoding("o200k_base");
	const promptTokenCount = encoding.encode(prompt).length;
	encoding.free();
	return promptTokenCount;
}

// 6. Generate commit message
async function generateCommitMessage(
	openai: OpenAI,
	model: string,
	prompt: string,
): Promise<string> {
	const s = spinner();
	s.start("Analyzing diff and generating commit message");

	try {
		const chatCompletion = await openai.chat.completions.create({
			model: model,
			messages: [{ role: "user", content: prompt }],
		});

		const commitMessage =
			chatCompletion.choices?.[0]?.message?.content?.trim() || "";
		if (!commitMessage) {
			throw new Error("Empty commit message returned from model.");
		}
		if (chatCompletion.usage) {
			const {
				prompt_tokens = 0,
				completion_tokens = 0,
				total_tokens = prompt_tokens + completion_tokens,
			} = chatCompletion.usage;
			log.info(
				`Token Usage: ${prompt_tokens} input + ${completion_tokens} output = ${total_tokens} total tokens`,
			);
		}
		s.stop("Diff analyzed successfully");
		return commitMessage;
	} catch (error) {
		const err = error as GitError;
		s.stop("Failed to generate commit message");
		cancel(`Error generating commit message: ${err.message}`);
		process.exit(1);
	}
}

// 7. Prompt and commit
async function promptAndCommit(commitMessage: string): Promise<boolean> {
	const shouldCommit = await confirm({
		message: "Do you want to stage all changes and commit?",
	});

	if (isCancel(shouldCommit)) {
		cancel("Commit aborted.");
		process.exit(0);
	}

	if (shouldCommit) {
		try {
			await $`git add -A`;
			await $`git commit -m ${commitMessage}`;
			log.success("Staged and committed successfully!");
			return true;
		} catch (error) {
			const err = error as GitError;
			cancel(
				`Error: Staging or committing failed: ${err.stderr?.toString().trim() || err.message}`,
			);
			process.exit(1);
		}
	} else {
		outro("Commit aborted.");
		return false;
	}
}

// 8. Prompt and push
async function promptAndPush(): Promise<void> {
	const shouldPush = await confirm({
		message: "Do you want to push to remote repository?",
	});

	if (isCancel(shouldPush)) {
		cancel("Push aborted.");
		process.exit(0);
	}

	if (shouldPush) {
		const s = spinner();
		s.start("Pushing to remote repository");
		try {
			await $`git push`.quiet();
			s.stop("Pushed successfully!");
		} catch (error) {
			s.stop("Failed to push");
			const err = error as GitError;
			cancel(
				`Error: Push failed: ${err.stderr?.toString().trim() || err.message}`,
			);
			process.exit(1);
		}
	}
}

async function main() {
	const apiKey = validateConfig(provider);
	const statusOutput = await checkChanges();

	intro("Git Commit Generator");
	note(statusOutput, "Git Status Output");

	const diffOutput = await getDiff();
	const prompt = craftPrompt(diffOutput);

	const promptTokenCount = getTokenCount(prompt);
	log.info(`Prompt Token Estimate: ${promptTokenCount} tokens`);

	const shouldGenerate = await confirm({
		message: "Generate a commit message with the remote LLM?",
	});

	if (isCancel(shouldGenerate)) {
		cancel("Commit aborted.");
		process.exit(0);
	}

	if (!shouldGenerate) {
		outro("Commit aborted.");
		process.exit(0);
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

main().catch((error) => {
	cancel(`An unexpected error occurred: ${error.message || error}`);
	process.exit(1);
});
