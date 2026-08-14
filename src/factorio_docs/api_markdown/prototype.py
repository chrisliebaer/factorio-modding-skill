from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from factorio_docs.api_markdown.common import (
    DocumentationRenderer,
    MarkdownAssembler,
    MarkdownPage,
    MetadataRenderer,
    TypeNameRewriter,
)
from factorio_docs.api_markdown.types import TypeExpressionRenderer
from factorio_docs.models.common import Visibility
from factorio_docs.models.prototype import (
    CustomProperties,
    Prototype,
    PrototypeApi,
    PrototypeProperty,
    PrototypeType,
)


@dataclass(frozen=True, slots=True, eq=False)
class PrototypeApiRenderer:
    """Render prototype API entities without deciding their output files."""

    _types: TypeExpressionRenderer
    _documentation: DocumentationRenderer
    _aliases: Mapping[str, str]

    def __init__(
        self,
        types: TypeExpressionRenderer,
        documentation: DocumentationRenderer,
        aliases: Mapping[str, str],
    ) -> None:
        object.__setattr__(self, "_types", types)
        object.__setattr__(self, "_documentation", documentation)
        object.__setattr__(self, "_aliases", TypeNameRewriter.immutable(aliases))

    def render_index(self, api: PrototypeApi) -> list[str]:
        return [
            "# Prototype API",
            "",
            f"* application: `{api.application}`",
            f"* application_version: `{api.application_version}`",
            f"* api_version: `{api.api_version}`",
            f"* stage: `{api.stage}`",
        ]

    def render_prototype(self, prototype: Prototype, page_path: Path) -> list[str]:
        typename = (
            f" `{self._literal(prototype.typename)}`" if prototype.typename is not None else ""
        )
        name = TypeNameRewriter.rewrite(prototype.name, self._aliases)
        parent = (
            f" < `{TypeNameRewriter.rewrite(prototype.parent, self._aliases)}`"
            if prototype.parent is not None
            else ""
        )
        blocks = [
            MarkdownAssembler.documented_declaration(
                f"## prototype `{name}`{typename}{parent}",
                prototype.description,
            )
        ]
        metadata = self._entity_metadata(
            prototype.abstract,
            prototype.deprecated,
            prototype.instance_limit,
            prototype.visibility,
            False,
        )
        if metadata:
            blocks.append([MetadataRenderer.line(metadata, "")])
        blocks.extend(
            [[extra] for extra in self._documentation.render_member_extras(prototype, page_path)]
        )
        blocks.extend(
            self.render_property(property_, page_path) for property_ in prototype.properties
        )
        if prototype.custom_properties is not None:
            blocks.append(self.render_custom_properties(prototype.custom_properties, page_path))
        return self._flatten_blocks(blocks)

    def render_type(self, type_: PrototypeType, page_path: Path) -> list[str]:
        if type_.type == "builtin":
            signature = "builtin"
            type_details: tuple[str, ...] = ()
        else:
            rendered = self._types.render_prototype(type_.type, type_.properties, self._aliases)
            signature = rendered.signature
            type_details = rendered.details
        name = TypeNameRewriter.rewrite(type_.name, self._aliases)
        parent = (
            f" < `{TypeNameRewriter.rewrite(type_.parent, self._aliases)}`"
            if type_.parent is not None
            else ""
        )
        blocks = [
            MarkdownAssembler.documented_declaration(
                f"## type `{name}` {MarkdownAssembler.code(signature)}{parent}",
                type_.description,
            )
        ]
        metadata = self._entity_metadata(
            type_.abstract,
            False,
            None,
            None,
            type_.inline,
        )
        if metadata:
            blocks.append([MetadataRenderer.line(metadata, "")])
        blocks.append(list(type_details))
        blocks.extend(
            [[extra] for extra in self._documentation.render_member_extras(type_, page_path)]
        )
        return self._flatten_blocks(blocks)

    def render_property(
        self,
        property_: PrototypeProperty,
        page_path: Path,
    ) -> list[str]:
        rendered = self._types.render_prototype(property_.type, None, self._aliases)
        optionality = "optional" if property_.optional else "required"
        default = (
            f"={self._types.render_prototype_default(property_.default)}"
            if property_.default is not None
            else ""
        )
        blocks = [
            MarkdownAssembler.documented_declaration(
                f"### prop `{property_.name}` "
                f"{MarkdownAssembler.code(rendered.signature + default)} {optionality}",
                property_.description,
            ),
            list(rendered.details),
        ]
        metadata = self._property_metadata(property_)
        if metadata:
            blocks.append([MetadataRenderer.line(metadata, "")])
        blocks.extend(
            [[extra] for extra in self._documentation.render_member_extras(property_, page_path)]
        )
        return self._flatten_blocks(blocks)

    def render_custom_properties(
        self,
        custom: CustomProperties,
        page_path: Path,
    ) -> list[str]:
        key = self._types.render_prototype(custom.key_type, None, self._aliases)
        value = self._types.render_prototype(custom.value_type, None, self._aliases)
        blocks = [
            MarkdownAssembler.documented_declaration(
                f"### custom {MarkdownAssembler.code(f'{{{key.signature}:{value.signature}}}')}",
                custom.description,
            ),
            list(key.details + value.details),
        ]
        blocks.extend(
            [
                [extra]
                for extra in self._documentation.render_extras(
                    custom.lists,
                    custom.examples,
                    custom.images,
                    page_path,
                )
            ]
        )
        return self._flatten_blocks(blocks)

    @staticmethod
    def _entity_metadata(
        abstract: bool,
        deprecated: bool,
        instance_limit: int | None,
        visibility: list[Visibility] | None,
        inline: bool,
    ) -> list[str]:
        metadata: list[str] = []
        if abstract:
            metadata.append("abstract")
        if deprecated:
            metadata.append("deprecated")
        if inline:
            metadata.append("inline")
        if instance_limit is not None:
            metadata.append(f"limit=`{instance_limit}`")
        metadata.extend(MetadataRenderer.visibility_items(visibility))
        return sorted(metadata, key=str.casefold)

    @staticmethod
    def _property_metadata(property_: PrototypeProperty) -> list[str]:
        return MetadataRenderer.property_items(
            property_.alt_name,
            property_.override,
            property_.visibility,
        )

    @staticmethod
    def _literal(value: str) -> str:
        return TypeExpressionRenderer.render_literal(value)

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
class PrototypePagePlanner:
    """Assign rendered prototype entities to official top-level category pages."""

    _renderer: PrototypeApiRenderer

    def plan(self, api: PrototypeApi) -> tuple[MarkdownPage, ...]:
        prototype_path = Path("prototype/prototypes.md")
        type_path = Path("prototype/types.md")
        return (
            MarkdownPage(
                Path("prototype/index.md"),
                "\n".join(self._renderer.render_index(api)) + "\n",
            ),
            MarkdownPage(
                prototype_path,
                MarkdownAssembler.join_blocks(
                    [
                        ["# Prototypes"],
                        *[
                            self._renderer.render_prototype(value, prototype_path)
                            for value in api.prototypes
                        ],
                    ]
                ),
            ),
            MarkdownPage(
                type_path,
                MarkdownAssembler.join_blocks(
                    [
                        ["# Prototype types"],
                        *[self._renderer.render_type(value, type_path) for value in api.types],
                    ]
                ),
            ),
        )
