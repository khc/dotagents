import json
from dataclasses import dataclass
from typing import Annotated

from agents.context_loader import ContextInput, load_context
from agents.project_root import project_root
from agents.sidecar import (
    AddEntryArgs,
    Relation,
    Status,
    UpdateEntryArgs,
    add_sidecar_entry,
    get_sidecar_entry,
    update_sidecar_entry,
)


@dataclass
class SaveArgs:
    agent: Annotated[str, "Agent runtime identifier"]
    skill: Annotated[str, "Skill that created this entry"]
    context: Annotated[str, "Context JSON payload, file path, or - for stdin"]
    model: Annotated[str | None, "Model name used by the agent"] = None
    scope: Annotated[str | None, "Active scope path within the project"] = None
    status: Annotated[Status, "Entry status"] = "open"
    parent_uuid: Annotated[str | None, "UUID of the parent entry"] = None
    relation: Annotated[Relation | None, "Relation to parent entry"] = None
    start_path: Annotated[str, "Path used to resolve the project root"] = "."
    context_input: Annotated[
        ContextInput,
        "How to interpret --context: inline JSON, a file path, or stdin",
    ] = "inline"


@dataclass
class ReadArgs:
    project: Annotated[str | None, "Project name filter"] = None
    skill: Annotated[str | None, "Skill name filter"] = None
    scope: Annotated[str | None, "Scope path filter"] = None
    status: Annotated[Status | None, "Status filter"] = None
    uuid: Annotated[str | None, "Exact UUID filter"] = None
    limit: Annotated[int, "Maximum number of entries to return"] = 1
    start_path: Annotated[str, "Path used to resolve the project root"] = "."


@dataclass
class UpdateArgs:
    uuid: Annotated[str, "UUID of the entry to update"]
    status: Annotated[Status, "New status value"]
    start_path: Annotated[str, "Path used to resolve the project root"] = "."


def save(args: SaveArgs) -> str:
    root_dir = project_root(args.start_path)
    sidecar_dir = root_dir / ".sidecar"
    sidecar_dir.mkdir(parents=True, exist_ok=True)

    context_json = load_context(args.context, args.context_input)

    return add_sidecar_entry(
        db_path=str(sidecar_dir / "sidecar.db"),
        project=root_dir.name,
        skill=args.skill,
        scope=args.scope,
        agent=args.agent,
        model=args.model or f"{args.agent}/unknown",
        context=context_json,
        status=args.status,
        parent_uuid=args.parent_uuid,
        relation=args.relation,
    )


def read(args: ReadArgs) -> str:
    root_dir = project_root(args.start_path)
    entries = get_sidecar_entry(
        db_path=str(root_dir / ".sidecar" / "sidecar.db"),
        project=args.project if args.uuid is not None else (args.project or root_dir.name),
        skill=args.skill,
        scope=args.scope,
        status=args.status,
        uuid=args.uuid,
        limit=args.limit,
    )
    return json.dumps(entries, indent=2)


def update(args: UpdateArgs) -> str:
    root_dir = project_root(args.start_path)
    updated = update_sidecar_entry(
        UpdateEntryArgs(
            db_path=str(root_dir / ".sidecar" / "sidecar.db"),
            uuid=args.uuid,
            status=args.status,
        )
    )
    if not updated:
        raise ValueError(f"no entry found for uuid {args.uuid}")
    return args.uuid
