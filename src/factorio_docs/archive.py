from __future__ import annotations

import logging
import os
import shutil
import stat
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from factorio_docs.releases import ResolvedRelease


@dataclass(frozen=True, slots=True)
class DownloadedArchive:
    """A downloaded archive held by its owning temporary workspace."""

    content: BinaryIO
    size: int


@dataclass(frozen=True, slots=True)
class ExtractedDocumentation:
    """The validated paths exposed by an extracted Factorio documentation archive."""

    root: Path
    runtime_api: Path
    prototype_api: Path
    static_directory: Path

    @classmethod
    def parse(cls, extraction_directory: Path) -> ExtractedDocumentation:
        root = extraction_directory / "files"
        runtime_api = root / "runtime-api.json"
        prototype_api = root / "prototype-api.json"
        static_directory = root / "static"
        if not root.is_dir():
            message = f"Factorio archive does not contain its files directory: {root}"
            raise ValueError(message)
        if not runtime_api.is_file():
            message = f"Factorio archive does not contain runtime-api.json: {runtime_api}"
            raise ValueError(message)
        if not prototype_api.is_file():
            message = f"Factorio archive does not contain prototype-api.json: {prototype_api}"
            raise ValueError(message)
        if not static_directory.is_dir():
            message = f"Factorio archive does not contain its static directory: {static_directory}"
            raise ValueError(message)
        return cls(root, runtime_api, prototype_api, static_directory)


class ArchiveDownloader:
    """Download an official Factorio documentation archive."""

    _logger = logging.getLogger(__name__)
    _request_timeout_seconds = 60
    _copy_buffer_size = 1024 * 1024

    @classmethod
    def download(
        cls,
        release: ResolvedRelease,
        destination: BinaryIO,
    ) -> DownloadedArchive:
        destination.seek(0, os.SEEK_END)
        if destination.tell() != 0:
            message = "Temporary archive destination is not empty"
            raise ValueError(message)
        destination.seek(0, os.SEEK_SET)
        cls._logger.info(
            "Downloading Factorio %s documentation from %s",
            release.version,
            release.archive_url,
        )
        request = urllib.request.Request(
            release.archive_url,
            headers={"User-Agent": "factorio-docs"},
        )
        with urllib.request.urlopen(request, timeout=cls._request_timeout_seconds) as response:
            shutil.copyfileobj(response, destination, cls._copy_buffer_size)
        size = destination.tell()
        if size == 0:
            message = f"Downloaded Factorio documentation archive is empty: {release.archive_url}"
            raise ValueError(message)
        destination.seek(0)
        cls._logger.debug("Downloaded %d bytes from %s", size, release.archive_url)
        return DownloadedArchive(destination, size)


class ArchiveExtractor:
    """Validate and extract a Factorio documentation ZIP archive."""

    _logger = logging.getLogger(__name__)

    @classmethod
    def extract(
        cls,
        archive: DownloadedArchive,
        extraction_directory: Path,
    ) -> ExtractedDocumentation:
        if tuple(extraction_directory.iterdir()):
            message = f"Archive extraction directory is not empty: {extraction_directory}"
            raise ValueError(message)
        cls._logger.info("Extracting Factorio documentation archive")
        archive.content.seek(0)
        with zipfile.ZipFile(archive.content) as compressed:
            cls._validate_entries(compressed.infolist())
            bad_entry = compressed.testzip()
            if bad_entry is not None:
                message = f"Factorio documentation archive contains a corrupt entry: {bad_entry}"
                raise zipfile.BadZipFile(message)
            compressed.extractall(extraction_directory)
        documentation = ExtractedDocumentation.parse(extraction_directory)
        cls._logger.debug("Extracted Factorio documentation into %s", extraction_directory)
        return documentation

    @classmethod
    def _validate_entries(cls, entries: list[zipfile.ZipInfo]) -> None:
        if not entries:
            message = "Factorio documentation archive contains no entries"
            raise ValueError(message)
        destinations: set[PurePosixPath] = set()
        for entry in entries:
            destination = cls._parse_entry_path(entry)
            if destination in destinations:
                message = f"Factorio documentation archive repeats an entry: {entry.filename}"
                raise ValueError(message)
            destinations.add(destination)
            if entry.flag_bits & 1:
                message = (
                    f"Factorio documentation archive contains an encrypted entry: {entry.filename}"
                )
                raise ValueError(message)
            unix_mode = entry.external_attr >> 16
            if stat.S_ISLNK(unix_mode):
                message = (
                    f"Factorio documentation archive contains a symbolic link: {entry.filename}"
                )
                raise ValueError(message)

        required = {
            PurePosixPath("files/runtime-api.json"),
            PurePosixPath("files/prototype-api.json"),
            PurePosixPath("files/static"),
        }
        available = destinations | {path.parent for path in destinations}
        missing = required - available
        if missing:
            rendered = ", ".join(str(path) for path in sorted(missing))
            message = f"Factorio documentation archive is missing required entries: {rendered}"
            raise ValueError(message)

    @staticmethod
    def _parse_entry_path(entry: zipfile.ZipInfo) -> PurePosixPath:
        name = entry.filename
        if not name or "\\" in name or name.startswith("/"):
            message = f"Factorio documentation archive contains an invalid entry path: {name!r}"
            raise ValueError(message)
        raw_parts = name.split("/")
        content_parts = raw_parts[:-1] if entry.is_dir() else raw_parts
        if not content_parts or any(part in {"", ".", ".."} for part in content_parts):
            message = f"Factorio documentation archive contains an invalid entry path: {name!r}"
            raise ValueError(message)
        if entry.is_dir() and raw_parts[-1] != "":
            message = (
                f"Factorio documentation archive contains an invalid directory entry: {name!r}"
            )
            raise ValueError(message)
        path = PurePosixPath(*content_parts)
        if path.parts[0] != "files":
            message = f"Factorio documentation archive entry is outside files/: {name!r}"
            raise ValueError(message)
        return path
