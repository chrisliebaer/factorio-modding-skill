from pathlib import Path

import pytest

from factorio_docs.workspace import BuildWorkspace


class TestBuildWorkspace:
    def test_cleans_all_resources_after_success(self) -> None:
        with BuildWorkspace.open() as workspace:
            temporary_root = workspace.extraction_directory.parent
            workspace.archive.write(b"archive")
            workspace.generation_directory.mkdir()
            (workspace.generation_directory / "result").write_text(
                "result",
                encoding="utf-8",
            )

        assert workspace.archive.closed
        assert not temporary_root.exists()

    def test_cleans_all_resources_after_failure(self) -> None:
        temporary_root = Path()
        message = "Generation failed"

        with (
            pytest.raises(
                RuntimeError,
                match="Generation failed",
            ),
            BuildWorkspace.open() as workspace,
        ):
            temporary_root = workspace.extraction_directory.parent
            raise RuntimeError(message)

        assert workspace.archive.closed
        assert not temporary_root.exists()
