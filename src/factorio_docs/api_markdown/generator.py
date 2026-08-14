from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

from factorio_docs.api_markdown.common import (
    DocumentationRenderer,
    MarkdownPageWriter,
)
from factorio_docs.api_markdown.defines import DefinePagePlanner, DefineRenderer
from factorio_docs.api_markdown.prototype import PrototypeApiRenderer, PrototypePagePlanner
from factorio_docs.api_markdown.runtime import RuntimeApiRenderer, RuntimePagePlanner
from factorio_docs.api_markdown.types import TypeExpressionRenderer
from factorio_docs.models.common import Define
from factorio_docs.models.prototype import PrototypeApi
from factorio_docs.models.runtime import RuntimeApi


class RuntimeMarkdownBuild:
    """Build the runtime metadata and official category pages."""

    _logger = logging.getLogger(__name__)

    @classmethod
    def generate(
        cls,
        api: RuntimeApi,
        static_directory: Path,
        output_directory: Path,
        type_aliases: Mapping[str, str],
    ) -> int:
        documentation = DocumentationRenderer(static_directory, output_directory)
        types = TypeExpressionRenderer()
        pages = RuntimePagePlanner(RuntimeApiRenderer(types, documentation, type_aliases)).plan(api)
        MarkdownPageWriter.write(pages, output_directory)
        cls._logger.info(
            "Generated %d runtime API Markdown pages in %s",
            len(pages),
            output_directory,
        )
        return len(pages)


class PrototypeMarkdownBuild:
    """Build the prototype metadata and official category pages."""

    _logger = logging.getLogger(__name__)

    @classmethod
    def generate(
        cls,
        api: PrototypeApi,
        static_directory: Path,
        output_directory: Path,
        type_aliases: Mapping[str, str],
    ) -> int:
        documentation = DocumentationRenderer(static_directory, output_directory)
        types = TypeExpressionRenderer()
        pages = PrototypePagePlanner(PrototypeApiRenderer(types, documentation, type_aliases)).plan(
            api
        )
        MarkdownPageWriter.write(pages, output_directory)
        cls._logger.info(
            "Generated %d prototype API Markdown pages in %s",
            len(pages),
            output_directory,
        )
        return len(pages)


class SharedDefinesMarkdownBuild:
    """Build the independently merged shared define page."""

    _logger = logging.getLogger(__name__)

    @classmethod
    def generate(
        cls,
        runtime_defines: list[Define],
        prototype_defines: list[Define],
        static_directory: Path,
        output_directory: Path,
    ) -> int:
        documentation = DocumentationRenderer(static_directory, output_directory)
        pages = DefinePagePlanner(DefineRenderer(documentation)).plan(
            runtime_defines,
            prototype_defines,
        )
        MarkdownPageWriter.write(pages, output_directory)
        cls._logger.info(
            "Generated the shared Factorio defines Markdown page in %s",
            output_directory,
        )
        return len(pages)
