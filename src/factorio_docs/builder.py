from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from factorio_docs.api_loader import ApiLoader, ValidationReporter
from factorio_docs.api_markdown.common import TypeNameRewriter
from factorio_docs.api_markdown.generator import (
    PrototypeMarkdownBuild,
    RuntimeMarkdownBuild,
    SharedDefinesMarkdownBuild,
)
from factorio_docs.archive import ExtractedDocumentation
from factorio_docs.html_generator import HtmlDocumentationGenerator
from factorio_docs.image_assets import ImageAssetPublisher
from factorio_docs.releases import FactorioVersion, ResolvedRelease


@dataclass(frozen=True, slots=True)
class GeneratedDocumentation:
    """A complete generated documentation tree ready for deployment."""

    root: Path
    version: FactorioVersion
    api_version: int


class DocumentationBuilder:
    """Build all Markdown documentation from one extracted official archive."""

    _logger = logging.getLogger(__name__)
    _redirect_blacklist: ClassVar[frozenset[Path]] = frozenset(
        {
            Path("auxiliary/global.html"),
            Path("concepts/int.html"),
            Path("concepts/uint.html"),
            Path("tree.html"),
        }
    )

    @classmethod
    def generate(
        cls,
        release: ResolvedRelease,
        source: ExtractedDocumentation,
        output_directory: Path,
    ) -> GeneratedDocumentation:
        cls._logger.info("Generating Markdown documentation for Factorio %s", release.version)
        pair = ApiLoader().load_pair(source.runtime_api, source.prototype_api)
        actual_version = FactorioVersion(pair.runtime.application_version)
        if actual_version != release.version:
            message = (
                "Downloaded Factorio documentation version differs from the resolved release: "
                f"{actual_version} != {release.version}"
            )
            raise ValueError(message)
        ValidationReporter().report(pair)
        HtmlDocumentationGenerator.generate(
            source.root,
            output_directory,
            cls._redirect_blacklist,
        )
        published_static_directory = ImageAssetPublisher.publish(
            source.static_directory,
            output_directory,
        )
        aliases = TypeNameRewriter.production_aliases()
        RuntimeMarkdownBuild.generate(
            pair.runtime,
            published_static_directory,
            output_directory,
            aliases,
        )
        PrototypeMarkdownBuild.generate(
            pair.prototype,
            published_static_directory,
            output_directory,
            aliases,
        )
        SharedDefinesMarkdownBuild.generate(
            pair.runtime.defines,
            pair.prototype.defines,
            published_static_directory,
            output_directory,
        )
        cls._logger.info(
            "Generated Factorio %s documentation using API format %d",
            actual_version,
            pair.runtime.api_version,
        )
        return GeneratedDocumentation(output_directory, actual_version, pair.runtime.api_version)
