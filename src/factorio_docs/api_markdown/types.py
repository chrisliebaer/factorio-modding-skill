from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass

from factorio_docs.api_markdown.common import (
    MarkdownAssembler,
    MetadataRenderer,
    TypeNameRewriter,
)
from factorio_docs.models.common import LiteralValue
from factorio_docs.models.prototype import (
    PrototypeArrayType,
    PrototypeDescribedType,
    PrototypeDictionaryType,
    PrototypeLiteralType,
    PrototypeProperty,
    PrototypeTupleType,
    PrototypeTypeExpression,
    PrototypeUnionType,
)
from factorio_docs.models.runtime import (
    ParameterGroup,
    RuntimeArrayType,
    RuntimeBuiltinType,
    RuntimeDescribedType,
    RuntimeDictionaryType,
    RuntimeFunctionType,
    RuntimeLazyLoadedValueType,
    RuntimeLiteralType,
    RuntimeLuaStructType,
    RuntimeParameter,
    RuntimeTableType,
    RuntimeTupleType,
    RuntimeTypeExpression,
    RuntimeUnionType,
)


@dataclass(frozen=True, slots=True)
class RenderedType:
    signature: str
    details: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class TypeExpressionRenderer:
    """Exhaustively render the recursive runtime and prototype type languages."""

    _discriminator_description = re.compile(
        r"^Other attributes may be specified depending on `(?P<field>[^`]+)`:$"
    )
    _entity_type_description = "Other attributes may be specified depending on the type of entity:"
    _alternative_shapes_description = (
        "These attributes provide different methods of specifying the unit's spawn location:"
    )

    def render_runtime(
        self, expression: RuntimeTypeExpression, aliases: Mapping[str, str]
    ) -> RenderedType:
        if isinstance(expression, str):
            return RenderedType(TypeNameRewriter.rewrite(expression, aliases))
        if isinstance(expression, RuntimeArrayType):
            value = self.render_runtime(expression.value, aliases)
            return RenderedType(f"{value.signature}[]", value.details)
        if isinstance(expression, RuntimeDictionaryType):
            key = self.render_runtime(expression.key, aliases)
            value = self.render_runtime(expression.value, aliases)
            wrapper = "LuaCustomTable" if expression.complex_type == "LuaCustomTable" else ""
            signature = (
                f"{wrapper}<{key.signature},{value.signature}>"
                if wrapper
                else f"{{{key.signature}:{value.signature}}}"
            )
            return RenderedType(signature, key.details + value.details)
        if isinstance(expression, RuntimeTupleType):
            values = tuple(self.render_runtime(value, aliases) for value in expression.values)
            return RenderedType(
                f"({','.join(value.signature for value in values)})",
                tuple(detail for value in values for detail in value.details),
            )
        if isinstance(expression, RuntimeUnionType):
            return self._render_runtime_union(expression, aliases)
        if isinstance(expression, RuntimeLiteralType):
            return RenderedType(self.render_literal(expression.value))
        if isinstance(expression, RuntimeDescribedType):
            rendered = self.render_runtime(expression.value, aliases)
            if rendered.details:
                message = "A described runtime type contains nested details"
                raise ValueError(message)
            return rendered
        if isinstance(expression, RuntimeTableType):
            return self._render_runtime_table(expression, aliases)
        if isinstance(expression, RuntimeFunctionType):
            parameters = tuple(
                self.render_runtime(value, aliases) for value in expression.parameters
            )
            return RenderedType(
                f"function({','.join(value.signature for value in parameters)})",
                tuple(detail for value in parameters for detail in value.details),
            )
        if isinstance(expression, RuntimeLazyLoadedValueType):
            value = self.render_runtime(expression.value, aliases)
            return RenderedType(f"LuaLazyLoadedValue<{value.signature}>", value.details)
        if isinstance(expression, RuntimeBuiltinType):
            return RenderedType("builtin")
        return self._render_lua_struct(expression, aliases)

    def render_prototype(
        self,
        expression: PrototypeTypeExpression,
        properties: list[PrototypeProperty] | None,
        aliases: Mapping[str, str],
    ) -> RenderedType:
        if isinstance(expression, str):
            return RenderedType(TypeNameRewriter.rewrite(expression, aliases))
        if isinstance(expression, PrototypeArrayType):
            value = self.render_prototype(expression.value, properties, aliases)
            return RenderedType(f"{value.signature}[]", value.details)
        if isinstance(expression, PrototypeDictionaryType):
            key = self.render_prototype(expression.key, properties, aliases)
            value = self.render_prototype(expression.value, properties, aliases)
            return RenderedType(
                f"{{{key.signature}:{value.signature}}}",
                key.details + value.details,
            )
        if isinstance(expression, PrototypeTupleType):
            values = tuple(
                self.render_prototype(value, properties, aliases) for value in expression.values
            )
            return RenderedType(
                f"({','.join(value.signature for value in values)})",
                tuple(detail for value in values for detail in value.details),
            )
        if isinstance(expression, PrototypeUnionType):
            return self._render_prototype_union(expression, properties, aliases)
        if isinstance(expression, PrototypeLiteralType):
            return RenderedType(self.render_literal(expression.value))
        if isinstance(expression, PrototypeDescribedType):
            rendered = self.render_prototype(expression.value, properties, aliases)
            if rendered.details:
                message = "A described prototype type contains nested details"
                raise ValueError(message)
            return rendered
        if properties is None:
            message = "A prototype struct has no adjacent properties"
            raise ValueError(message)
        return self._render_prototype_struct(properties, aliases)

    def render_prototype_default(
        self,
        default: str | PrototypeLiteralType,
    ) -> str:
        if isinstance(default, str):
            return default
        return self.render_literal(default.value)

    def render_parameters_signature(
        self, parameters: list[RuntimeParameter], aliases: Mapping[str, str]
    ) -> str:
        return ",".join(
            self._render_runtime_parameter(parameter, aliases) for parameter in parameters
        )

    def render_parameter_details(
        self,
        parameters: list[RuntimeParameter],
        label: str,
        indentation: str,
        aliases: Mapping[str, str],
    ) -> list[str]:
        lines: list[str] = []
        for parameter in parameters:
            if parameter.description:
                lines.extend(
                    MarkdownAssembler.detail(
                        f"{label} `{parameter.name}`",
                        parameter.description,
                        indentation,
                    )
                )
            rendered_type = self.render_runtime(parameter.type, aliases)
            lines.extend(f"{indentation}{detail}" for detail in rendered_type.details)
        return lines

    def render_variant_groups(
        self,
        groups: list[ParameterGroup],
        description: str,
        aliases: Mapping[str, str],
    ) -> list[str]:
        match = self._discriminator_description.fullmatch(description)
        if match is not None:
            return self._render_discriminator_groups(groups, match.group("field"), aliases)
        if description == self._entity_type_description:
            return self._render_contextual_groups(groups, description, aliases)
        if description == self._alternative_shapes_description:
            return self._render_alternative_groups(groups, description, aliases)
        message = f"Unknown runtime parameter-group relationship: {description!r}"
        raise ValueError(message)

    def _render_runtime_union(
        self, expression: RuntimeUnionType, aliases: Mapping[str, str]
    ) -> RenderedType:
        options = tuple(self.render_runtime(option, aliases) for option in expression.options)
        details = list(dict.fromkeys(detail for option in options for detail in option.details))
        for source, rendered in zip(expression.options, options, strict=True):
            description = self._runtime_option_description(source)
            if description:
                details.extend(
                    MarkdownAssembler.detail(f"option `{rendered.signature}`", description, "")
                )
        return RenderedType(
            "|".join(option.signature for option in options),
            tuple(details),
        )

    def _render_prototype_union(
        self,
        expression: PrototypeUnionType,
        properties: list[PrototypeProperty] | None,
        aliases: Mapping[str, str],
    ) -> RenderedType:
        options = tuple(
            self.render_prototype(option, properties, aliases) for option in expression.options
        )
        details = list(dict.fromkeys(detail for option in options for detail in option.details))
        for source, rendered in zip(expression.options, options, strict=True):
            description = self._prototype_option_description(source)
            if description:
                details.extend(
                    MarkdownAssembler.detail(f"option `{rendered.signature}`", description, "")
                )
        return RenderedType(
            "|".join(option.signature for option in options),
            tuple(details),
        )

    def _render_runtime_table(
        self, expression: RuntimeTableType, aliases: Mapping[str, str]
    ) -> RenderedType:
        signature = f"{{{self.render_parameters_signature(expression.parameters, aliases)}}}"
        details = self.render_parameter_details(expression.parameters, "field", "", aliases)
        if expression.variant_parameter_groups is not None:
            if expression.variant_parameter_description is None:
                message = "Runtime table variants have no relationship description"
                raise ValueError(message)
            details.extend(
                self.render_variant_groups(
                    expression.variant_parameter_groups,
                    expression.variant_parameter_description,
                    aliases,
                )
            )
        elif expression.variant_parameter_description is not None:
            details.extend(
                MarkdownAssembler.detail(
                    "variants",
                    expression.variant_parameter_description,
                    "",
                )
            )
        return RenderedType(signature, tuple(details))

    def _render_lua_struct(
        self, expression: RuntimeLuaStructType, aliases: Mapping[str, str]
    ) -> RenderedType:
        fields = ",".join(
            self._render_runtime_attribute_signature(
                attribute.name,
                attribute.optional,
                attribute.read_type,
                attribute.write_type,
                aliases,
            )
            for attribute in expression.attributes
        )
        details: list[str] = []
        for attribute in expression.attributes:
            if attribute.description:
                details.extend(
                    MarkdownAssembler.detail(f"attr `{attribute.name}`", attribute.description, "")
                )
        return RenderedType(f"LuaStruct{{{fields}}}", tuple(details))

    def _render_prototype_struct(
        self,
        properties: list[PrototypeProperty],
        aliases: Mapping[str, str],
    ) -> RenderedType:
        signatures: list[str] = []
        details: list[str] = []
        for property_ in properties:
            rendered = self.render_prototype(property_.type, None, aliases)
            optional = "?" if property_.optional else ""
            default = (
                f"={self.render_prototype_default(property_.default)}"
                if property_.default is not None
                else ""
            )
            signatures.append(f"{property_.name}{optional}:{rendered.signature}{default}")
            metadata = MetadataRenderer.property_items(
                property_.alt_name,
                property_.override,
                property_.visibility,
            )
            if property_.description or metadata or rendered.details:
                details.extend(
                    MarkdownAssembler.detail(f"field `{property_.name}`", property_.description, "")
                )
                details.extend(f"  {detail}" for detail in rendered.details)
                if metadata:
                    details.append(MetadataRenderer.line(metadata, "  "))
        return RenderedType(f"{{{','.join(signatures)}}}", tuple(details))

    def _render_discriminator_groups(
        self,
        groups: list[ParameterGroup],
        field: str,
        aliases: Mapping[str, str],
    ) -> list[str]:
        lines: list[str] = []
        for group in groups:
            signature = self.render_parameters_signature(group.parameters, aliases)
            prefix = f"when `{field}={self.render_literal(group.name)}` add `{{{signature}}}`"
            lines.extend(MarkdownAssembler.detail(prefix, group.description, ""))
            lines.extend(self.render_parameter_details(group.parameters, "arg", "  ", aliases))
        return lines

    def _render_contextual_groups(
        self,
        groups: list[ParameterGroup],
        description: str,
        aliases: Mapping[str, str],
    ) -> list[str]:
        lines = MarkdownAssembler.detail("by entity type", description, "")
        for group in groups:
            signature = self.render_parameters_signature(group.parameters, aliases)
            lines.extend(
                MarkdownAssembler.detail(
                    f"`{group.name}` add `{{{signature}}}`",
                    group.description,
                    "  ",
                )
            )
            lines.extend(self.render_parameter_details(group.parameters, "arg", "    ", aliases))
        return lines

    def _render_alternative_groups(
        self,
        groups: list[ParameterGroup],
        description: str,
        aliases: Mapping[str, str],
    ) -> list[str]:
        lines = MarkdownAssembler.detail("one of", description, "")
        for group in groups:
            signature = self.render_parameters_signature(group.parameters, aliases)
            lines.extend(
                MarkdownAssembler.detail(
                    f"`{group.name}` `{{{signature}}}`",
                    group.description,
                    "  ",
                )
            )
            lines.extend(self.render_parameter_details(group.parameters, "arg", "    ", aliases))
        return lines

    def _render_runtime_parameter(
        self, parameter: RuntimeParameter, aliases: Mapping[str, str]
    ) -> str:
        rendered = self.render_runtime(parameter.type, aliases)
        optional = "?" if parameter.optional else ""
        return f"{parameter.name}{optional}:{rendered.signature}"

    def _render_runtime_attribute_signature(
        self,
        name: str,
        optional: bool,
        read_type: RuntimeTypeExpression | None,
        write_type: RuntimeTypeExpression | None,
        aliases: Mapping[str, str],
    ) -> str:
        if read_type is None and write_type is None:
            message = f"Runtime attribute has neither read nor write type: {name}"
            raise ValueError(message)
        optional_marker = "?" if optional else ""
        if read_type is not None and write_type is not None:
            read = self.render_runtime(read_type, aliases).signature
            write = self.render_runtime(write_type, aliases).signature
            type_signature = f"{read} read/write" if read == write else f"{read}<-{write}"
        elif read_type is not None:
            type_signature = f"{self.render_runtime(read_type, aliases).signature} read"
        else:
            if write_type is None:
                message = f"Runtime attribute has no write type: {name}"
                raise ValueError(message)
            type_signature = f"{self.render_runtime(write_type, aliases).signature} write"
        return f"{name}{optional_marker}:{type_signature}"

    @staticmethod
    def _runtime_option_description(expression: RuntimeTypeExpression) -> str | None:
        if isinstance(expression, RuntimeDescribedType | RuntimeLiteralType):
            return expression.description
        return None

    @staticmethod
    def _prototype_option_description(expression: PrototypeTypeExpression) -> str | None:
        if isinstance(expression, PrototypeDescribedType | PrototypeLiteralType):
            return expression.description
        return None

    @staticmethod
    def render_literal(value: LiteralValue) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
