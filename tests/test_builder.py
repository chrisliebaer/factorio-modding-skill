from pathlib import Path

import pytest

from factorio_docs.archive import ExtractedDocumentation
from factorio_docs.builder import DocumentationBuilder
from factorio_docs.releases import FactorioVersion, ResolvedRelease


class TestDocumentationBuilder:
    @pytest.mark.parametrize(
        ("version", "expected_file_count"),
        [
            ("2.0.75", 1533),
            ("2.0.76", 1533),
            ("2.0.77", 1537),
        ],
    )
    def test_generates_complete_pinned_stable_documentation(
        self,
        tmp_path: Path,
        factorio_versions: Path,
        version: str,
        expected_file_count: int,
    ) -> None:
        factorio_version = FactorioVersion(version)
        source = ExtractedDocumentation.parse(factorio_versions / version)
        output = tmp_path / version

        generated = DocumentationBuilder.generate(
            ResolvedRelease(version, factorio_version, "https://example.invalid/archive.zip"),
            source,
            output,
        )

        assert generated.root == output
        assert generated.version == factorio_version
        assert generated.api_version == 6
        assert sum(path.is_file() for path in output.rglob("*")) == expected_file_count
        assert (output / "runtime" / "classes.md").is_file()
        assert (output / "prototype" / "prototypes.md").is_file()
        assert (output / "auxiliary" / "mod-structure.md").is_file()
        assert (output / "defines.md").is_file()
