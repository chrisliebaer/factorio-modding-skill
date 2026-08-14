import pytest
from pydantic import ValidationError

from factorio_docs.releases import (
    FactorioVersion,
    ReleaseChannel,
    ReleaseManifest,
    ReleaseResolver,
    VersionRequestParser,
)


class TestVersionRequestParser:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("stable", ReleaseChannel.STABLE),
            ("experimental", ReleaseChannel.EXPERIMENTAL),
            ("2.1.14", FactorioVersion("2.1.14")),
        ],
    )
    def test_parses_exhaustive_version_requests(
        self,
        text: str,
        expected: ReleaseChannel | FactorioVersion,
    ) -> None:
        assert VersionRequestParser.parse(text) == expected

    @pytest.mark.parametrize(
        "text",
        ["latest", "2.1", "2.01.14", "v2.1.14", "2.1.14.0", ""],
    )
    def test_rejects_noncanonical_versions(self, text: str) -> None:
        with pytest.raises(ValueError, match="Invalid Factorio version"):
            VersionRequestParser.parse(text)


class TestReleaseResolver:
    def test_explicit_version_bypasses_manifest(self) -> None:
        release = ReleaseResolver.resolve(FactorioVersion("2.1.14"))

        assert release.export_name == "2.1.14"
        assert release.version == FactorioVersion("2.1.14")
        assert release.archive_url == ("https://lua-api.factorio.com/2.1.14/static/archive.zip")

    def test_resolves_matching_channel_variants(self) -> None:
        manifest = ReleaseManifest.model_validate(
            {
                "stable": {
                    "alpha": "2.0.77",
                    "expansion": "2.0.77",
                    "headless": "2.0.77",
                    "demo": "1.1.110",
                },
                "experimental": {
                    "alpha": "2.1.14",
                    "expansion": "2.1.14",
                    "headless": "2.1.14",
                },
            }
        )

        assert ReleaseResolver.resolve_channel(ReleaseChannel.STABLE, manifest) == (
            FactorioVersion("2.0.77")
        )
        assert ReleaseResolver.resolve_channel(
            ReleaseChannel.EXPERIMENTAL,
            manifest,
        ) == FactorioVersion("2.1.14")

    def test_rejects_divergent_channel_variants(self) -> None:
        manifest = ReleaseManifest.model_validate(
            {
                "stable": {
                    "alpha": "2.0.77",
                    "expansion": "2.0.76",
                    "headless": "2.0.77",
                },
                "experimental": {
                    "alpha": "2.1.14",
                    "expansion": "2.1.14",
                    "headless": "2.1.14",
                },
            }
        )

        with pytest.raises(ValueError, match="release versions differ"):
            ReleaseResolver.resolve_channel(ReleaseChannel.STABLE, manifest)

    def test_manifest_is_strict_and_frozen(self) -> None:
        with pytest.raises(ValidationError):
            ReleaseManifest.model_validate(
                {
                    "stable": {
                        "alpha": 2077,
                        "expansion": "2.0.77",
                        "headless": "2.0.77",
                    },
                    "experimental": {
                        "alpha": "2.1.14",
                        "expansion": "2.1.14",
                        "headless": "2.1.14",
                    },
                }
            )
