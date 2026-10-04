from dataclasses import dataclass
from typing import Annotated

from agents.context_loader import ContextInput, load_context
from agents.project_root import project_root
from agents.sidecar import add_sidecar_entry


@dataclass
class Args:
    agent: Annotated[str, "Agent runtime identifier"]
    context: Annotated[str, "Review context JSON payload, file path, or - for stdin"]
    scope: Annotated[str | None, "Active scope path within the project"] = None
    model: Annotated[str | None, "Model name used by the agent"] = None
    start_path: Annotated[str, "Path used to resolve the project root"] = "."
    context_input: Annotated[
        ContextInput,
        "How to interpret --context: inline JSON, a file path, or stdin",
    ] = "inline"


def review_workflow(args: Args) -> str:
    root_dir = project_root(args.start_path)
    sidecar_dir = root_dir / ".sidecar"
    sidecar_dir.mkdir(parents=True, exist_ok=True)

    context_json = load_context(args.context, args.context_input)

    return add_sidecar_entry(
        db_path=str(sidecar_dir / "sidecar.db"),
        project=root_dir.name,
        skill="review",
        scope=args.scope,
        agent=args.agent,
        model=args.model or f"{args.agent}/unknown",
        context=context_json,
    )
