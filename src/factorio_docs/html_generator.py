from __future__ import annotations

import logging
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import html_to_markdown
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString


@runtime_checkable
class _HtmlConverter(Protocol):
    def __call__(
        self,
        html: str,
        *,
        options: html_to_markdown.ConversionOptions,
        visitor: object,
    ) -> html_to_markdown.ConversionResult: ...


class AgentTableVisitor:
    """Render HTML tables as compact, tab-delimited Markdown lists."""

    def visit_table_row(
        self,
        _context: object,
        cells: list[str],
        is_header: bool,
    ) -> str:
        if not cells:
            message = "A table row must contain at least one cell"
            raise ValueError(message)

        for cell in cells:
            if "\t" in cell or "\n" in cell or "\r" in cell:
                message = f"Table cell contains ambiguous whitespace: {cell!r}"
                raise ValueError(message)

        prefix = "Table: " if is_header else "* "
        return prefix + "\t".join(cells) + "\n"


@dataclass(frozen=True)
class MarkdownDocument:
    """A converted document and its path relative to the source tree."""

    relative_path: Path
    content: str


class HtmlDocumentationGenerator:
    """Convert a tree of rendered Factorio HTML documentation to Markdown."""

    _logger = logging.getLogger(__name__)
    _converter: object = html_to_markdown.convert

    @classmethod
    def generate(
        cls,
        source_directory: Path,
        output_directory: Path,
        blacklist: frozenset[Path],
    ) -> int:
        documents = cls._convert_documents(source_directory, output_directory, blacklist)
        cls._write_documents(documents, output_directory)
        cls._logger.info(
            "Converted %d Factorio HTML documents from %s to %s",
            len(documents),
            source_directory,
            output_directory,
        )
        return len(documents)

    @classmethod
    def _convert_documents(
        cls,
        source_directory: Path,
        output_directory: Path,
        blacklist: frozenset[Path],
    ) -> tuple[MarkdownDocument, ...]:
        cls._logger.info("Converting Factorio HTML documentation from %s", source_directory)
        source_directory = source_directory.resolve(strict=True)
        if not source_directory.is_dir():
            message = f"HTML source is not a directory: {source_directory}"
            raise NotADirectoryError(message)
        if output_directory.exists():
            message = f"Markdown output already exists: {output_directory}"
            raise FileExistsError(message)

        cls._validate_blacklist(source_directory, blacklist)
        sources = tuple(
            source
            for source in sorted(source_directory.rglob("*.html"))
            if source.relative_to(source_directory) not in blacklist
        )
        if not sources:
            message = f"HTML source contains no documents: {source_directory}"
            raise ValueError(message)

        return tuple(
            MarkdownDocument(
                relative_path=source.relative_to(source_directory).with_suffix(".md"),
                content=cls._convert_article(cls._extract_article(source)),
            )
            for source in sources
        )

    @staticmethod
    def _validate_blacklist(source_directory: Path, blacklist: frozenset[Path]) -> None:
        for relative_path in blacklist:
            if relative_path.is_absolute() or relative_path.suffix != ".html":
                message = f"Blacklisted path must be a relative HTML path: {relative_path}"
                raise ValueError(message)
            source = source_directory / relative_path
            if not source.is_file():
                message = f"Blacklisted HTML document does not exist: {source}"
                raise FileNotFoundError(message)

    @classmethod
    def _extract_article(cls, source: Path) -> str:
        cls._logger.debug("Converting Factorio HTML document %s", source)
        html = source.read_text(encoding="utf-8")
        document = BeautifulSoup(html, "lxml")
        articles = document.select(
            "main.panel-inset-lighter, div.docs-content > div.panel-inset-lighter"
        )
        if articles:
            article = cls._require_single_article(articles, source)
        else:
            article = cls._extract_root_page_article(html, source)

        cls._remove_heading_permalinks(article, source)
        cls._remove_responsive_table_rows(article, source)
        cls._normalize_single_source_srcsets(article, source)
        return article.decode_contents()

    @classmethod
    def _extract_root_page_article(cls, html: str, source: Path) -> Tag:
        """The archive's root index.html and license.html use a content panel and no main."""
        document = BeautifulSoup(html, "lxml")
        articles = document.select("#docs-layout-panel > div.panel-inset.mt0")
        return cls._require_single_article(articles, source)

    @staticmethod
    def _require_single_article(articles: Sequence[Tag], source: Path) -> Tag:
        if len(articles) != 1:
            message = (
                f"Expected exactly one documentation article in {source}, found {len(articles)}"
            )
            raise ValueError(message)
        return articles[0]

    @staticmethod
    def _remove_heading_permalinks(article: Tag, source: Path) -> None:
        for image in article.select('a.link > img[src$="link-symbol.png"]'):
            link = image.parent
            if not isinstance(link, Tag) or link.name != "a":
                message = f"Heading permalink has an unexpected parent in {source}"
                raise ValueError(message)
            for content in link.contents:
                if content is image:
                    continue
                if not isinstance(content, NavigableString) or content.strip():
                    message = f"Heading permalink contains unexpected content in {source}"
                    raise ValueError(message)
            link.decompose()

    @staticmethod
    def _remove_responsive_table_rows(article: Tag, source: Path) -> None:
        for row in article.select("tr.tr-separate-description"):
            cells = row.find_all("td", recursive=False)
            if (
                len(cells) != 1
                or cells[0].get("class") != ["td-modif"]
                or cells[0].get("colspan") != "3"
            ):
                message = f"Responsive table row has an unexpected structure in {source}"
                raise ValueError(message)
            previous_row = row.find_previous_sibling("tr")
            if not isinstance(previous_row, Tag):
                message = f"Responsive table row has no primary row in {source}"
                raise TypeError(message)
            primary_description = previous_row.select_one("td.td-inline-description")
            if not isinstance(primary_description, Tag):
                message = f"Responsive table row has no primary description in {source}"
                raise TypeError(message)
            if row.get_text(" ", strip=True) != primary_description.get_text(" ", strip=True):
                message = f"Responsive table descriptions differ in {source}"
                raise ValueError(message)
            row.decompose()

    @staticmethod
    def _normalize_single_source_srcsets(article: Tag, source: Path) -> None:
        for image in article.select("img[srcset]"):
            source_set = image.get("srcset")
            if not isinstance(source_set, str):
                message = f"Image has a non-text srcset in {source}"
                raise TypeError(message)
            source_candidates = source_set.split(",")
            source_parts = source_candidates[0].split()
            if len(source_candidates) != 1 or len(source_parts) != 1:
                message = f"Image must have a single-path srcset in {source}: {source_set!r}"
                raise ValueError(message)
            existing_source = image.get("src")
            if existing_source is not None and not isinstance(existing_source, str):
                message = f"Image has a non-text src in {source}"
                raise TypeError(message)
            if existing_source is None:
                image["src"] = source_parts[0]
            del image["srcset"]

    @classmethod
    def _convert_article(cls, article_html: str) -> str:
        converter = cls._converter
        if not isinstance(converter, _HtmlConverter):
            message = "html-to-markdown exposes an incompatible conversion function"
            raise TypeError(message)
        conversion = converter(
            article_html,
            options=html_to_markdown.ConversionOptions(bullets="*"),
            visitor=AgentTableVisitor(),
        )
        if conversion.content is None or not conversion.content.strip():
            message = "HTML conversion produced no Markdown content"
            raise ValueError(message)
        return conversion.content

    @staticmethod
    def _write_documents(
        documents: tuple[MarkdownDocument, ...],
        output_directory: Path,
    ) -> None:
        output_parent = output_directory.parent
        output_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=output_parent,
            prefix=f".{output_directory.name}-",
        ) as temporary_name:
            temporary_directory = Path(temporary_name)
            for document in documents:
                destination = temporary_directory / document.relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(document.content, encoding="utf-8")
            temporary_directory.rename(output_directory)
