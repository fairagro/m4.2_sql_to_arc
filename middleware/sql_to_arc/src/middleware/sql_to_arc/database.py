"""Database module for SQL-to-ARC."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from pydantic import ValidationError
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

logger = logging.getLogger(__name__)


class Database:
    """Database handler using SQLAlchemy."""

    def __init__(self, connection_string: str) -> None:
        """Initialize database with connection string."""
        # Use modern async drivers for SQLAlchemy connections
        if connection_string.startswith("postgresql://"):
            connection_string = connection_string.replace("postgresql://", "postgresql+psycopg://", 1)
        elif connection_string.startswith("mysql://") or connection_string.startswith("mariadb://"):
            connection_string = connection_string.replace("mysql://", "mysql+aiomysql://", 1).replace(
                "mariadb://", "mysql+aiomysql://", 1
            )
        elif connection_string.startswith("oracle://"):
            connection_string = connection_string.replace("oracle://", "oracle+oracledb://", 1)
        elif connection_string.startswith("mssql://"):
            connection_string = connection_string.replace("mssql://", "mssql+aioodbc://", 1)

        self.engine: AsyncEngine = create_async_engine(connection_string, echo=False)

    async def stream_investigations(self, limit: int | None = None) -> AsyncGenerator[InvestigationRow, None]:
        """Stream investigations using a server-side cursor."""
        async with self.engine.connect() as conn:
            sql = 'SELECT * FROM "vInvestigation"'
            if limit:
                sql += f" LIMIT {limit}"

            stmt = text(sql).execution_options(stream_results=True)
            result = await conn.stream(stmt)
            async for row in result.mappings():
                try:
                    yield InvestigationRow.model_validate(row)
                except ValidationError as e:
                    logger.warning("Skipping investigation due to validation error: %s", e)
                    continue

    async def stream_studies(self, investigation_ids: list[str]) -> AsyncGenerator[StudyRow, None]:
        """Stream studies for given investigations."""
        if not investigation_ids:
            return
        async with self.engine.connect() as conn:
            stmt = text('SELECT * FROM "vStudy" WHERE investigation_ref IN :ids').bindparams(
                bindparam("ids", expanding=True)
            )
            result = await conn.stream(stmt.execution_options(stream_results=True), {"ids": investigation_ids})
            async for row in result.mappings():
                yield StudyRow.model_validate(row)

    async def stream_assays(self, investigation_ids: list[str]) -> AsyncGenerator[AssayRow, None]:
        """Stream assets for given investigations."""
        if not investigation_ids:
            return
        async with self.engine.connect() as conn:
            stmt = text('SELECT * FROM "vAssay" WHERE investigation_ref IN :ids').bindparams(
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
            stmt = text('SELECT * FROM "vContact" WHERE investigation_ref IN :ids').bindparams(
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
            stmt = text('SELECT * FROM "vPublication" WHERE investigation_ref IN :ids').bindparams(
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
