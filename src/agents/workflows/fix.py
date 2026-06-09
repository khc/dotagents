import json
from dataclasses import dataclass
from typing import Annotated

from agents.context_loader import ContextInput, load_context
from agents.project_root import project_root
from agents.sidecar import (
    UpdateEntryArgs,
    add_sidecar_entry,
    get_sidecar_entry,
    update_sidecar_entry,
)


@dataclass
class GetReviewArgs:
    review_uuid: Annotated[str | None, "Specific review UUID to load"] = None
    start_path: Annotated[str, "Path used to resolve the project root"] = "."


@dataclass
class SaveFixArgs:
    agent: Annotated[str, "Agent runtime identifier"]
    context: Annotated[str, "Fix context JSON payload, file path, or - for stdin"]
    review_uuid: Annotated[str, "UUID of the review entry this fix addresses"]
    scope: Annotated[str | None, "Active scope path within the project"] = None
    model: Annotated[str | None, "Model name used by the agent"] = None
    start_path: Annotated[str, "Path used to resolve the project root"] = "."
    context_input: Annotated[
        ContextInput,
        "How to interpret --context: inline JSON, a file path, or stdin",
    ] = "inline"


def get_review(args: GetReviewArgs) -> str:
    root_dir = project_root(args.start_path)
    db_path = str(root_dir / ".sidecar" / "sidecar.db")

    if args.review_uuid is not None:
        entries = get_sidecar_entry(
            db_path=db_path,
            uuid=args.review_uuid,
            limit=1,
        )
        if not entries:
            raise ValueError(f"no sidecar entry found for uuid {args.review_uuid}")
    else:
        entries = get_sidecar_entry(
            db_path=db_path,
            project=root_dir.name,
            skill="review",
            status="open",
            limit=1,
        )
        if not entries:
            raise ValueError("no review entry found in sidecar")

    entry = entries[0]
    entry["context"] = json.loads(entry["context"])
    return json.dumps(entry, indent=2)


def save_fix(args: SaveFixArgs) -> str:
    root_dir = project_root(args.start_path)
    sidecar_dir = root_dir / ".sidecar"
    sidecar_dir.mkdir(parents=True, exist_ok=True)

    context_json = load_context(args.context, args.context_input)
    db_path = str(sidecar_dir / "sidecar.db")

    fix_uuid = add_sidecar_entry(
        db_path=db_path,
        project=root_dir.name,
        skill="fix",
        scope=args.scope,
        agent=args.agent,
        model=args.model or f"{args.agent}/unknown",
        context=context_json,
        status="done",
        parent_uuid=args.review_uuid,
        relation="fix",
    )

    updated = update_sidecar_entry(
        UpdateEntryArgs(
            db_path=db_path,
            uuid=args.review_uuid,
            status="done",
        )
    )
    if not updated:
        raise ValueError(f"no entry found for review uuid {args.review_uuid}")

    return fix_uuid
