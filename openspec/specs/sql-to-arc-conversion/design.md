# SQL-to-ARC Conversion — Design

## Architecture

Three concurrency layers cooperate to keep the pipeline fast and
memory-bounded:

```text
Main process (async event loop)
  │
  ├─ DB stream  (AsyncGenerator, server-side cursor, chunked)
  │
  ├─ asyncio.Semaphore  (flow control: caps active tasks)
  │
  ├─ asyncio.Task set  (one Task per investigation)
  │    │
  │    └─ ProcessPoolExecutor  (CPU-bound ARC build in forked process)
  │
  └─ httpx (async HTTP upload to Middleware API)
```

## Data Flow

1. `main.py` parses config and starts `process_investigations()`.
2. DB stream yields `InvestigationRow` objects one batch at a time
   (`db_batch_size`, default 100).
3. For each batch, related data (studies, assays, contacts, publications,
   annotations) is fetched in a single bulk query per entity type using
   `WHERE investigation_ref = ANY(...)`.
4. The semaphore gates entry into the per-investigation task. It limits
   peak concurrent active lifecycles to `max_concurrent_tasks` (default
   4 × `max_concurrent_arc_builds`).
5. Inside the task, an `ArcBuildData` bundle (plain Pydantic models) is
   handed to `loop.run_in_executor()` which runs `build_single_arc_task`
   in a worker process.
6. The worker builds the ARC, serializes it to a JSON-LD string, calls
   `gc.collect()`, and returns the string.
7. Successfully built payloads are validated and enqueued; an async
   generator feeds them into `ApiClient.harvest_arcs` (one harvest per RDI
   run). Build failures never enter the stream.
8. After `harvest_arcs` returns, the repository scope is updated from
   harvest outcomes (`HarvestReport` / `RepositoryScope`).

## Module Split

- `processor.py` keeps investigation-level build semantics and harvest outcome
  application.
- `pipeline.py` owns technical plumbing: queue management, backpressure,
  task lifecycle, DB-batch fan-out, and queue draining on abort.

## Key Decisions

1. **ProcessPoolExecutor, not ThreadPoolExecutor**
   — `arctrl` is CPU-bound and holds .NET bridge state; the GIL prevents
   true parallelism with threads. Separate OS processes give each worker
   a dedicated core.

2. **Semaphore scope wraps the build lifecycle (data → build → enqueue)**
   — A narrower scope (e.g. only around the CPU step) would let the event
   loop queue thousands of "waiting" tasks, each holding its DB rows in RAM.
   The semaphore prevents the backlog from growing unboundedly. Upload runs
   as one `harvest_arcs` call consuming the build queue in parallel.

3. **IPC via JSON string, not pickled ARC object**
   — ARC objects carry .NET interop state that does not survive pickling
   cleanly and is large. Returning a string minimises IPC overhead and
   avoids worker memory leaks.

4. **Batch fetch of related data, not per-investigation queries**
   — Querying DB once per investigation would be O(N) round-trips.
   One bulk `ANY()` query per entity type per batch keeps DB load constant.

5. **`max_concurrent_tasks` defaults to 4 × `max_concurrent_arc_builds`**
   — While `k` workers build ARCs, extra task slots keep the queue fed so
   `harvest_arcs` can submit without stalling behind a single build wave.

6. **Schema validation before the loop starts**
   — Fail fast with a clear diagnostic if the DB schema doesn't match
   the expected views. Better than partial output with silent column gaps.

7. **OpenTelemetry tracing across the full pipeline**
   — `processor.py` and `main.py` instrument each investigation span and
   the overall run span. This allows identifying bottlenecks in the process
   pool (CPU-bound) versus the API upload (I/O-bound) in production.

8. **Process pool recreation after worker crash**
   — If a worker dies (OOM, native crash), `ProcessPoolExecutor` becomes
   broken and all pending builds would fail. `ProcessPoolHolder.recreate()`
   replaces the pool so later investigations can still be processed; the
   investigation that triggered the crash is marked failed.
