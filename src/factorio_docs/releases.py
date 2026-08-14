from __future__ import annotations

import logging
import re
import urllib.request
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class ReleaseChannel(Enum):
    """A moving Factorio release channel published by Wube."""

    STABLE = "stable"
    EXPERIMENTAL = "experimental"


@dataclass(frozen=True, slots=True)
class FactorioVersion:
    """A canonical explicit Factorio release version."""

    value: str

    _pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    )

    def __post_init__(self) -> None:
        if self._pattern.fullmatch(self.value) is None:
            message = f"Invalid Factorio version: {self.value!r}"
            raise ValueError(message)

    def __str__(self) -> str:
        return self.value


type VersionRequest = ReleaseChannel | FactorioVersion


@dataclass(frozen=True, slots=True)
class ResolvedRelease:
    """A requested export name and its immutable upstream release."""

    export_name: str
    version: FactorioVersion
    archive_url: str


class VersionRequestParser:
    """Parse CLI version text into the exhaustive version request type."""

    @staticmethod
    def parse(value: str) -> VersionRequest:
        try:
            return ReleaseChannel(value)
        except ValueError:
            return FactorioVersion(value)


class ManifestVersions(BaseModel):
    """The release variants that must share one documentation version."""

    model_config = ConfigDict(extra="ignore", frozen=True, strict=True)

    alpha: str
    expansion: str
    headless: str


class ReleaseManifest(BaseModel):
    """The moving release channels published by Factorio."""

    model_config = ConfigDict(extra="ignore", frozen=True, strict=True)

    stable: ManifestVersions
    experimental: ManifestVersions


class ReleaseResolver:
    """Resolve Factorio channels and explicit versions to documentation archives."""

    _logger = logging.getLogger(__name__)
    _manifest_url = "https://factorio.com/api/latest-releases"
    _archive_url_template = "https://lua-api.factorio.com/{version}/static/archive.zip"
    _request_timeout_seconds = 30

    @classmethod
    def resolve(cls, request: VersionRequest) -> ResolvedRelease:
        if isinstance(request, FactorioVersion):
            version = request
            export_name = request.value
        else:
            cls._logger.info("Resolving Factorio %s release", request.value)
            manifest = cls._fetch_manifest()
            version = cls.resolve_channel(request, manifest)
            export_name = request.value

        return ResolvedRelease(
            export_name=export_name,
            version=version,
            archive_url=cls._archive_url_template.format(version=version),
        )

    @classmethod
    def resolve_channel(
        cls,
        channel: ReleaseChannel,
        manifest: ReleaseManifest,
    ) -> FactorioVersion:
        versions = manifest.stable if channel is ReleaseChannel.STABLE else manifest.experimental
        return cls._require_matching_versions(channel, versions)

    @classmethod
    def _fetch_manifest(cls) -> ReleaseManifest:
        request = urllib.request.Request(
            cls._manifest_url,
            headers={"User-Agent": "factorio-docs"},
        )
        with urllib.request.urlopen(request, timeout=cls._request_timeout_seconds) as response:
            document = response.read()
        cls._logger.debug("Downloaded %d bytes from %s", len(document), cls._manifest_url)
        return ReleaseManifest.model_validate_json(document)

    @staticmethod
    def _require_matching_versions(
        channel: ReleaseChannel,
        versions: ManifestVersions,
    ) -> FactorioVersion:
        alpha = FactorioVersion(versions.alpha)
        expansion = FactorioVersion(versions.expansion)
        headless = FactorioVersion(versions.headless)
        if alpha != expansion or alpha != headless:
            message = (
                f"Factorio {channel.value} release versions differ: "
                f"alpha={alpha}, expansion={expansion}, headless={headless}"
            )
            raise ValueError(message)
        return alpha
