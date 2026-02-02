"""Database module for SQL-to-ARC."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import (
    bindparam,
    text,
)
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from middleware.sql_to_arc.models import (
    AssayRow,
    ContactRow,
    InvestigationRow,
    PublicationRow,
    StudyRow,
)


class Database:
    """Database handler using SQLAlchemy."""

    def __init__(self, connection_string: str) -> None:
        """Initialize database with connection string."""
        self.engine: AsyncEngine = create_async_engine(connection_string, echo=False)

    async def stream_investigations(self, limit: int | None = None) -> AsyncGenerator[InvestigationRow, None]:
        """Stream investigations using a server-side cursor."""
        async with self.engine.connect() as conn:
            sql = "SELECT * FROM vInvestigation"
            if limit:
                sql += f" LIMIT {limit}"

            stmt = text(sql).execution_options(stream_results=True)
            result = await conn.stream(stmt)
            async for row in result.mappings():
                yield InvestigationRow.model_validate(row)

    async def stream_studies(self, investigation_ids: list[str]) -> AsyncGenerator[StudyRow, None]:
        """Stream studies for given investigations."""
        if not investigation_ids:
            return
        async with self.engine.connect() as conn:
            stmt = text("SELECT * FROM vStudy WHERE investigation_ref IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            result = await conn.stream(stmt.execution_options(stream_results=True), {"ids": investigation_ids})
            async for row in result.mappings():
                yield StudyRow.model_validate(row)

    async def stream_assays(self, investigation_ids: list[str]) -> AsyncGenerator[AssayRow, None]:
        """Stream assays for given investigations."""
        if not investigation_ids:
            return
        async with self.engine.connect() as conn:
            stmt = text("SELECT * FROM vAssay WHERE investigation_ref IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            result = await conn.stream(stmt.execution_options(stream_results=True), {"ids": investigation_ids})
            async for row in result.mappings():
                yield AssayRow.model_validate(row)

    async def stream_contacts(self, investigation_ids: list[str]) -> AsyncGenerator[ContactRow, None]:
        """Stream contacts for given investigations."""
        if not investigation_ids:
            return
        async with self.engine.connect() as conn:
            stmt = text("SELECT * FROM vContact WHERE investigation_ref IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            result = await conn.stream(stmt.execution_options(stream_results=True), {"ids": investigation_ids})
            async for row in result.mappings():
                yield ContactRow.model_validate(row)

    async def stream_publications(self, investigation_ids: list[str]) -> AsyncGenerator[PublicationRow, None]:
        """Stream publications for given investigations."""
        if not investigation_ids:
            return
        async with self.engine.connect() as conn:
            stmt = text("SELECT * FROM vPublication WHERE investigation_ref IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            result = await conn.stream(stmt.execution_options(stream_results=True), {"ids": investigation_ids})
            async for row in result.mappings():
                yield PublicationRow.model_validate(row)

    async def stream_annotation_tables(self, investigation_ids: list[str]) -> AsyncGenerator[dict[str, Any], None]:
        """Stream annotation tables for given investigations."""
        if not investigation_ids:
            return
        async with self.engine.connect() as conn:
            stmt = text("SELECT * FROM vAnnotationTable WHERE investigation_ref IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            result = await conn.stream(stmt.execution_options(stream_results=True), {"ids": investigation_ids})
            async for row in result.mappings():
                yield dict(row)

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[AsyncConnection, None]:
        """Context manager for database connection."""
        async with self.engine.connect() as conn:
            yield conn
