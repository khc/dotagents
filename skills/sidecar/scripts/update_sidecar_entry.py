import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated


def update_sidecar_entry(
    db_path: Annotated[str, "Path to the SQLite database file"],
    uuid: Annotated[str, "UUID of the entry to update"],
    status: Annotated[str, "New status value"],
) -> bool:
    if not Path(db_path).exists():
        return False

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "UPDATE sidecar SET status = ?, updated_at = ? WHERE uuid = ?",
            (status, now, uuid),
        )

    return cursor.rowcount == 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update the status of a sidecar entry.")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--uuid", required=True)
    parser.add_argument(
        "--status",
        required=True,
        choices=["open", "pending", "done", "fixed", "wontfix", "superseded"],
    )
    args = parser.parse_args()

    updated = update_sidecar_entry(
        db_path=args.db_path,
        uuid=args.uuid,
        status=args.status,
    )
    if not updated:
        raise SystemExit(f"Error: no entry found for uuid {args.uuid}")
    print(args.uuid)
