from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from factorio_docs.archive import ArchiveDownloader, ArchiveExtractor
from factorio_docs.builder import DocumentationBuilder
from factorio_docs.export_repository import ExportRepository
from factorio_docs.logging_config import LoggingConfigurator
from factorio_docs.releases import ReleaseResolver, VersionRequestParser
from factorio_docs.workspace import BuildWorkspace


class _Arguments(argparse.Namespace):
    version: str
    refetch: bool
    debug: bool


class CommandLineParser:
    """Parse the public factorio-docs command line."""

    @staticmethod
    def parse(arguments: Sequence[str]) -> _Arguments:
        parser = argparse.ArgumentParser(
            prog="factorio-docs",
            description="Fetch and generate agent-readable Factorio modding documentation.",
        )
        parser.add_argument(
            "--version",
            default="stable",
            help="Factorio version: stable, experimental, or an explicit release",
        )
        parser.add_argument(
            "--refetch",
            action="store_true",
            help="replace documentation that has already been fetched",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="enable verbose diagnostics and tracebacks",
        )
        namespace = _Arguments()
        parser.parse_args(arguments, namespace)
        return namespace


def main() -> None:
    started_at = time.monotonic()
    arguments = CommandLineParser.parse(sys.argv[1:])
    LoggingConfigurator.configure(arguments.debug)
    logger = logging.getLogger(__name__)

    try:
        version_request = VersionRequestParser.parse(arguments.version)
        repository = ExportRepository(Path("ref"))
        target = repository.target(version_request)
        with repository.acquire_lock():
            repository.remove_leftover_staging()
            if repository.contains(target) and not arguments.refetch:
                logger.info(
                    "Factorio documentation was already fetched into %s; "
                    "use --refetch to replace it",
                    target.path,
                )
                return

            release = ReleaseResolver.resolve(version_request)
            with BuildWorkspace.open() as workspace:
                archive = ArchiveDownloader.download(release, workspace.archive)
                documentation = ArchiveExtractor.extract(
                    archive,
                    workspace.extraction_directory,
                )
                generated = DocumentationBuilder.generate(
                    release,
                    documentation,
                    workspace.generation_directory,
                )
                repository.deploy(generated, target)
        logger.info(
            "Fetched Factorio %s documentation to %s in %.1f seconds",
            generated.version,
            target.path.resolve(strict=True),
            time.monotonic() - started_at,
        )
    except (KeyboardInterrupt, Exception) as error:
        if arguments.debug:
            logger.exception("Factorio documentation export failed")
            raise
        logger.log(logging.ERROR, "Factorio documentation export failed: %s", error)
        raise SystemExit(1) from None
