from pathlib import Path
from tarfile import TarFile

import pytest
from _pytest.tmpdir import TempPathFactory


@pytest.fixture(scope="session")
def factorio_versions(tmp_path_factory: TempPathFactory) -> Path:
    destination = tmp_path_factory.mktemp("factorio-versions")
    fixture = Path("tests/fixtures/factorio-docs-2.0.75-2.0.77-api-6.tar.xz")
    with TarFile.open(fixture, mode="r:xz") as archive:
        archive.extractall(destination, filter="data")
    return destination
