from pathlib import Path

import pytest

from factorio_docs.builder import GeneratedDocumentation
from factorio_docs.export_repository import ExportRepository
from factorio_docs.releases import FactorioVersion


class TestExportRepository:
    def test_lock_is_removed_after_success_and_failure(self, tmp_path: Path) -> None:
        repository = ExportRepository(tmp_path / "output")
        lock_path = repository.root / ".factorio-docs.lock"

        with repository.acquire_lock() as lock:
            assert lock.path == lock_path
            assert lock_path.is_file()
        assert not lock_path.exists()

        message = "Operation failed"
        with pytest.raises(RuntimeError, match="failed"), repository.acquire_lock():
            raise RuntimeError(message)
        assert not lock_path.exists()

    def test_existing_lock_fails_immediately_and_remains(self, tmp_path: Path) -> None:
        repository = ExportRepository(tmp_path / "output")
        repository.root.mkdir()
        lock_path = repository.root / ".factorio-docs.lock"
        lock_path.write_text("owner", encoding="utf-8")

        with (
            pytest.raises(
                FileExistsError,
                match=str(lock_path),
            ),
            repository.acquire_lock(),
        ):
            pytest.fail("existing marker must prevent lock acquisition")

        assert lock_path.read_text(encoding="utf-8") == "owner"

    def test_removes_the_single_leftover_staging_directory(self, tmp_path: Path) -> None:
        repository = ExportRepository(tmp_path / "output")
        staging = repository.root / "_staging"
        staging.mkdir(parents=True)
        (staging / "partial").write_text("partial", encoding="utf-8")

        repository.remove_leftover_staging()

        assert not staging.exists()

    def test_deploys_and_replaces_existing_target(self, tmp_path: Path) -> None:
        repository = ExportRepository(tmp_path / "output")
        target = repository.target(FactorioVersion("2.0.77"))
        target.path.mkdir(parents=True)
        (target.path / "stale").write_text("stale", encoding="utf-8")
        generated_root = tmp_path / "temporary" / "generated"
        generated_root.mkdir(parents=True)
        (generated_root / "current").write_text("current", encoding="utf-8")
        generated = GeneratedDocumentation(
            generated_root,
            FactorioVersion("2.0.77"),
            6,
        )

        repository.deploy(generated, target)

        assert target.path.is_dir()
        assert (target.path / "current").read_text(encoding="utf-8") == "current"
        assert not (target.path / "stale").exists()
        assert not generated_root.exists()
        assert not (repository.root / "_staging").exists()

    def test_deployment_failure_removes_partial_staging(self, tmp_path: Path) -> None:
        repository = ExportRepository(tmp_path / "output")
        repository.root.mkdir()
        target = repository.target(FactorioVersion("2.0.77"))
        target.path.write_text("invalid target", encoding="utf-8")
        generated_root = tmp_path / "temporary" / "generated"
        generated_root.mkdir(parents=True)
        (generated_root / "current").write_text("current", encoding="utf-8")
        generated = GeneratedDocumentation(
            generated_root,
            FactorioVersion("2.0.77"),
            6,
        )

        with pytest.raises(NotADirectoryError, match="target is not a directory"):
            repository.deploy(generated, target)

        assert target.path.read_text(encoding="utf-8") == "invalid target"
        assert not (repository.root / "_staging").exists()
