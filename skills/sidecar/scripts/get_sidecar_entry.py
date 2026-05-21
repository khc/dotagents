import argparse
import json
import sqlite3
from pathlib import Path


def get_sidecar_entry(
    db_path: str,
    project: str | None = None,
    skill: str | None = None,
    scope: str | None = None,
    status: str | None = None,
    uuid: str | None = None,
    limit: int = 1,
) -> list[dict]:
    if not Path(db_path).exists():
        return []

    conditions = []
    params: list = []

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query entries from the sidecar SQLite store.")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--project")
    parser.add_argument("--skill")
    parser.add_argument("--scope")
    parser.add_argument("--status")
    parser.add_argument("--uuid")
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()

    results = get_sidecar_entry(
        db_path=args.db_path,
        project=args.project,
        skill=args.skill,
        scope=args.scope,
        status=args.status,
        uuid=args.uuid,
        limit=args.limit,
    )
    print(json.dumps(results, indent=2))
