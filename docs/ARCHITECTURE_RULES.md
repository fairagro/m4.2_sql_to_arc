# Architecture Rules: SQL-to-ARC Middleware

This document defines **binding rules** for the `middleware/sql_to_arc` package.
These constraints exist to preserve correctness, prevent circular imports, and enforce design patterns.
An AI assistant or developer modifying this codebase MUST follow these rules.

---

## 1. Module Dependency Graph

`sql_to_arc` is a single, self-contained component. There is no complex inter-package dependency policy to enforce within it.

The one cross-package rule is:

> `middleware.shared` and `middleware.api_client` are **read-only dependencies** of `sql_to_arc`.
> They must NEVER import from `middleware.sql_to_arc`. This is naturally enforced since both packages live in a separate repository.

If intra-package layering rules become necessary in the future (e.g., forbidden imports between specific modules), document them here.

---

## 2. Extension Points

### 2.1 Adding a New Database Entity

When adding a new entity type (e.g. `SampleRow`), ALL of the following steps are mandatory:

1. **Define the model** in `models.py` by subclassing `BaseRow`:

   ```python
   class SampleRow(BaseRow):
       __view_name__: ClassVar[str] = "vSample"
       identifier: str = spec_field(required=True)
       ...
   ```

   - Use `spec_field()` (not `Field()` directly) for all ARC-spec-relevant fields.
   - Set `__view_name__` to the exact database view name.

2. **Add a streaming method** to `Database` in `database.py`:

   ```python
   async def stream_samples(self, investigation_ids: list[str]) -> AsyncGenerator[SampleRow, None]:
       async for r in self._stream_by_investigation(SampleRow, investigation_ids, "sample"):
           yield r
   ```

3. **Register for schema validation** in `Database.validate_schema()`:

   ```python
   models = [..., SampleRow]
   ```

4. **Add a mapper function** in `mapper.py`.

5. **Link into the data bundle** `ArcBuildData` in `context.py` and populate it in `_fetch_and_group_related_data()` in `processor.py` using `group_stream()`.

6. **Call the mapper** inside `builder.py` in `build_single_arc_task()`.

### 2.2 Adding New Mapper Functions

- Mapper functions live exclusively in `mapper.py`.
- They accept a single `*Row` Pydantic model as input and return an `arctrl` type.
- They MUST NOT perform I/O, logging, or access the database.

### 2.3 Adding New Configuration Values

- All configuration values MUST be added as typed, annotated fields in the `Config` class in `config.py` or in other config classes that are referenced by `Config`.
- MUST use `Annotated[..., Field(description="...")]` with a meaningful description.
- Provide a sensible default whenever possible.
- **NEVER** access `os.environ` directly in any module. The `Config` object is the single source of truth for all settings.
- **NEVER** introduce new environment variables outside of `Config`.

---

## 3. Concurrency & IPC Rules

### 3.1 Process Pool Entry Point

- `build_single_arc_task()` in `builder.py` is the **only function** executed inside worker processes.
- It MUST be a plain, top-level function (not a method or lambda) because it is pickled for IPC.
- Its argument MUST be the frozen dataclass `ArcBuildData` (picklable, no locks, no sockets).
- Its return value MUST be a `str` (JSON-LD string) or `None`. Returning complex objects (e.g., `ARC`) is forbidden — they are not reliably picklable across process boundaries and waste IPC bandwidth.

### 3.2 Memory Management in Workers

- After serializing the ARC to JSON, `del arc` MUST be called, followed by `gc.collect()`.
- This prevents worker processes from accumulating memory across repeated calls.

### 3.3 Semaphore Usage

- The `asyncio.Semaphore` (from `config.max_concurrent_tasks`) limits the **full lifecycle** of each investigation: data bundling → CPU build → API upload.
- It is acquired inside `_build_and_upload_single_arc()`.
- NEVER acquire the semaphore in a different scope (e.g. before spawning a task).
- Do NOT use `asyncio.Semaphore` as a substitute for the process pool limit. Both controls serve different purposes: the semaphore manages memory/IO, the `ProcessPoolExecutor` manages CPU.

---

## 4. Error Handling Rules

- A failure for one investigation MUST NOT abort the entire run.
- Catch expected errors at the point closest to the failure (`_upload_and_update_stats`, `_build_and_upload_single_arc`).
- On failure: increment `stats.failed_datasets` and append the identifier to `stats.failed_ids`.
- Re-raise unexpected errors (i.e., programming errors) so they are visible immediately.
- NEVER use bare `except Exception` as the final catch — only use it in `process_investigations`'s batch loop where it is immediately re-raised after logging.

---

## 5. Configuration & Secrets

- Configuration is loaded once in `main.py` via `ConfigWrapper` from `middleware.shared`.
- The resulting `Config` object is passed explicitly to functions that need it (dependency injection).
- Secrets (e.g. `connection_string`, API keys) use `pydantic.SecretStr`. Never log them with `str()` directly; use `.get_secret_value()` only at the point of use (e.g., engine creation).

---

## 6. Logging Conventions

- Every module defines: `logger = logging.getLogger(__name__)`.
- Do NOT use `print()` for any diagnostic output.
- Log messages that occur inside concurrent tasks MUST include a traceability prefix. Use the pattern `"%s: message", inv_info` (see `inv_info` in `processor.py`) so parallel log lines are distinguishable.
- Log levels:
  - `DEBUG`: internal state, loop iterations.
  - `INFO`: successful milestones (fetch, build, upload).
  - `WARNING`: recoverable issues (missing optional column, assay without study).
  - `ERROR`: per-item failures (build failed, upload failed). Do not use for fatal errors.

---

## 7. Database Access Rules

- All database reads go through the `Database` class in `database.py`. No other module is allowed to instantiate `AsyncEngine` or execute SQL directly.
- Use `stream_results=True` on all large queries to enable server-side cursors and avoid loading full tables into RAM.
- Use `literal_column("*")` with `select()` rather than ORM field mappings to generate clean `SELECT *` SQL.
- Related data (studies, assays, etc.) is ALWAYS fetched in bulk per batch using `WHERE investigation_ref IN (...)`. Never fetch related data row-by-row in a loop.
