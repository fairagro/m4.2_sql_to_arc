"""Database module for SQL-to-ARC."""

import logging
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from typing import Any, TypeVar, cast

import sqlalchemy
from pydantic import ValidationError
from sqlalchemy import (
    column,
    func,
    inspect,
    select,
    table,
)
from sqlalchemy.exc import NoSuchTableError, ProgrammingError
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


class SchemaValidator:
    """Validator for database schema and structural integrity."""

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize with database engine."""
        self.engine = engine

    async def validate_models(self, models: Iterable[type[BaseRow]]) -> None:
        """Validate all provided models against the database schema."""
        async with self.engine.connect() as conn:
            for model in models:
                await self._validate_model(conn, model)

    async def _validate_model(self, conn: AsyncConnection, model: type[BaseRow]) -> None:
        """Validate a single model against its corresponding database view."""
        view_name = getattr(model, "__view_name__", None)
        if not view_name:
            logger.debug("Skipping validation for model %s (no __view_name__)", model.__name__)
            return

        db_columns = await self._get_db_columns(conn, view_name)
        if db_columns is None:
            return

        self._check_column_presence(model, db_columns)
        await self._check_null_values(conn, model, db_columns)

    @staticmethod
    async def _get_db_columns(conn: AsyncConnection, view_name: str) -> set[str] | None:
        """Retrieve column names for a given table or view."""
        try:
            columns = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_columns(view_name))
            return {col["name"] for col in columns}
        except (ProgrammingError, NoSuchTableError):
            logger.warning('Table or view "%s" does not exist or is not accessible.', view_name)
            return None

    @staticmethod
    def _check_column_presence(model: type[BaseRow], db_columns: set[str]) -> None:
        """Check for missing required/optional columns and extra columns."""
        model_fields = model.model_fields
        present_fields = set(model_fields.keys())
        missing_required: list[str] = []
        missing_optional: list[str] = []

        for field_name, field_info in model_fields.items():
            if field_name in db_columns:
                continue

            json_extra = field_info.json_schema_extra
            spec_required = json_extra.get("spec_required") if isinstance(json_extra, dict) else None
            is_required = field_info.is_required() if spec_required is None else spec_required

            if is_required and field_info.is_required():
                missing_required.append(field_name)
            else:
                missing_optional.append(field_name)

        if missing_required:
            raise MissingRequiredColumnsError(model.__name__, sorted(missing_required))

        if missing_optional:
            logger.warning(
                'Table "%s" is missing optional columns: %s. Using default values.',
                model.__name__,
                ", ".join(sorted(missing_optional)),
            )

        extra_columns = db_columns - present_fields
        if extra_columns:
            logger.info(
                'Table "%s" contains extra columns not used by model: %s.',
                model.__name__,
                ", ".join(sorted(extra_columns)),
            )

    @staticmethod
    async def _check_null_values(conn: AsyncConnection, model: type[BaseRow], db_columns: set[str]) -> None:
        """Check for NULL values in required fields."""
        view_name = model.__view_name__
        for field_name, field_info in model.model_fields.items():
            if field_name not in db_columns:
                continue

            json_extra = field_info.json_schema_extra
            spec_required = json_extra.get("spec_required") if isinstance(json_extra, dict) else None
            if spec_required is False:
                continue

            # If not explicitly marked as NOT spec_required, and has no default, it's mandatory
            if spec_required or field_info.is_required():
                allow_override = json_extra.get("spec_override", False) if isinstance(json_extra, dict) else False

                # Use SQLAlchemy select() to count NULLs
                t = table(view_name, column(field_name))
                stmt = select(func.count()).select_from(t).where(column(field_name).is_(None))  # pylint: disable=not-callable
                result = await conn.execute(stmt)
                null_count = result.scalar() or 0

                if null_count > 0:
                    if allow_override:
                        logger.warning(
                            'Table "%s": Column "%s" contains %d NULL values. '
                            "These will be replaced by model defaults due to allow_spec_override=True.",
                            model.__name__,
                            field_name,
                            null_count,
                        )
                    else:
                        raise RequiredColumnsNullError(model.__name__, [field_name])


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
        self.validator = SchemaValidator(self.engine)

    async def validate_schema(self) -> None:
        """Validate schema for all known models."""
        models = [
            InvestigationRow,
            StudyRow,
            AssayRow,
            ContactRow,
            PublicationRow,
        ]
        # Cast to satisfying the Iterable[type[BaseRow]] requirement
        await self.validator.validate_models(cast(Iterable[type[BaseRow]], models))

    @staticmethod
    def _validate_and_map(
        row: Any,
        model: type[RowModel],
        entity_name: str,
    ) -> RowModel | None:
        try:
            validated: RowModel = model.model_validate(dict(row))
            return validated
        except ValidationError as error:
            logger.warning("Skipping %s due to validation error: %s", entity_name, error)
            return None

    async def stream_investigations(
        self,
        stats: ProcessingStats,
        limit: int | None = None,
    ) -> AsyncGenerator[InvestigationRow, None]:
        """Stream investigations using a server-side cursor."""
        view_name = InvestigationRow.__view_name__
        try:
            async with self.engine.connect() as conn:
                # Use literal_column("*") to ensure SQLAlchemy generates 'SELECT *'
                # instead of '"vInvestigation"."*"' which can cause issues with some dialects
                stmt: sqlalchemy.Select[Any] = (
                    select(sqlalchemy.literal_column("*"))
                    .select_from(table(view_name))
                    .execution_options(stream_results=True)
                )
                if limit:
                    stmt = stmt.limit(limit)

                # Execute stream to use server-side cursor (prevents loading all rows into RAM)
                result = await conn.stream(stmt)
                async for row in result.mappings():
                    # Count everything we find in the database
                    stats.found_datasets += 1

                    # Map raw DB row to Pydantic model with validation
                    investigation = self._validate_and_map(row, InvestigationRow, "investigation")
                    if investigation is None:
                        # If validation fails, it's a found but failed dataset
                        stats.failed_datasets += 1
                        stats.failed_ids.append(row.get("identifier", "unknown"))
                        continue

                    # Yield validated model to the async loop in processor.py
                    yield investigation
        except ProgrammingError as e:
            # Handle missing view gracefully (e.g. during initial setup or empty DBs)
            if f'relation "{view_name.lower()}" does not exist' in str(e).lower():
                logger.warning('Table or view "%s" does not exist. Treating as empty.', view_name)
            else:
                raise

    async def _stream_by_investigation(
        self,
        model: type[RowModel],
        investigation_ids: list[str],
        entity_name: str,
    ) -> AsyncGenerator[RowModel, None]:
        """Stream related data for a given set of investigation IDs."""
        if not investigation_ids:
            return
        view_name = model.__view_name__
        try:
            async with self.engine.connect() as conn:
                # Use literal_column("*") to select all columns
                c_inv_ref: sqlalchemy.ColumnElement[Any] = column("investigation_ref")
                stmt: sqlalchemy.Select[Any] = (
                    select(sqlalchemy.literal_column("*"))
                    .select_from(table(view_name))
                    .where(c_inv_ref.in_(investigation_ids))
                    .execution_options(stream_results=True)
                )

                result = await conn.stream(stmt)
                async for row in result.mappings():
                    item = self._validate_and_map(row, model, entity_name)
                    if item is not None:
                        yield item
        except ProgrammingError as e:
            if f'relation "{view_name.lower()}" does not exist' in str(e).lower():
                logger.warning('Table or view "%s" does not exist. Treating as empty.', view_name)
            else:
                raise

    async def stream_studies(self, investigation_ids: list[str]) -> AsyncGenerator[StudyRow, None]:
        """Stream studies for given investigations."""
        async for r in self._stream_by_investigation(StudyRow, investigation_ids, "study"):
            yield r

    async def stream_assays(self, investigation_ids: list[str]) -> AsyncGenerator[AssayRow, None]:
        """Stream assets for given investigations."""
        async for r in self._stream_by_investigation(AssayRow, investigation_ids, "assay"):
            yield r

    async def stream_contacts(self, investigation_ids: list[str]) -> AsyncGenerator[ContactRow, None]:
        """Stream contacts for given investigations."""
        async for r in self._stream_by_investigation(ContactRow, investigation_ids, "contact"):
            yield r

    async def stream_publications(self, investigation_ids: list[str]) -> AsyncGenerator[PublicationRow, None]:
        """Stream publications for given investigations."""
        async for r in self._stream_by_investigation(PublicationRow, investigation_ids, "publication"):
            yield r

    async def stream_annotation_tables(self, investigation_ids: list[str]) -> AsyncGenerator[dict[str, Any], None]:
        """Stream annotation tables for given investigations."""
        if not investigation_ids:
            return
        view_name = "vAnnotationTable"
        try:
            async with self.engine.connect() as conn:
                # Use literal_column("*") to select all columns
                c_inv_ref: sqlalchemy.ColumnElement[Any] = column("investigation_ref")
                stmt: sqlalchemy.Select[Any] = (
                    select(sqlalchemy.literal_column("*"))
                    .select_from(table(view_name))
                    .where(c_inv_ref.in_(investigation_ids))
                    .execution_options(stream_results=True)
                )

                result = await conn.stream(stmt)
                async for row in result.mappings():
                    yield dict(row)
        except ProgrammingError as e:
            if f'relation "{view_name.lower()}" does not exist' in str(e).lower():
                logger.warning('Table or view "%s" does not exist. Treating as empty.', view_name)
            else:
                raise

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[AsyncConnection, None]:
        """Context manager for database connection."""
        async with self.engine.connect() as conn:
            yield conn
