import io
import zipfile
from pathlib import Path

import pytest

from factorio_docs.archive import (
    ArchiveDownloader,
    ArchiveExtractor,
    DownloadedArchive,
)
from factorio_docs.releases import FactorioVersion, ResolvedRelease


class TestArchiveDownloader:
    def test_downloads_into_provided_temporary_file(self, tmp_path: Path) -> None:
        source = tmp_path / "archive.zip"
        source.write_bytes(b"archive")
        destination = io.BytesIO()
        release = ResolvedRelease(
            "2.0.77",
            FactorioVersion("2.0.77"),
            source.as_uri(),
        )

        downloaded = ArchiveDownloader.download(release, destination)

        assert downloaded.size == 7
        assert downloaded.content.tell() == 0
        assert downloaded.content.read() == b"archive"

    def test_rejects_nonempty_destination(self, tmp_path: Path) -> None:
        destination = io.BytesIO(b"occupied")
        destination.seek(0)
        release = ResolvedRelease(
            "2.0.77",
            FactorioVersion("2.0.77"),
            (tmp_path / "unused.zip").as_uri(),
        )

        with pytest.raises(ValueError, match="not empty"):
            ArchiveDownloader.download(release, destination)


class TestArchiveExtractor:
    def test_extracts_validated_documentation(self, tmp_path: Path) -> None:
        archive = self._archive(
            {
                "files/runtime-api.json": b"{}",
                "files/prototype-api.json": b"{}",
                "files/static/image.png": b"image",
                "files/article.html": b"<main></main>",
            }
        )
        destination = tmp_path / "extracted"
        destination.mkdir()

        documentation = ArchiveExtractor.extract(archive, destination)

        assert documentation.root == destination / "files"
        assert documentation.runtime_api.read_bytes() == b"{}"
        assert documentation.prototype_api.read_bytes() == b"{}"
        assert documentation.static_directory.is_dir()

    @pytest.mark.parametrize(
        "entry",
        ["../escape", "/absolute", "files/../escape", "files\\escape"],
    )
    def test_rejects_unsafe_entry_paths(self, tmp_path: Path, entry: str) -> None:
        archive = self._archive(
            {
                "files/runtime-api.json": b"{}",
                "files/prototype-api.json": b"{}",
                "files/static/image.png": b"image",
                entry: b"escape",
            }
        )
        destination = tmp_path / "extracted"
        destination.mkdir()

        with pytest.raises(ValueError, match=r"entry path|outside files"):
            ArchiveExtractor.extract(archive, destination)

        assert tuple(destination.iterdir()) == ()

    def test_rejects_missing_required_structure_before_extraction(
        self,
        tmp_path: Path,
    ) -> None:
        archive = self._archive({"files/article.html": b"article"})
        destination = tmp_path / "extracted"
        destination.mkdir()

        with pytest.raises(ValueError, match="missing required entries"):
            ArchiveExtractor.extract(archive, destination)

        assert tuple(destination.iterdir()) == ()

    @staticmethod
    def _archive(entries: dict[str, bytes]) -> DownloadedArchive:
        content = io.BytesIO()
        with zipfile.ZipFile(content, mode="w") as archive:
            for path, value in entries.items():
                archive.writestr(path, value)
        size = content.tell()
        content.seek(0)
        return DownloadedArchive(content, size)
