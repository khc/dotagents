
# Dependency manager

## Purpose

Remove unused transitive dependencies from a package and add missing direct ones. Invoke when `uv sync` fails due to unresolved or unused dependency errors.

## Reqs

Requires a scoped package path set via `$context <path>` (e.g., `$context packages/crawl`). Context = the package directory where `pyproject.toml` is located.

If no scope is active, ask the user to run: `$context {packages/crawl,packages/flows,packages/notebooklm}` for the target package.


## Workflow

1. Run analysis:
   ```bash
   uv run deptry {context} --config {context}/pyproject.toml
   ```
   Where `{context}` = the package path (e.g., `packages/crawl`)

2. Review output and apply changes:
   - **DEP002** (defined but not used): run `uv remove {dependency} --package {package_name}` for each
   - **DEP003** (imported but transitive): run `uv add {dependency} --package {package_name}` for each

3. Error handling:
   - If deptry fails: check `{context}/pyproject.toml` for syntax errors
   - If uv add/remove fails: verify package exists and dependency name is valid
