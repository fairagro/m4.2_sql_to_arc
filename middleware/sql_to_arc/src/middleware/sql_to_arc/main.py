"""SQL-to-ARC middleware component entry point."""

import argparse
import asyncio
import logging
import multiprocessing
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pydantic import ValidationError

from middleware.api_client import ApiClient
from middleware.shared.config.config_wrapper import ConfigWrapper
from middleware.shared.config.logging import configure_logging
from middleware.shared.report import HarvestReport, JsonLdReportSerializer
from middleware.shared.tracing import initialize_tracing
from middleware.sql_to_arc.config import Config
from middleware.sql_to_arc.database import Database
from middleware.sql_to_arc.processor import process_investigations

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="SQL to ARC Converter")
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Show version and exit",
    )
    args = parser.parse_args(argv)
    return args


async def run_conversion(config: Config) -> HarvestReport:
    """Run the conversion and return the finished harvest report."""
    db = Database(config.connection_string.get_secret_value())

    await db.validate_schema()

    async with ApiClient(config.api_client) as client:
        return await process_investigations(db, client, config)


async def main(argv: list[str] | None = None) -> None:
    """Execute the main entry point."""
    args = parse_args(argv)

    if args.version:
        try:
            print(f"sql_to_arc version: {version('sql_to_arc')}")
        except PackageNotFoundError:
            print("sql_to_arc version: unknown (package not installed)")
        return

    try:
        wrapper = ConfigWrapper.from_yaml_file(args.config, prefix="SQL_TO_ARC")
        config = Config.from_config_wrapper(wrapper)
        configure_logging(config.log_level)
    except (FileNotFoundError, IsADirectoryError, ValidationError) as e:
        logger.error("Failed to load configuration: %s", e)
        return

    otlp_endpoint = str(config.otel.endpoint) if config.otel.endpoint else None
    _tracer_provider, tracer = initialize_tracing(
        service_name="sql_to_arc",
        otlp_endpoint=otlp_endpoint,
        log_console_spans=config.otel.log_console_spans,
    )

    with tracer.start_as_current_span("sql_to_arc.main"):
        logger.info("Starting SQL-to-ARC conversion with config: %s", args.config)
        try:
            report = await run_conversion(config)

            logger.info("SQL-to-ARC conversion completed. Report:")
            try:
                print(JsonLdReportSerializer().render(report), end="")
            except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                logger.warning("Failed to serialise harvest report: %s", exc)

            repo = report.repository_reports[0] if report.repository_reports else None
            if repo is None:
                logger.info("Conversion finished with no repository scope.")
            elif repo.failed_datasets > 0:
                processed = repo.harvested_datasets + repo.failed_datasets + repo.skipped_datasets
                logger.warning(
                    "Conversion finished with %d failures out of %d datasets (harvested=%d, skipped=%d).",
                    repo.failed_datasets,
                    processed,
                    repo.harvested_datasets,
                    repo.skipped_datasets,
                )
            else:
                logger.info(
                    "Conversion finished successfully. %d datasets harvested.",
                    repo.harvested_datasets,
                )

        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            logger.critical("Fatal error during conversion process: %s", e, exc_info=True)
            raise


if __name__ == "__main__":
    multiprocessing.freeze_support()
    asyncio.run(main())
