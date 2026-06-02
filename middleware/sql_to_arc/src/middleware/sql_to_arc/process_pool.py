"""Process pool holder with recovery after worker crashes."""

import concurrent.futures
import logging
import multiprocessing

logger = logging.getLogger(__name__)


class ProcessPoolHolder:
    """Process pool that can be recreated after a worker crash (OOM, segfault, etc.)."""

    def __init__(
        self,
        max_workers: int,
        mp_context: multiprocessing.context.BaseContext | None = None,
        *,
        inject_executor: concurrent.futures.Executor | None = None,
    ) -> None:
        """Create a holder; use inject_executor in tests to skip real process pools."""
        self._max_workers = max_workers
        self._mp_context = mp_context or multiprocessing.get_context("spawn")
        self._inject_executor = inject_executor
        self._executor: concurrent.futures.ProcessPoolExecutor | None = None

    def get_executor(self) -> concurrent.futures.Executor:
        """Return the active executor, creating the process pool on first use."""
        if self._inject_executor is not None:
            return self._inject_executor
        if self._executor is None:
            self._executor = self._new_pool()
        return self._executor

    def recreate(self) -> None:
        """Replace a broken process pool so later investigation builds can continue."""
        if self._inject_executor is not None:
            return
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None
        self._executor = self._new_pool()
        logger.warning("Recreated process pool after worker failure; subsequent builds can continue.")

    def shutdown(self) -> None:
        """Shut down the process pool at the end of a conversion run."""
        if self._inject_executor is not None:
            return
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None

    def _new_pool(self) -> concurrent.futures.ProcessPoolExecutor:
        return concurrent.futures.ProcessPoolExecutor(
            max_workers=self._max_workers,
            mp_context=self._mp_context,
        )
