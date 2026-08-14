from pathlib import Path

import pytest

from factorio_docs.api_loader import ApiLoader


class TestApiLoader:
    @pytest.mark.parametrize(
        ("version", "runtime_counts", "prototype_counts"),
        [
            ("2.0.75", (148, 219, 418, 9, 3, 60), (278, 686, 60)),
            ("2.0.76", (148, 219, 418, 9, 3, 60), (278, 686, 60)),
            ("2.0.77", (148, 219, 420, 9, 3, 60), (278, 687, 60)),
        ],
    )
    def test_complete_factorio_exports_parse(
        self,
        factorio_versions: Path,
        version: str,
        runtime_counts: tuple[int, int, int, int, int, int],
        prototype_counts: tuple[int, int, int],
    ) -> None:
        source = factorio_versions / version / "files"
        pair = ApiLoader().load_pair(
            source / "runtime-api.json",
            source / "prototype-api.json",
        )

        assert pair.runtime.application_version == version
        assert pair.prototype.application_version == version
        assert pair.runtime.api_version == 6
        assert pair.prototype.api_version == 6
        assert (
            len(pair.runtime.classes),
            len(pair.runtime.events),
            len(pair.runtime.concepts),
            len(pair.runtime.global_objects),
            len(pair.runtime.global_functions),
            len(pair.runtime.defines),
        ) == runtime_counts
        assert (
            len(pair.prototype.prototypes),
            len(pair.prototype.types),
            len(pair.prototype.defines),
        ) == prototype_counts
