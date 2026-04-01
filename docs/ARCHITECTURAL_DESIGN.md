# Architectural Documentation: SQL-to-ARC Middleware

## 1. Overview

The SQL-to-ARC Middleware is responsible for converting metadata from a relational SQL database into the **ARC (Annotated Research Context)** format. The architecture is designed for **high throughput**, **memory-efficient processing**, and **stability** when handling large volumes of data.

## 2. Core Components

The middleware consists of three main layers:

1. **Async IO Loop (Controller):** Orchestrates the data flow, manages database streams, and handles API uploads.
2. **Process Pool Executor (Worker):** Parallelizes CPU-intensive ARC calculations in separate operating system processes.
3. **Streaming Generator (Data Layer):** Reads data in chunks from the database to keep RAM consumption constant.

---

## 3. Detailed Architectural Concepts

### 3.1 Parallelization & CPU Offloading

Since generating ARCs (via `arctrl`) is computationally intensive and Python is limited by the Global Interpreter Lock (GIL), the middleware utilizes a `ProcessPoolExecutor`.

* **Advantage:** Each ARC calculation runs on its own CPU core.
* **Implementation:** `loop.run_in_executor(executor, build_single_arc_task, ...)`
* **Multiprocessing Support:** Calling `multiprocessing.freeze_support()` ensures the middleware correctly starts new processes even in "frozen" environments (such as PyInstaller binaries on Windows). On Linux, this is primarily a best practice for cross-platform compatibility.

### 3.2 Concurrency & Flow Control (The Semaphore)

In addition to the process pool, an `asyncio.Semaphore` is used. This addresses two critical issues that a pure process pool cannot solve:

1. **Memory Protection:** Without a semaphore, Python would start asynchronous tasks for all (e.g., 10,000) datasets simultaneously and keep the database data in RAM. The semaphore limits the number of *concurrently active* workflows.
2. **Network/IO Backpressure:** The semaphore also limits the number of simultaneous HTTP connections to the API to avoid timeouts and rate-limiting.

**Discussion Point:** *Why not simply limit the size of the process pool?*
The process pool only limits CPU usage. The semaphore limits the **entire lifecycle** (data preparation -> build -> upload). It prevents the memory from overflowing with "waiting" data before it is even handed over to the pool.

### 3.3 Memory-Efficient Data Streaming

The middleware implements a **lazy-loading** approach for database entities:

* **Chunking:** Using the `stream_investigations` generator (in the `Database` class), investigations are loaded in batches.
* **Relational Batching:** Associated studies, assays, contacts, and publications are fetched in bulk for each batch using specialized queries (e.g., `WHERE investigation_ref = ANY(...)`).
* **Effect:** We avoid the "N+1 Query" problem (extremely slow) while also avoiding a "Full Table Load" (extremely memory-intensive).

---

## 4. Memory Management & Performance Optimization

When processing thousands of investigations (ARC containers), RAM consumption can become critical. The middleware implements three strategies for this:

### 4.1 Backlog Flow Control (Producer Pause)

The asynchronous database stream produces data faster than the process pool can convert it.

* **Problem:** Thousands of `asyncio.Tasks` would wait in RAM simultaneously for execution, including all associated database rows.
* **Solution:** Throttling in the main loop managed by the semaphore and task set management. The stream pauses until capacity becomes available. This limits the number of datasets residing in memory at once.

### 4.2 Worker-Side Serialization & GC

ARC objects in the `arctrl` library are complex and consume both Python and .NET-bridge memory.

* **Strategy:** Conversion to a JSON-LD string is performed directly within the worker process.
* **Memory Cleanup:** After serialization, ARC objects in the worker are explicitly deleted (`del`) and the garbage collector (`gc.collect()`) is called before the process returns the result to the main process. This prevents worker processes from "swelling."

### 4.3 JSON vs. Object Transfer

In the current implementation, large ARC objects are not transferred between the main process and workers. Instead, primitive Python types (like dicts) are used as input, and serialized JSON-LD strings are returned as output. This minimizes Inter-Process Communication (IPC) overhead.

### 4.4 Decoupling I/O and CPU (Workload Balancing)

To maximize CPU utilization, the number of concurrently active tasks (`max_concurrent_tasks`) is controlled independently of the number of CPU workers (`max_concurrent_arc_builds`).

