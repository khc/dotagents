import argparse
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

SCHEMA_FILE = Path(__file__).parent.parent / "schemas" / "sidecar.schema.sql"


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
    status: Annotated[str, "Entry status"] = "open",
    parent_uuid: Annotated[str | None, "UUID of the parent entry"] = None,
    relation: Annotated[str | None, "Relation to parent entry"] = None,
) -> str:
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add an entry to the sidecar SQLite store."
    )
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--scope", default=None)
    parser.add_argument(
        "--status",
        default="open",
        choices=["open", "pending", "done", "fixed", "wontfix", "superseded"],
    )
    parser.add_argument("--parent-uuid", default=None)
    parser.add_argument(
        "--relation", default=None, choices=["followup", "fix", "review", "supersedes"]
    )
    args = parser.parse_args()
    print(
        add_sidecar_entry(
            db_path=args.db_path,
            project=args.project,
            skill=args.skill,
            agent=args.agent,
            model=args.model,
            context=args.context,
            scope=args.scope,
            status=args.status,
            parent_uuid=args.parent_uuid,
            relation=args.relation,
        )
    )
