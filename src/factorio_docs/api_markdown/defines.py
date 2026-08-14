from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from factorio_docs.api_markdown.common import (
    DocumentationRenderer,
    MarkdownAssembler,
    MarkdownPage,
)
from factorio_docs.models.common import Define, DefineValue


class DefineCollectionMerger:
    """Merge runtime and prototype definitions under both sources' order constraints."""

    @classmethod
    def merge(
        cls,
        runtime_defines: list[Define],
        prototype_defines: list[Define],
    ) -> tuple[Define, ...]:
        runtime_by_name = cls._index(runtime_defines, "runtime")
        prototype_by_name = cls._index(prototype_defines, "prototype")
        shared_names = runtime_by_name.keys() & prototype_by_name.keys()
        for name in shared_names:
            if runtime_by_name[name] != prototype_by_name[name]:
                message = f"Runtime and prototype define subtrees differ: {name}"
                raise ValueError(message)

        runtime_shared = [item.name for item in runtime_defines if item.name in shared_names]
        prototype_shared = [item.name for item in prototype_defines if item.name in shared_names]
        if runtime_shared != prototype_shared:
            message = "Runtime and prototype defines have incompatible shared ordering"
            raise ValueError(message)

        merged: list[Define] = []
        runtime_index = 0
        prototype_index = 0
        while runtime_index < len(runtime_defines) or prototype_index < len(prototype_defines):
            if runtime_index == len(runtime_defines):
                merged.append(prototype_defines[prototype_index])
                prototype_index += 1
                continue
            if prototype_index == len(prototype_defines):
                merged.append(runtime_defines[runtime_index])
                runtime_index += 1
                continue

            runtime = runtime_defines[runtime_index]
            prototype = prototype_defines[prototype_index]
            if runtime.name == prototype.name:
                merged.append(runtime)
                runtime_index += 1
                prototype_index += 1
            elif runtime.name not in shared_names:
                merged.append(runtime)
                runtime_index += 1
            elif prototype.name not in shared_names:
                merged.append(prototype)
                prototype_index += 1
            else:
                message = (
                    "Runtime and prototype defines reached incompatible shared entries: "
                    f"{runtime.name!r} and {prototype.name!r}"
                )
                raise ValueError(message)
        return tuple(merged)

    @staticmethod
    def _index(defines: list[Define], source: str) -> dict[str, Define]:
        indexed: dict[str, Define] = {}
        for define in defines:
            if define.name in indexed:
                message = f"Duplicate {source} define name: {define.name}"
                raise ValueError(message)
            indexed[define.name] = define
        return indexed


@dataclass(frozen=True, slots=True, eq=False)
class DefineRenderer:
    """Render the recursive shared define hierarchy."""

    _documentation: DocumentationRenderer

    def render(self, define: Define, page_path: Path, heading_level: int) -> list[str]:
        if heading_level > 6:
            message = f"Define hierarchy exceeds Markdown heading depth: {define.name}"
            raise ValueError(message)
        blocks = [
            MarkdownAssembler.documented_declaration(
                f"{'#' * heading_level} define `{define.name}`",
                define.description,
            )
        ]
        blocks.extend(
            [[extra] for extra in self._documentation.render_member_extras(define, page_path)]
        )
        if define.values is not None:
            blocks.extend(
                self._render_value(value, page_path, heading_level + 1) for value in define.values
            )
        if define.subkeys is not None:
            blocks.extend(
                self.render(subkey, page_path, heading_level + 1) for subkey in define.subkeys
            )
        return self._flatten_blocks(blocks)

    def _render_value(
        self,
        value: DefineValue,
        page_path: Path,
        heading_level: int,
    ) -> list[str]:
        if heading_level > 6:
            message = f"Define value exceeds Markdown heading depth: {value.name}"
            raise ValueError(message)
        blocks = [
            MarkdownAssembler.documented_declaration(
                f"{'#' * heading_level} value `{value.name}`",
                value.description,
            )
        ]
        blocks.extend(
            [[extra] for extra in self._documentation.render_member_extras(value, page_path)]
        )
        return self._flatten_blocks(blocks)

    @staticmethod
    def _flatten_blocks(blocks: list[list[str]]) -> list[str]:
        lines: list[str] = []
        for block in blocks:
            if not block:
                continue
            if lines:
                lines.append("")
            lines.extend(block)
        return lines


@dataclass(frozen=True, slots=True, eq=False)
class DefinePagePlanner:
    """Build the independent shared define page."""

    _renderer: DefineRenderer

    def plan(
        self,
        runtime_defines: list[Define],
        prototype_defines: list[Define],
    ) -> tuple[MarkdownPage, ...]:
        page_path = Path("defines.md")
        merged = DefineCollectionMerger.merge(runtime_defines, prototype_defines)
        blocks = [["# Defines"]]
        blocks.extend(self._renderer.render(define, page_path, 2) for define in merged)
        return (MarkdownPage(page_path, MarkdownAssembler.join_blocks(blocks)),)
