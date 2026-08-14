from __future__ import annotations

import logging
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest import LogCaptureFixture, MonkeyPatch

import factorio_docs.cli as cli
from factorio_docs.archive import ExtractedDocumentation
from factorio_docs.builder import GeneratedDocumentation
from factorio_docs.releases import FactorioVersion, ResolvedRelease, VersionRequest


@dataclass(frozen=True, slots=True)
class _LocalReleaseResolver:
    release: ResolvedRelease

    def resolve(self, request: VersionRequest) -> ResolvedRelease:
        if request != self.release.version:
            message = f"Unexpected release request: {request}"
            raise AssertionError(message)
        return self.release


class _ForbiddenReleaseResolver:
    @staticmethod
    def resolve(request: VersionRequest) -> ResolvedRelease:
        message = f"Existing export unexpectedly resolved release {request}"
        raise AssertionError(message)


@dataclass(frozen=True, slots=True)
class _DocumentationBuilder:
    fail: bool

    def generate(
        self,
        release: ResolvedRelease,
        source: ExtractedDocumentation,
        output_directory: Path,
    ) -> GeneratedDocumentation:
        if not source.runtime_api.is_file() or not source.prototype_api.is_file():
            message = "Archive was not extracted before generation"
            raise AssertionError(message)
        if self.fail:
            message = "Synthetic parser failure"
            raise RuntimeError(message)
        output_directory.mkdir()
        (output_directory / "version.txt").write_text(
            release.version.value,
            encoding="utf-8",
        )
        return GeneratedDocumentation(output_directory, release.version, 6)


class TestCommandLinePipeline:
    def test_success_publishes_target_and_cleans_build_artifacts(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        caplog: LogCaptureFixture,
    ) -> None:
        self._configure_pipeline(tmp_path, monkeypatch, fail=False, refetch=False)
        caplog.set_level(logging.INFO)

        cli.main()

        output = tmp_path / "ref"
        assert (output / "2.0.77" / "version.txt").read_text(encoding="utf-8") == ("2.0.77")
        assert not (output / ".factorio-docs.lock").exists()
        assert not (output / "_staging").exists()
        target = output / "2.0.77"
        assert re.fullmatch(
            rf"Fetched Factorio 2\.0\.77 documentation to {re.escape(str(target))} "
            r"in \d+\.\d seconds",
            caplog.messages[-1],
        )

    def test_existing_target_skips_pipeline_without_refetch(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["factorio-docs", "--version", "2.0.77"])
        monkeypatch.setattr(cli, "ReleaseResolver", _ForbiddenReleaseResolver)
        target = tmp_path / "ref" / "2.0.77"
        target.mkdir(parents=True)
        (target / "existing").write_text("existing", encoding="utf-8")

        cli.main()

        assert (target / "existing").read_text(encoding="utf-8") == "existing"
        assert not (tmp_path / "ref" / ".factorio-docs.lock").exists()

    def test_refetch_replaces_existing_target(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        self._configure_pipeline(tmp_path, monkeypatch, fail=False, refetch=True)
        target = tmp_path / "ref" / "2.0.77"
        target.mkdir(parents=True)
        (target / "stale").write_text("stale", encoding="utf-8")

        cli.main()

        assert not (target / "stale").exists()
        assert (target / "version.txt").read_text(encoding="utf-8") == "2.0.77"
        assert not (tmp_path / "ref" / "_staging").exists()

    def test_parser_failure_preserves_target_and_cleans_build_artifacts(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        self._configure_pipeline(tmp_path, monkeypatch, fail=True, refetch=True)
        target = tmp_path / "ref" / "2.0.77"
        target.mkdir(parents=True)
        (target / "existing").write_text("existing", encoding="utf-8")

        with pytest.raises(SystemExit) as failure:
            cli.main()

        assert failure.value.code == 1
        assert (target / "existing").read_text(encoding="utf-8") == "existing"
        assert not (tmp_path / "ref" / ".factorio-docs.lock").exists()
        assert not (tmp_path / "ref" / "_staging").exists()

    def test_leftover_staging_is_removed_before_early_skip(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["factorio-docs", "--version", "2.0.77"])
        monkeypatch.setattr(cli, "ReleaseResolver", _ForbiddenReleaseResolver)
        (tmp_path / "ref" / "2.0.77").mkdir(parents=True)
        staging = tmp_path / "ref" / "_staging"
        staging.mkdir()
        (staging / "partial").write_text("partial", encoding="utf-8")

        cli.main()

        assert not staging.exists()

    def _configure_pipeline(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        *,
        fail: bool,
        refetch: bool,
    ) -> None:
        archive = tmp_path / "archive.zip"
        with zipfile.ZipFile(archive, mode="w") as compressed:
            compressed.writestr("files/runtime-api.json", "{}")
            compressed.writestr("files/prototype-api.json", "{}")
            compressed.writestr("files/static/image.png", "image")
        version = FactorioVersion("2.0.77")
        release = ResolvedRelease(version.value, version, archive.as_uri())
        command = ["factorio-docs", "--version", version.value]
        if refetch:
            command.append("--refetch")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", command)
        monkeypatch.setattr(cli, "ReleaseResolver", _LocalReleaseResolver(release))
        monkeypatch.setattr(cli, "DocumentationBuilder", _DocumentationBuilder(fail))
