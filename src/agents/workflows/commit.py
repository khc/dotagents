import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from agents.project_root import project_root
from agents.sidecar import (
    UpdateEntryArgs,
    add_sidecar_entry,
    get_sidecar_entry,
    update_sidecar_entry,
)


@dataclass
class SaveCommitArgs:
    agent: Annotated[str, "Agent runtime identifier"]
    commit_message: Annotated[str, "The generated commit message"]
    model: Annotated[str | None, "Model name used by the agent"] = None
    scope: Annotated[str | None, "Active scope path within the project"] = None
    start_path: Annotated[str, "Path used to resolve the project root"] = "."


@dataclass
class ExecuteCommitArgs:
    uuid: Annotated[str | None, "UUID of the pending commit to execute"] = None
    start_path: Annotated[str, "Path used to resolve the project root"] = "."


def check_git_repo(cwd: Path) -> None:
    res = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise ValueError("Error: not a git repository.")


def get_git_status(cwd: Path) -> str:
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout


def get_validation_commands(root_dir: Path) -> list[str]:
    agents_md_path = root_dir / "AGENTS.md"
    if not agents_md_path.exists():
        return []
    content = agents_md_path.read_text()

    commands = []
    in_validation_gates = False
    for line in content.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("##"):
            if "validation" in line_stripped.lower() or "verification" in line_stripped.lower():
                in_validation_gates = True
            else:
                in_validation_gates = False
        elif in_validation_gates:
            if line_stripped.startswith("-"):
                match = re.search(r"`([^`]+)`", line_stripped)
                if match:
                    command = match.group(1).strip()
                    if "<" in command or ">" in command:
                        continue
                    commands.append(command)
    return commands


def save_commit(args: SaveCommitArgs) -> str:
    root_dir = project_root(args.start_path)
    check_git_repo(root_dir)

    snapshot = get_git_status(root_dir)
    if not snapshot.strip():
        raise ValueError("Nothing to commit.")

    sidecar_dir = root_dir / ".sidecar"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    db_path = str(sidecar_dir / "sidecar.db")

    context_json = json.dumps({
        "repo_state_snapshot": snapshot,
        "commit_message": args.commit_message,
    })

    entry_uuid = add_sidecar_entry(
        db_path=db_path,
        project=root_dir.name,
        skill="commit",
        scope=args.scope,
        agent=args.agent,
        model=args.model or f"{args.agent}/unknown",
        context=context_json,
        status="pending",
    )
    return entry_uuid


def execute_commit(args: ExecuteCommitArgs) -> str:
    root_dir = project_root(args.start_path)
    check_git_repo(root_dir)

    db_path = str(root_dir / ".sidecar" / "sidecar.db")

    if args.uuid is not None:
        entries = get_sidecar_entry(
            db_path=db_path,
            uuid=args.uuid,
            limit=1,
        )
    else:
        entries = get_sidecar_entry(
            db_path=db_path,
            project=root_dir.name,
            skill="commit",
            status="pending",
            limit=1,
        )

    if not entries:
        raise ValueError("No pending commit found in sidecar.")

    entry = entries[0]
    entry_uuid = entry["uuid"]
    context_data = entry.get("context")
    if not isinstance(context_data, str):
        raise TypeError("Expected context to be a string")

    context = json.loads(context_data)
    repo_state_snapshot = context["repo_state_snapshot"]
    commit_message = context["commit_message"]

    repo_state_now = get_git_status(root_dir)
    if repo_state_now != repo_state_snapshot:
        update_sidecar_entry(
            UpdateEntryArgs(
                db_path=db_path,
                uuid=entry_uuid,
                status="superseded",
            )
        )
        raise ValueError("Repository state has changed since snapshot was taken. Aborting.")

    # Stage changes
    if repo_state_now.strip():
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(root_dir),
            capture_output=True,
            text=True,
            check=True,
        )

    # Run validation gates
    validation_commands = get_validation_commands(root_dir)
    for cmd in validation_commands:
        res = subprocess.run(
            cmd,
            shell=True,
            cwd=str(root_dir),
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            # Report the error in one line and do not commit (remain status: pending)
            error_msg = (res.stderr or res.stdout or "").replace("\n", " ").strip()[:200]
            raise ValueError(f"Validation failed for command '{cmd}': {error_msg}")

    # Run git commit
    res = subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        error_msg = (res.stderr or res.stdout or "").replace("\n", " ").strip()[:200]
        raise ValueError(f"Git commit failed: {error_msg}")

    # Mark sidecar entry as done
    update_sidecar_entry(
        UpdateEntryArgs(
            db_path=db_path,
            uuid=entry_uuid,
            status="done",
        )
    )

    return f"Successfully committed with UUID {entry_uuid}. Output:\n{res.stdout}"
