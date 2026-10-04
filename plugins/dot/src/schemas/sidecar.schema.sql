CREATE TABLE IF NOT EXISTS sidecar (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid    TEXT NOT NULL UNIQUE,
    project TEXT NOT NULL,
    skill   TEXT NOT NULL,
    scope   TEXT,
    agent   TEXT NOT NULL,
    model   TEXT NOT NULL,
    context TEXT,
    parent_uuid TEXT,
    status  TEXT NOT NULL DEFAULT 'open'
            CHECK (status IN ('open', 'pending', 'done', 'fixed', 'wontfix', 'superseded')),
    relation    TEXT
                CHECK (relation IN ('followup', 'fix', 'review', 'supersedes')),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (parent_uuid) REFERENCES sidecar(uuid)
);
