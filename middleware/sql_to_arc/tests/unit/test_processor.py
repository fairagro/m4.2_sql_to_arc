"""Unit tests for processor pool recovery."""

import multiprocessing

from middleware.sql_to_arc.process_pool import ProcessPoolHolder


def test_process_pool_holder_recreate_replaces_executor() -> None:
    """After recreate(), get_executor() must return a new pool instance."""
    holder = ProcessPoolHolder(max_workers=1, mp_context=multiprocessing.get_context("spawn"))
    try:
        first = holder.get_executor()
        holder.recreate(first)
        second = holder.get_executor()
        assert first is not second
    finally:
        holder.shutdown()
