import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

Status = Literal["open", "pending", "done", "fixed", "wontfix", "superseded"]
Relation = Literal["followup", "fix", "review", "supersedes"]
SCHEMA_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "skills"
    / "sidecar"
    / "schemas"
    / "sidecar.schema.sql"
)


@dataclass
class AddEntryArgs:
    db_path: Annotated[str, "Path to the SQLite database file"]
    project: Annotated[str, "Project name to scope entries"]
    skill: Annotated[str, "Skill that created this entry"]
    agent: Annotated[str, "Agent runtime identifier"]
    model: Annotated[str, "Model name used by the agent"]
    context: Annotated[str | None, "Skill output serialized as JSON"] = None
    context_file: Annotated[
        str | None,
        "Path to a file containing the JSON context payload.",
    ] = None
    scope: Annotated[str | None, "Active scope path within the project"] = None
    status: Annotated[Status, "Entry status"] = "open"
    parent_uuid: Annotated[str | None, "UUID of the parent entry"] = None
    relation: Annotated[Relation | None, "Relation to parent entry"] = None


@dataclass
class UpdateEntryArgs:
    db_path: Annotated[str, "Path to the SQLite database file"]
    uuid: Annotated[str, "UUID of the entry to update"]
    status: Annotated[Status, "New status value"]


def ensure_db(db_path: str) -> None:
    target = Path(db_path)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_FILE.read_text()
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema)


def add_sidecar_entry(
    db_path: Annotated[str, "Path to the SQLite database file"],
    project: Annotated[str, "Project name to scope entries"],
    skill: Annotated[str, "Skill that created this entry"],
    agent: Annotated[str, "Agent runtime identifier"],
    model: Annotated[str, "Model name used by the agent"],
    context: Annotated[str, "Skill output serialized as JSON"],
    scope: Annotated[str | None, "Active scope path within the project"] = None,
    status: Annotated[Status, "Entry status"] = "open",
    parent_uuid: Annotated[str | None, "UUID of the parent entry"] = None,
    relation: Annotated[Relation | None, "Relation to parent entry"] = None,
) -> str:
    json.loads(context)
    ensure_db(db_path)

    entry_uuid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO sidecar (uuid, project, skill, scope, agent, model, context,
                                 status, parent_uuid, relation, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_uuid,
                project,
                skill,
                scope,
                agent,
                model,
                context,
                status,
                parent_uuid,
                relation,
                now,
                now,
            ),
        )

    return entry_uuid


def load_add_entry_context(args: AddEntryArgs) -> str:
    provided = int(args.context is not None) + int(args.context_file is not None)
    if provided != 1:
        raise ValueError("exactly one of --context or --context-file is required")
    if args.context_file is not None:
        return Path(args.context_file).read_text()
    if args.context is None:
        raise ValueError("context payload is empty")
    return args.context


def get_sidecar_entry(
    db_path: str,
    project: str | None = None,
    skill: str | None = None,
    scope: str | None = None,
    status: str | None = None,
    uuid: str | None = None,
    limit: int = 1,
) -> list[dict[str, Any]]:
    if not Path(db_path).exists():
        return []

    conditions: list[str] = []
    params: list[str | int] = []

    if uuid:
        conditions.append("uuid = ?")
        params.append(uuid)
    else:
        if project:
            conditions.append("project = ?")
            params.append(project)
        if skill:
            conditions.append("skill = ?")
            params.append(skill)
        if scope:
            conditions.append("scope = ?")
            params.append(scope)
        if status:
            conditions.append("status = ?")
            params.append(status)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT * FROM sidecar {where} ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]


def update_sidecar_entry(args: UpdateEntryArgs) -> bool:
    if not Path(args.db_path).exists():
        return False

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(args.db_path) as conn:
        cursor = conn.execute(
            "UPDATE sidecar SET status = ?, updated_at = ? WHERE uuid = ?",
            (args.status, now, args.uuid),
        )

    return cursor.rowcount == 1
