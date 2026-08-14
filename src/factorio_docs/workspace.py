from __future__ import annotations

import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


@dataclass(frozen=True, slots=True)
class BuildWorkspacePaths:
    """Resources owned by one temporary documentation build workspace."""

    archive: BinaryIO
    extraction_directory: Path
    generation_directory: Path


class BuildWorkspace:
    """Own native temporary resources for one documentation build."""

    @staticmethod
    @contextmanager
    def open() -> Generator[BuildWorkspacePaths]:
        with (
            tempfile.TemporaryFile(mode="w+b") as archive,
            tempfile.TemporaryDirectory(prefix="factorio-docs-") as temporary_name,
        ):
            temporary_directory = Path(temporary_name)
            extraction_directory = temporary_directory / "extracted"
            extraction_directory.mkdir()
            yield BuildWorkspacePaths(
                archive=archive,
                extraction_directory=extraction_directory,
                generation_directory=temporary_directory / "generated",
            )
