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
from factorio_docs.models.runtime import (
    EventRaised,
    RuntimeApi,
    RuntimeAttribute,
    RuntimeClass,
    RuntimeConcept,
    RuntimeEvent,
    RuntimeGlobalObject,
    RuntimeMethod,
    RuntimeOperator,
    RuntimeParameter,
    RuntimeReturnValue,
)


@dataclass(frozen=True, slots=True, eq=False)
class RuntimeApiRenderer:
    """Render runtime API entities without deciding their output files."""

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

    def render_index(self, api: RuntimeApi) -> list[str]:
        return [
            "# Runtime API",
            "",
            f"* application: `{api.application}`",
            f"* application_version: `{api.application_version}`",
            f"* api_version: `{api.api_version}`",
            f"* stage: `{api.stage}`",
        ]

    def render_class(self, class_: RuntimeClass, page_path: Path) -> list[str]:
        name = TypeNameRewriter.rewrite(class_.name, self._aliases)
        parent = (
            f" < `{TypeNameRewriter.rewrite(class_.parent, self._aliases)}`"
            if class_.parent is not None
            else ""
        )
        blocks = [
            MarkdownAssembler.documented_declaration(
                f"## class `{name}`{parent}",
                class_.description,
            )
        ]
        metadata = self._metadata(class_.abstract, class_.visibility)
        if metadata:
            blocks.append([MetadataRenderer.line(metadata, "")])
        blocks.extend(
            [[extra] for extra in self._documentation.render_member_extras(class_, page_path)]
        )
        blocks.extend(self.render_method(method, page_path) for method in class_.methods)
        blocks.extend(
            self.render_attribute(attribute, page_path) for attribute in class_.attributes
        )
        blocks.extend(self.render_operator(operator, page_path) for operator in class_.operators)
        return self._flatten_blocks(blocks)

    def render_event(self, event: RuntimeEvent, page_path: Path) -> list[str]:
        signature = self._types.render_parameters_signature(event.data, self._aliases)
        blocks = [
            MarkdownAssembler.documented_declaration(
                f"## event `{event.name}` {MarkdownAssembler.code(f'{{{signature}}}')}",
                event.description,
            )
        ]
        if event.filter is not None:
            blocks.append([f"* filter `{TypeNameRewriter.rewrite(event.filter, self._aliases)}`"])
        blocks.append(self._render_parameter_details(event.data, "field"))
        blocks.extend(
            [[extra] for extra in self._documentation.render_member_extras(event, page_path)]
        )
        return self._flatten_blocks(blocks)

    def render_concept(self, concept: RuntimeConcept, page_path: Path) -> list[str]:
        rendered = self._types.render_runtime(concept.type, self._aliases)
        name = TypeNameRewriter.rewrite(concept.name, self._aliases)
        blocks = [
            MarkdownAssembler.documented_declaration(
                f"## concept `{name}` {MarkdownAssembler.code(rendered.signature)}",
                concept.description,
            ),
            list(rendered.details),
        ]
        blocks.extend(
            [[extra] for extra in self._documentation.render_member_extras(concept, page_path)]
        )
        return self._flatten_blocks(blocks)

    def render_global_object(
        self,
        global_object: RuntimeGlobalObject,
    ) -> list[str]:
        rendered = self._types.render_runtime(global_object.type, self._aliases)
        return self._flatten_blocks(
            [
                MarkdownAssembler.documented_declaration(
                    f"## object `{global_object.name}` "
                    f"{MarkdownAssembler.code(rendered.signature)}",
                    global_object.description,
                ),
                list(rendered.details),
            ]
        )

    def render_method(self, method: RuntimeMethod, page_path: Path) -> list[str]:
        return self._render_callable(method, "### fn", page_path)

    def render_attribute(
        self,
        attribute: RuntimeAttribute,
        page_path: Path,
    ) -> list[str]:
        signature, type_details = self._attribute_signature(attribute)
        optional = " optional" if attribute.optional else ""
        blocks = [
            MarkdownAssembler.documented_declaration(
                f"### attr `{attribute.name}` {MarkdownAssembler.code(signature)}{optional}",
                attribute.description,
            ),
            list(type_details),
        ]
        metadata = self._visibility_metadata(attribute.visibility)
        if metadata:
            blocks.append([MetadataRenderer.line(metadata, "")])
        blocks.extend(self._render_raises(attribute.raises))
        if attribute.subclasses is not None:
            blocks.append([self._render_subclasses(attribute.subclasses)])
        blocks.extend(
            [[extra] for extra in self._documentation.render_member_extras(attribute, page_path)]
        )
        return self._flatten_blocks(blocks)

    def render_operator(
        self,
        operator: RuntimeOperator,
        page_path: Path,
    ) -> list[str]:
        if isinstance(operator, RuntimeMethod):
            return self._render_callable(operator, "### op", page_path)
        signature, type_details = self._attribute_signature(operator)
        optional = " optional" if operator.optional else ""
        blocks = [
            MarkdownAssembler.documented_declaration(
                f"### op `{operator.name}` {MarkdownAssembler.code(signature)}{optional}",
                operator.description,
            ),
            list(type_details),
        ]
        blocks.extend(
            [[extra] for extra in self._documentation.render_member_extras(operator, page_path)]
        )
        return self._flatten_blocks(blocks)

    def _render_callable(
        self,
        method: RuntimeMethod,
        declaration_prefix: str,
        page_path: Path,
    ) -> list[str]:
        signature = self._method_signature(method)
        blocks = [
            MarkdownAssembler.documented_declaration(
                f"{declaration_prefix} `{method.name}` {MarkdownAssembler.code(signature)}",
                method.description,
            )
        ]
        metadata = self._visibility_metadata(method.visibility)
        if metadata:
            blocks.append([MetadataRenderer.line(metadata, "")])
        if method.subclasses is not None:
            blocks.append([self._render_subclasses(method.subclasses)])
        blocks.append(self._render_parameter_details(method.parameters, "arg"))
        if method.variadic_parameter is not None and method.variadic_parameter.description:
            blocks.append(
                MarkdownAssembler.detail("arg `...`", method.variadic_parameter.description, "")
            )
        blocks.append(self._render_return_details(method.return_values))
        blocks.extend(self._render_raises(method.raises))
        if method.variant_parameter_groups is not None:
            if not method.format.takes_table or method.format.table_optional is not False:
                message = f"Runtime method variants require one mandatory table: {method.name}"
                raise ValueError(message)
            if method.variant_parameter_description is None:
                message = f"Runtime method variants have no description: {method.name}"
                raise ValueError(message)
            blocks.append(
                self._types.render_variant_groups(
                    method.variant_parameter_groups,
                    method.variant_parameter_description,
                    self._aliases,
                )
            )
        elif method.variant_parameter_description is not None:
            message = f"Runtime method has a variant description without groups: {method.name}"
            raise ValueError(message)
        blocks.extend(
            [[extra] for extra in self._documentation.render_member_extras(method, page_path)]
        )
        return self._flatten_blocks(blocks)

    def _method_signature(self, method: RuntimeMethod) -> str:
        parameter_signature = self._types.render_parameters_signature(
            method.parameters, self._aliases
        )
        if method.variadic_parameter is not None:
            variadic = "..."
            if method.variadic_parameter.type is not None:
                variadic_type = self._types.render_runtime(
                    method.variadic_parameter.type, self._aliases
                )
                if variadic_type.details:
                    message = f"Variadic parameter type has nested details: {method.name}"
                    raise ValueError(message)
                variadic = f"...:{variadic_type.signature}"
            parameter_signature = ",".join(part for part in (parameter_signature, variadic) if part)
        if method.format.takes_table:
            if method.format.table_optional is None:
                message = f"Table-taking method has no table optionality: {method.name}"
                raise ValueError(message)
            arguments = f"{{{parameter_signature}}}"
            if method.format.table_optional:
                arguments += "?"
        else:
            if method.format.table_optional is not None:
                message = f"Positional method declares table optionality: {method.name}"
                raise ValueError(message)
            arguments = f"({parameter_signature})"
        returns = self._return_signature(method.return_values)
        return f"{arguments} -> {returns}" if returns else arguments

    def _return_signature(self, values: list[RuntimeReturnValue]) -> str:
        rendered = [self._types.render_runtime(value.type, self._aliases) for value in values]
        signatures = [
            f"{item.signature}{'?' if value.optional else ''}"
            for value, item in zip(values, rendered, strict=True)
        ]
        if not signatures:
            return ""
        if len(signatures) == 1:
            return signatures[0]
        return f"({','.join(signatures)})"

    def _render_parameter_details(
        self,
        parameters: list[RuntimeParameter],
        label: str,
    ) -> list[str]:
        return self._types.render_parameter_details(parameters, label, "", self._aliases)

    def _render_return_details(self, values: list[RuntimeReturnValue]) -> list[str]:
        lines: list[str] = []
        multiple = len(values) > 1
        for index, value in enumerate(values, start=1):
            prefix = f"return `{index}`" if multiple else "return"
            if value.description:
                lines.extend(MarkdownAssembler.detail(prefix, value.description, ""))
            rendered = self._types.render_runtime(value.type, self._aliases)
            lines.extend(rendered.details)
        return lines

    def _attribute_signature(
        self,
        attribute: RuntimeAttribute,
    ) -> tuple[str, tuple[str, ...]]:
        if attribute.read_type is None and attribute.write_type is None:
            message = f"Runtime attribute has neither read nor write type: {attribute.name}"
            raise ValueError(message)
        read = (
            self._types.render_runtime(attribute.read_type, self._aliases)
            if attribute.read_type is not None
            else None
        )
        write = (
            self._types.render_runtime(attribute.write_type, self._aliases)
            if attribute.write_type is not None
            else None
        )
        details = tuple(
            detail
            for rendered in (read, write)
            if rendered is not None
            for detail in rendered.details
        )
        if read is not None and write is not None:
            if read.signature == write.signature:
                return f"{read.signature} read/write", details
            return f"{read.signature} <- {write.signature}", details
        if read is not None:
            return f"{read.signature} read", details
        if write is None:
            message = f"Runtime attribute has no write type: {attribute.name}"
            raise ValueError(message)
        return f"{write.signature} write", details

    @staticmethod
    def _render_raises(raises: list[EventRaised] | None) -> list[list[str]]:
        if raises is None:
            return []
        blocks: list[list[str]] = []
        for raised in raises:
            optional = " optional" if raised.optional else ""
            blocks.append(
                MarkdownAssembler.detail(
                    f"raises `{raised.name}` `{raised.timeframe}`{optional}",
                    raised.description,
                    "",
                )
            )
        return blocks

    def _render_subclasses(self, subclasses: list[str]) -> str:
        rewritten = (TypeNameRewriter.rewrite(subclass, self._aliases) for subclass in subclasses)
        values = ", ".join(f"`{subclass}`" for subclass in sorted(rewritten))
        return f"* subclasses: {values}"

    @classmethod
    def _metadata(
        cls,
        abstract: bool,
        visibility: list[Visibility] | None,
    ) -> list[str]:
        metadata = MetadataRenderer.visibility_items(visibility)
        if abstract:
            metadata.append("abstract")
        return sorted(metadata, key=str.casefold)

    @staticmethod
    def _visibility_metadata(visibility: list[Visibility] | None) -> list[str]:
        return MetadataRenderer.visibility_items(visibility)

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
class RuntimePagePlanner:
    """Assign rendered runtime entities to official top-level category pages."""

    _renderer: RuntimeApiRenderer

    def plan(self, api: RuntimeApi) -> tuple[MarkdownPage, ...]:
        category_specs = (
            (
                Path("runtime/classes.md"),
                "# Runtime classes",
                [
                    self._renderer.render_class(value, Path("runtime/classes.md"))
                    for value in api.classes
                ],
            ),
            (
                Path("runtime/events.md"),
                "# Runtime events",
                [
                    self._renderer.render_event(value, Path("runtime/events.md"))
                    for value in api.events
                ],
            ),
            (
                Path("runtime/concepts.md"),
                "# Runtime concepts",
                [
                    self._renderer.render_concept(value, Path("runtime/concepts.md"))
                    for value in api.concepts
                ],
            ),
            (
                Path("runtime/global-objects.md"),
                "# Runtime global objects",
                [self._renderer.render_global_object(value) for value in api.global_objects],
            ),
            (
                Path("runtime/global-functions.md"),
                "# Runtime global functions",
                [
                    self._renderer.render_method(value, Path("runtime/global-functions.md"))
                    for value in api.global_functions
                ],
            ),
        )
        pages = [
            MarkdownPage(
                Path("runtime/index.md"), "\n".join(self._renderer.render_index(api)) + "\n"
            )
        ]
        pages.extend(
            MarkdownPage(path, MarkdownAssembler.join_blocks([[title], *entities]))
            for path, title, entities in category_specs
        )
        return tuple(pages)
