from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from factorio_docs.models.common import DocumentedMember, Image


@dataclass(frozen=True, slots=True)
class MarkdownPage:
    """A generated Markdown page relative to an API output root."""

    relative_path: Path
    content: str


class TypeNameRewriter:
    """Apply the configured aliases to atomic API type names."""

    @staticmethod
    def production_aliases() -> dict[str, str]:
        return {"boolean": "bool"}

    @staticmethod
    def immutable(aliases: Mapping[str, str]) -> Mapping[str, str]:
        return MappingProxyType(dict(aliases))

    @staticmethod
    def rewrite(name: str, aliases: Mapping[str, str]) -> str:
        return aliases.get(name, name)


class MetadataRenderer:
    """Normalize and render metadata at every ownership level."""

    @staticmethod
    def visibility_items(visibility: Sequence[str] | None) -> list[str]:
        if visibility is None:
            return []
        return ["Space Age" if item == "space_age" else item for item in visibility]

    @classmethod
    def property_items(
        cls,
        alternative_name: str | None,
        override: bool,
        visibility: Sequence[str] | None,
    ) -> list[str]:
        items = cls.visibility_items(visibility)
        if alternative_name is not None:
            items.append(f"alias=`{alternative_name}`")
        if override:
            items.append("override")
        return items

    @staticmethod
    def line(items: list[str], indentation: str) -> str:
        if not items:
            message = "A metadata line requires at least one item"
            raise ValueError(message)
        return f"{indentation}* meta: {', '.join(sorted(items, key=str.casefold))}"


class MarkdownAssembler:
    """Build compact Markdown blocks while retaining source documentation."""

    @classmethod
    def documented_declaration(
        cls,
        declaration: str,
        description: str,
    ) -> list[str]:
        if not description:
            return [declaration]
        first_paragraph, separator, remainder = description.partition("\n\n")
        if "\n" in first_paragraph:
            return [declaration, "", description]
        lines = [f"{declaration} - {first_paragraph}"]
        if separator:
            lines.extend(("", remainder))
        return lines

    @classmethod
    def detail(cls, prefix: str, description: str, indentation: str) -> list[str]:
        line = f"{indentation}* {prefix}"
        if not description:
            return [line]
        first_paragraph, separator, remainder = description.partition("\n\n")
        if "\n" in first_paragraph:
            return [line, "", cls._indent(description, indentation + "  ")]
        lines = [f"{line} - {first_paragraph}"]
        if separator:
            lines.extend(("", cls._indent(remainder, indentation + "  ")))
        return lines

    @staticmethod
    def _indent(value: str, indentation: str) -> str:
        return "\n".join(f"{indentation}{line}" if line else line for line in value.splitlines())

    @staticmethod
    def code(value: str) -> str:
        if "``" in value:
            message = "Signature contains an unsupported double-backtick sequence"
            raise ValueError(message)
        delimiter = "``" if "`" in value else "`"
        return f"{delimiter}{value}{delimiter}"

    @staticmethod
    def join_blocks(blocks: list[list[str]]) -> str:
        return "\n\n".join("\n".join(block) for block in blocks if block) + "\n"


@dataclass(frozen=True, slots=True, eq=False)
class DocumentationRenderer:
    """Render documentation fields shared by API entities."""

    _static_directory: Path
    _output_directory: Path

    def __init__(self, static_directory: Path, output_directory: Path) -> None:
        resolved_static_directory = static_directory.resolve(strict=True)
        if not resolved_static_directory.is_dir():
            message = f"Static asset source is not a directory: {resolved_static_directory}"
            raise NotADirectoryError(message)
        object.__setattr__(self, "_static_directory", resolved_static_directory)
        object.__setattr__(self, "_output_directory", output_directory.resolve())

    def render_member_extras(
        self,
        member: DocumentedMember,
        page_path: Path,
    ) -> list[str]:
        return self.render_extras(
            member.lists,
            member.examples,
            member.images,
            page_path,
        )

    def render_extras(
        self,
        lists: list[str] | None,
        examples: list[str] | None,
        images: list[Image] | None,
        page_path: Path,
    ) -> list[str]:
        blocks: list[str] = []
        if lists is not None:
            blocks.extend(lists)
        if examples is not None:
            blocks.extend(examples)
        if images is not None:
            blocks.extend(self._render_image(image, page_path) for image in images)
        return blocks

    def _render_image(
        self,
        image: Image,
        page_path: Path,
    ) -> str:
        source = self._static_directory / "images" / image.filename
        if not source.is_file():
            message = f"Documented image does not exist: {source}"
            raise FileNotFoundError(message)
        destination_parent = (self._output_directory / page_path).parent
        relative_source = Path(os.path.relpath(source, destination_parent)).as_posix()
        caption = image.caption if image.caption is not None else ""
        return f"![{caption}]({relative_source})"


class MarkdownPageWriter:
    """Publish a complete set of generated pages after validation and rendering."""

    @staticmethod
    def write(pages: tuple[MarkdownPage, ...], output_directory: Path) -> None:
        if not pages:
            message = "A Markdown build must contain at least one page"
            raise ValueError(message)
        relative_paths: set[Path] = set()
        for page in pages:
            if page.relative_path.is_absolute() or page.relative_path.suffix != ".md":
                message = f"Markdown output path must be relative: {page.relative_path}"
                raise ValueError(message)
            if page.relative_path in relative_paths:
                message = f"Duplicate Markdown output path: {page.relative_path}"
                raise ValueError(message)
            if not page.content.strip():
                message = f"Markdown page is empty: {page.relative_path}"
                raise ValueError(message)
            relative_paths.add(page.relative_path)

        output_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=output_directory,
            prefix=".api-markdown-",
        ) as temporary_name:
            temporary_directory = Path(temporary_name)
            for page in pages:
                temporary_path = temporary_directory / page.relative_path
                temporary_path.parent.mkdir(parents=True, exist_ok=True)
                temporary_path.write_text(page.content, encoding="utf-8")
            for page in pages:
                source = temporary_directory / page.relative_path
                destination = output_directory / page.relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                source.replace(destination)
