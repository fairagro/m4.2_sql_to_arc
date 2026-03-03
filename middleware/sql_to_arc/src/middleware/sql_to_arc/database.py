"""Database module for SQL-to-ARC."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from pydantic import ValidationError
from sqlalchemy import (
    bindparam,
    text,
)
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from middleware.sql_to_arc.models import (
    AssayRow,
    BaseRow,
    ContactRow,
    InvestigationRow,
    MissingRequiredColumnsError,
    PublicationRow,
    RequiredColumnsNullError,
    StudyRow,
)
from middleware.sql_to_arc.stats import ProcessingStats

logger = logging.getLogger(__name__)
RowModel = TypeVar("RowModel", bound=BaseRow)


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

    @staticmethod
    def _validate_and_map(
        row: Any,
        model: type[RowModel],
        entity_name: str,
    ) -> RowModel | None:
        try:
            return model.model_validate(row)
        except MissingRequiredColumnsError as error:
            logger.error(
                'CRITICAL: Table "%s" is missing required columns: %s. Re-raising for caller to handle.',
                error.model_name,
                ", ".join(error.columns),
            )
            # Re-raise instead of exiting to allow for higher-level cleanup
            raise
        except RequiredColumnsNullError as error:
            logger.warning(
                'Skipping %s: required columns contain NULL values in table "%s": %s.',
                entity_name,
                error.model_name,
                ", ".join(error.columns),
            )
            return None
        except ValidationError as error:
            logger.warning("Skipping %s due to validation error: %s", entity_name, error)
            return None

    async def stream_investigations(
        self,
        stats: ProcessingStats,
        limit: int | None = None,
    ) -> AsyncGenerator[InvestigationRow, None]:
        """Stream investigations using a server-side cursor."""
        try:
            async with self.engine.connect() as conn:
                sql = 'SELECT * FROM "vInvestigation"'
                if limit:
                    sql += f" LIMIT {limit}"

                stmt = text(sql).execution_options(stream_results=True)
                result = await conn.stream(stmt)
                async for row in result.mappings():
                    # Count everything we find in the database
                    stats.found_datasets += 1

                    investigation = self._validate_and_map(row, InvestigationRow, "investigation")
                    if investigation is None:
                        # If validation fails, it's a found but failed dataset
                        stats.failed_datasets += 1
                        stats.failed_ids.append(row.get("identifier", "unknown"))
                        continue

                    yield investigation
        except ProgrammingError as e:
            if 'relation "vinvestigation" does not exist' in str(e).lower():
                logger.warning('Table or view "vInvestigation" does not exist. Treating as empty.')
            else:
                raise

    async def stream_studies(self, investigation_ids: list[str]) -> AsyncGenerator[StudyRow, None]:
        """Stream studies for given investigations."""
        if not investigation_ids:
            return
        try:
            async with self.engine.connect() as conn:
                stmt = text('SELECT * FROM "vStudy" WHERE investigation_ref IN :ids').bindparams(
                    bindparam("ids", expanding=True)
                )
                result = await conn.stream(stmt.execution_options(stream_results=True), {"ids": investigation_ids})
                async for row in result.mappings():
                    study = self._validate_and_map(row, StudyRow, "study")
                    if study is not None:
                        yield study
        except ProgrammingError as e:
            if 'relation "vstudy" does not exist' in str(e).lower():
                logger.warning('Table or view "vStudy" does not exist. Treating as empty.')
            else:
                raise

    async def stream_assays(self, investigation_ids: list[str]) -> AsyncGenerator[AssayRow, None]:
        """Stream assets for given investigations."""
        if not investigation_ids:
            return
        try:
            async with self.engine.connect() as conn:
                stmt = text('SELECT * FROM "vAssay" WHERE investigation_ref IN :ids').bindparams(
                    bindparam("ids", expanding=True)
                )
                result = await conn.stream(stmt.execution_options(stream_results=True), {"ids": investigation_ids})
                async for row in result.mappings():
                    assay = self._validate_and_map(row, AssayRow, "assay")
                    if assay is not None:
                        yield assay
        except ProgrammingError as e:
            if 'relation "vassay" does not exist' in str(e).lower():
                logger.warning('Table or view "vAssay" does not exist. Treating as empty.')
            else:
                raise

    async def stream_contacts(self, investigation_ids: list[str]) -> AsyncGenerator[ContactRow, None]:
        """Stream contacts for given investigations."""
        if not investigation_ids:
            return
        try:
            async with self.engine.connect() as conn:
                stmt = text('SELECT * FROM "vContact" WHERE investigation_ref IN :ids').bindparams(
                    bindparam("ids", expanding=True)
                )
                result = await conn.stream(stmt.execution_options(stream_results=True), {"ids": investigation_ids})
                async for row in result.mappings():
                    contact = self._validate_and_map(row, ContactRow, "contact")
                    if contact is not None:
                        yield contact
        except ProgrammingError as e:
            if 'relation "vcontact" does not exist' in str(e).lower():
                logger.warning('Table or view "vContact" does not exist. Treating as empty.')
            else:
                raise

    async def stream_publications(self, investigation_ids: list[str]) -> AsyncGenerator[PublicationRow, None]:
        """Stream publications for given investigations."""
        if not investigation_ids:
            return
        try:
            async with self.engine.connect() as conn:
                stmt = text('SELECT * FROM "vPublication" WHERE investigation_ref IN :ids').bindparams(
                    bindparam("ids", expanding=True)
                )
                result = await conn.stream(stmt.execution_options(stream_results=True), {"ids": investigation_ids})
                async for row in result.mappings():
                    publication = self._validate_and_map(row, PublicationRow, "publication")
                    if publication is not None:
                        yield publication
        except ProgrammingError as e:
            if 'relation "vpublication" does not exist' in str(e).lower():
                logger.warning('Table or view "vPublication" does not exist. Treating as empty.')
            else:
                raise

    async def stream_annotation_tables(self, investigation_ids: list[str]) -> AsyncGenerator[dict[str, Any], None]:
        """Stream annotation tables for given investigations."""
        if not investigation_ids:
            return
        try:
            async with self.engine.connect() as conn:
                stmt = text("SELECT * FROM vAnnotationTable WHERE investigation_ref IN :ids").bindparams(
                    bindparam("ids", expanding=True)
                )
                result = await conn.stream(stmt.execution_options(stream_results=True), {"ids": investigation_ids})
                async for row in result.mappings():
                    yield dict(row)
        except ProgrammingError as e:
            if 'relation "vannotationtable" does not exist' in str(e).lower():
                logger.warning('Table or view "vAnnotationTable" does not exist. Treating as empty.')
            else:
                raise

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[AsyncConnection, None]:
        """Context manager for database connection."""
        async with self.engine.connect() as conn:
            yield conn
