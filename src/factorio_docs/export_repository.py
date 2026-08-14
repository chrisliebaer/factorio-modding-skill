from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from factorio_docs.builder import GeneratedDocumentation
from factorio_docs.releases import FactorioVersion, ReleaseChannel, VersionRequest


@dataclass(frozen=True, slots=True)
class ExportTarget:
    """A version target derived from an export repository."""

    path: Path


@dataclass(frozen=True, slots=True)
class OutputLock:
    """Ownership of the atomic marker coordinating one export repository."""

    path: Path


@dataclass(frozen=True, slots=True)
class ExportRepository:
    """The paths and deployment operations belonging to one export parent."""

    root: Path

    _lock_name = ".factorio-docs.lock"
    _staging_name = "_staging"
    _logger = logging.getLogger(__name__)

    @contextmanager
    def acquire_lock(self) -> Generator[OutputLock]:
        self._prepare_root()
        lock_path = self.root / self._lock_name
        try:
            descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError:
            message = f"Output lock exists: {lock_path}"
            raise FileExistsError(message) from None
        try:
            os.close(descriptor)
        except BaseException:
            lock_path.unlink()
            raise

        try:
            yield OutputLock(lock_path)
        finally:
            lock_path.unlink()

    def target(self, request: VersionRequest) -> ExportTarget:
        match request:
            case ReleaseChannel():
                name = request.value
            case FactorioVersion():
                name = request.value
        return ExportTarget(self.root / name)

    def remove_leftover_staging(self) -> None:
        staging = self.root / self._staging_name
        if staging.is_symlink() or (staging.exists() and not staging.is_dir()):
            message = f"Export staging path is not a directory: {staging}"
            raise NotADirectoryError(message)
        if staging.is_dir():
            self._logger.info("Removing leftover export staging directory %s", staging)
            shutil.rmtree(staging)

    @staticmethod
    def contains(target: ExportTarget) -> bool:
        if target.path.is_symlink() or (target.path.exists() and not target.path.is_dir()):
            message = f"Factorio documentation target is not a directory: {target.path}"
            raise NotADirectoryError(message)
        return target.path.is_dir()

    def deploy(
        self,
        documentation: GeneratedDocumentation,
        target: ExportTarget,
    ) -> None:
        staging = self.root / self._staging_name
        if staging.exists() or staging.is_symlink():
            message = f"Export staging path already exists: {staging}"
            raise FileExistsError(message)
        if target.path.parent != self.root:
            message = f"Export target does not belong to repository {self.root}: {target.path}"
            raise ValueError(message)
        if not documentation.root.is_dir():
            message = f"Generated documentation is not a directory: {documentation.root}"
            raise NotADirectoryError(message)

        self._logger.info("Publishing Factorio documentation to %s", target.path)
        try:
            shutil.move(documentation.root, staging)
            if self.contains(target):
                shutil.rmtree(target.path)
            staging.rename(target.path)
        except BaseException:
            if staging.is_dir() and not staging.is_symlink():
                shutil.rmtree(staging)
            raise

    def _prepare_root(self) -> None:
        if self.root.is_symlink() or (self.root.exists() and not self.root.is_dir()):
            message = f"Export parent is not a directory: {self.root}"
            raise NotADirectoryError(message)
        self.root.mkdir(parents=True, exist_ok=True)
