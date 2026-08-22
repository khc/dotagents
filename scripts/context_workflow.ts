import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export interface InstructionsLoaded {
	global: boolean;
	root: boolean;
	local: boolean;
}

export interface ContextBoundaries {
	allowed: string;
	disallowed: string;
}

export interface ContextData {
	scope_path: string;
	instructions_loaded: InstructionsLoaded;
	scope_boundaries: ContextBoundaries;
}

function expandUser(pathStr: string): string {
	if (pathStr === "~") {
		return os.homedir();
	}
	if (pathStr.startsWith("~/") || pathStr.startsWith("~\\")) {
		return path.join(os.homedir(), pathStr.slice(2));
	}
	return pathStr;
}

export function resolveScope(pathArg: string): string {
	const expanded = expandUser(pathArg);
	const scope = path.isAbsolute(expanded)
		? path.resolve(expanded)
		: path.resolve(process.cwd(), expanded);

	if (!fs.existsSync(scope)) {
		throw new Error(
			`Error: path ${pathArg} does not exist. Provide a valid path to activate scope.`,
		);
	}
	return fs.realpathSync(scope);
}

export function repoRoot(scope: string): string {
	const isDir = fs.statSync(scope).isDirectory();
	const cwd = isDir ? scope : path.dirname(scope);

	const result = spawnSync("git", ["rev-parse", "--show-toplevel"], {
		cwd,
		encoding: "utf8",
		stdio: ["pipe", "pipe", "pipe"],
	});

	if (result.status === 0 && result.stdout && result.stdout.trim().length > 0) {
		const gitRoot = result.stdout.trim();
		return fs.existsSync(gitRoot) ? fs.realpathSync(gitRoot) : path.resolve(gitRoot);
	}
	return fs.existsSync(cwd) ? fs.realpathSync(cwd) : path.resolve(cwd);
}

export function nearestAgentsMd(scope: string, root: string): string | null {
	let current = fs.statSync(scope).isDirectory() ? scope : path.dirname(scope);
	while (true) {
		const candidate = path.join(current, "AGENTS.md");
		if (fs.existsSync(candidate)) {
			return fs.realpathSync(candidate);
		}
		const parent = path.dirname(current);
		if (current === root || current === parent) {
			return null;
		}
		current = parent;
	}
}

export function loadedPaths(scope: string): InstructionsLoaded {
	const root = repoRoot(scope);
	const paths: Record<keyof InstructionsLoaded, string | null> = {
		global: path.join(os.homedir(), ".agents", "AGENTS.md"),
		root: path.join(root, "AGENTS.md"),
		local: nearestAgentsMd(scope, root),
	};

	const seen = new Set<string>();
	const loaded: InstructionsLoaded = {
		global: false,
		root: false,
		local: false,
	};

	for (const [key, filePath] of Object.entries(paths) as [
		keyof InstructionsLoaded,
		string | null,
	][]) {
		if (filePath === null) {
			loaded[key] = false;
			continue;
		}
		const resolved = fs.existsSync(filePath)
			? fs.realpathSync(filePath)
			: path.resolve(filePath);
		const exists = fs.existsSync(resolved);
		const isLoaded = exists && !seen.has(resolved);
		loaded[key] = isLoaded;
		if (isLoaded) {
			seen.add(resolved);
		}
	}

	return loaded;
}

export function contextData(pathArg: string): ContextData {
	const scope = resolveScope(pathArg);
	const loaded = loadedPaths(scope);
	const allowed = fs.statSync(scope).isDirectory() ? `${scope}/**` : scope;

	return {
		scope_path: scope,
		instructions_loaded: loaded,
		scope_boundaries: {
			allowed,
			disallowed: "everything else unless explicitly approved",
		},
	};
}

export function main(): void {
	const args = process.argv.slice(2);
	if (args.includes("-h") || args.includes("--help")) {
		console.log(
			"Usage: context_workflow.ts [-h] <path>\n\nResolve and render an active agent context.\n\nPositional arguments:\n  path        Scope path to activate.\n\nOptions:\n  -h, --help  Show this help message and exit.",
		);
		process.exit(0);
	}

	const pathArg = args[0];
	if (!pathArg) {
		console.error(
			"Usage: context_workflow.ts [-h] <path>\nError: the following arguments are required: path",
		);
		process.exit(2);
	}

	try {
		console.log(JSON.stringify(contextData(pathArg), null, 2));
	} catch (error) {
		if (error instanceof Error) {
			console.error(error.message);
		} else {
			console.error(String(error));
		}
		process.exit(1);
	}
}

if (import.meta.main) {
	main();
}