* **Principle:** While some tasks wait for the API's network response (I/O), CPU workers can already process the next ARC build from the queue.
* **Configuration:** By default, task capacity is four times larger than the number of CPU workers (configurable via `max_concurrent_tasks`) to bridge latencies without overstretching RAM.

---

## 5. Data Flow (Step-by-Step)

1. **Producer:** The main process starts the streaming generator.
2. **Throttle:** The loop waits on the `Semaphore` for an available slot.
3. **Data Fetch:** Investigation data and related entities (Studies, Assays, etc.) are fetched from the database.
4. **Build (CPU):** The dataset is sent to the `ProcessPoolExecutor`. The main loop remains free for other tasks in the meantime.
5. **Upload (I/O):** The result (JSON) is sent asynchronously via HTTP to the Middleware API using `ApiClient`.
6. **Release:** The semaphore is released, and the next dataset flows in.

---

## 6. Error Handling & Monitoring

* **Targeted Exception Handling:** Errors during upload or build do not cause the entire run to abort.
* **ProcessingStats:** Every success and failure is recorded by ID and output as a JSON-LD report at the end.
* **Tracing:** The entire chain is instrumented with **OpenTelemetry** (tracing) to identify performance bottlenecks in the process pool or network.
* **Pre-flight Schema Validation:** The middleware verifies that all required database views and columns exist before starting the process.

---

## 7. Summary of Design Decisions

| Problem | Solution | Reason |
| :--- | :--- | :--- |
| GIL / CPU Limit | `ProcessPoolExecutor` | True parallelism across multiple cores. |
| Low CPU Utilization | I/O-CPU Decoupling | `max_concurrent_tasks` allows API uploads in parallel with new ARC builds. |
| Memory Overflow (Backlog) | Producer Throttling | Prevents too many datasets from "waiting" in RAM simultaneously. |
| Memory Leak (Worker) | `gc.collect()` + JSON Return | Frees memory in the worker immediately after conversion. |
| Database Load | Server-side Cursors + `ANY()` | Optimal balance between number of queries and memory load. |
| Scalability | Single ARC Processing | Earlier success/error feedback per investigation instead of per batch only. |

---

## 8. Performance Tuning Guide

To optimally adapt the middleware to existing hardware and database structures, the following parameters in the configuration file (`config.yaml`) can be optimized:

### 8.1 CPU & Parallelization

* **`max_concurrent_arc_builds`**: Determines the number of worker processes in the `ProcessPoolExecutor`.
  * **Recommendation**: Set this value to the number of available CPU cores minus 1 (to leave reserves for the main process and the operating system).
  * **Effect**: Higher CPU load, but faster execution of ARC generation.

### 8.2 Throughput & I/O Balancing

* **`max_concurrent_tasks`**: Limits the number of concurrently active asynchronous workflows (data fetch + build + upload).
  * **Rule of Thumb**: `4 * max_concurrent_arc_builds`.
  * **Why?**: While 4 cores are calculating ARCs, other tasks can wait for the API's network response (I/O). A value that is too high leads to increased RAM consumption; a value that is too low causes the CPU to run dry ("Stop-and-Go").

### 8.3 Database Efficiency

* **`db_batch_size`**: Number of investigations loaded per database chunk.
  * **Default**: 100.
  * **Tuning**: Increase this value if you have many small investigations (few studies/assays) to reduce SQL roundtrips. Decrease it if individual investigations are extremely large to limit the RAM consumption of the main process.

### 8.4 Stability & Timeouts

* **`arc_generation_timeout_minutes`**: Maximum time for a single `build_single_arc_task` call in the worker.
  * **Tuning**: Increase this value if you see "Timeout" errors in the log for very large datasets (e.g., thousands of assays).

### 8.5 Summary: Finding the Optimal Setup

1. **Find CPU Limit:** Increase `max_concurrent_arc_builds` until CPU cores are saturated.
2. **Fill I/O Gaps:** Increase `max_concurrent_tasks` if CPU load drops to 0% between builds (an indication of waiting for API uploads).
3. **RAM Check:** Monitor memory consumption. RAM requirements increase linearly with `max_concurrent_tasks` and the size of investigations in the batch.
