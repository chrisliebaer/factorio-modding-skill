import re
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from factorio_docs.api_loader import ApiLoader
from factorio_docs.api_markdown.common import (
    DocumentationRenderer,
    MarkdownAssembler,
    TypeNameRewriter,
)
from factorio_docs.api_markdown.defines import DefineCollectionMerger
from factorio_docs.api_markdown.prototype import PrototypeApiRenderer
from factorio_docs.api_markdown.runtime import RuntimeApiRenderer, RuntimePagePlanner
from factorio_docs.api_markdown.types import TypeExpressionRenderer
from factorio_docs.image_assets import ImageAssetPublisher
from factorio_docs.models.common import Define, Image
from factorio_docs.models.prototype import (
    PrototypeArrayType,
    PrototypeLiteralType,
    PrototypeProperty,
    PrototypeStructType,
    PrototypeType,
    PrototypeUnionType,
)
from factorio_docs.models.runtime import (
    MethodFormat,
    ParameterGroup,
    RuntimeAttribute,
    RuntimeGlobalObject,
    RuntimeLuaStructType,
    RuntimeMethod,
    RuntimeParameter,
    RuntimeTableType,
)


class TestDefineCollectionMerger:
    def test_identical_shared_entities_are_emitted_once(self) -> None:
        shared = self._define("shared", 0)

        merged = DefineCollectionMerger.merge([shared], [shared])

        assert merged == (shared,)

    def test_mismatched_shared_entities_fail(self) -> None:
        runtime = self._define("shared", 0)
        prototype = self._define("shared", 1)

        with pytest.raises(ValueError, match="subtrees differ"):
            DefineCollectionMerger.merge([runtime], [prototype])

    def test_exclusive_entities_preserve_both_source_orders(self) -> None:
        runtime_only = self._define("runtime-only", 0)
        shared = self._define("shared", 1)
        prototype_only = self._define("prototype-only", 0)

        merged = DefineCollectionMerger.merge(
            [runtime_only, shared],
            [prototype_only, shared],
        )

        assert [item.name for item in merged] == [
            "runtime-only",
            "prototype-only",
            "shared",
        ]

    def test_duplicate_name_in_either_source_fails(self) -> None:
        duplicate = self._define("duplicate", 0)

        with pytest.raises(ValueError, match="Duplicate runtime"):
            DefineCollectionMerger.merge([duplicate, duplicate], [])
        with pytest.raises(ValueError, match="Duplicate prototype"):
            DefineCollectionMerger.merge([], [duplicate, duplicate])

    def test_incompatible_shared_order_fails(self) -> None:
        first = self._define("first", 0)
        second = self._define("second", 1)

        with pytest.raises(ValueError, match="incompatible shared ordering"):
            DefineCollectionMerger.merge([first, second], [second, first])

    @staticmethod
    def _define(name: str, order: int) -> Define:
        return Define(name=name, order=order, description="")


class TestDocumentationImages:
    def test_referenced_image_is_copied_into_generated_tree(self, tmp_path: Path) -> None:
        source_image, source_static_directory, output_directory = self._image_fixture(tmp_path)

        ImageAssetPublisher.publish(source_static_directory, output_directory)

        generated_image = output_directory / "static" / "images" / source_image.name

        assert generated_image.read_bytes() == source_image.read_bytes()

    def test_rendered_image_path_resolves_after_source_is_removed(
        self,
        tmp_path: Path,
    ) -> None:
        source_image, source_static_directory, output_directory = self._image_fixture(tmp_path)
        published_static_directory = ImageAssetPublisher.publish(
            source_static_directory,
            output_directory,
        )
        source_image.unlink()
        page_path = Path("prototype/types.md")
        renderer = DocumentationRenderer(published_static_directory, output_directory)
        rendered = renderer.render_extras(
            None,
            None,
            [Image(filename=source_image.name, caption="Example")],
            page_path,
        )
        link_prefix = "![Example]("
        rendered_image = rendered[0]

        assert rendered_image.startswith(link_prefix)
        assert rendered_image.endswith(")")

        relative_image = Path(rendered_image[len(link_prefix) : -1])
        resolved_image = ((output_directory / page_path).parent / relative_image).resolve()
        generated_image = (output_directory / "static" / "images" / source_image.name).resolve()

        assert resolved_image == generated_image
        assert resolved_image.is_file()

    @staticmethod
    def _image_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
        static_directory = tmp_path / "source" / "static"
        images_directory = static_directory / "images"
        images_directory.mkdir(parents=True)
        source_image = images_directory / "example.png"
        source_image.write_bytes(b"example image")
        output_directory = tmp_path / "output"
        return source_image, static_directory, output_directory


class TestRuntimeApiRenderer:
    def test_renderer_configuration_is_runtime_immutable(self, tmp_path: Path) -> None:
        aliases = {"boolean": "bool"}
        renderer = self._renderer_with_aliases(tmp_path, aliases)

        aliases["boolean"] = "changed"
        rendered = renderer.render_global_object(
            RuntimeGlobalObject(
                name="value",
                order=0,
                description="",
                type="boolean",
            )
        )

        assert "`bool`" in rendered[0]
        type_field = "_types"
        with pytest.raises(FrozenInstanceError):
            setattr(renderer, type_field, TypeExpressionRenderer())

    def test_retained_alias_mapping_rejects_direct_mutation(self) -> None:
        aliases = TypeNameRewriter.immutable({"boolean": "bool"})

        with pytest.raises(TypeError):
            exec('aliases["boolean"] = "changed"', {"aliases": aliases})

    def test_nested_render_context_is_runtime_immutable(self, tmp_path: Path) -> None:
        static_directory = tmp_path / "static"
        static_directory.mkdir()
        documentation = DocumentationRenderer(static_directory, tmp_path / "output")

        output_field = "_output_directory"
        with pytest.raises(FrozenInstanceError):
            setattr(documentation, output_field, tmp_path / "changed")
        unexpected_field = "unexpected"
        with pytest.raises((FrozenInstanceError, AttributeError)):
            setattr(TypeExpressionRenderer(), unexpected_field, True)

    def test_lua_struct_signature_retains_read_write_status(self) -> None:
        renderer = TypeExpressionRenderer()
        struct = RuntimeLuaStructType(
            complex_type="LuaStruct",
            attributes=[
                RuntimeAttribute(
                    name="value",
                    order=0,
                    description="",
                    read_type="boolean",
                    write_type="boolean",
                    optional=False,
                )
            ],
        )

        rendered = renderer.render_runtime(struct, TypeNameRewriter.production_aliases())

        assert rendered.signature == "LuaStruct{value:bool read/write}"

    def test_variant_description_without_groups_is_preserved(self) -> None:
        renderer = TypeExpressionRenderer()
        table = RuntimeTableType(
            complex_type="table",
            parameters=[],
            variant_parameter_description=(
                "Other attributes may be specified depending on `filter`:"
            ),
        )

        rendered = renderer.render_runtime(table, TypeNameRewriter.production_aliases())

        assert rendered.details == (
            "* variants - Other attributes may be specified depending on `filter`:",
        )

    def test_variant_groups_require_a_mandatory_table(self, tmp_path: Path) -> None:
        renderer = self._renderer(tmp_path)
        positional = self._variant_method(MethodFormat(takes_table=False))
        optional_table = self._variant_method(MethodFormat(takes_table=True, table_optional=True))

        with pytest.raises(ValueError, match="require one mandatory table"):
            renderer.render_method(positional, Path("runtime/classes.md"))
        with pytest.raises(ValueError, match="require one mandatory table"):
            renderer.render_method(optional_table, Path("runtime/classes.md"))

    def test_common_type_alias_rewrites_complete_structured_runtime_output(
        self,
        factorio_versions: Path,
    ) -> None:
        source_directory = factorio_versions / "2.0.77" / "files"
        pair = ApiLoader().load_pair(
            source_directory / "runtime-api.json",
            source_directory / "prototype-api.json",
        )
        aliases = TypeNameRewriter.production_aliases()
        aliases["LuaEntity"] = "ConspicuousEntityAlias"
        pages = RuntimePagePlanner(
            RuntimeApiRenderer(
                TypeExpressionRenderer(),
                DocumentationRenderer(source_directory / "static", Path("output")),
                aliases,
            )
        ).plan(pair.runtime)
        rendered = "\n".join(page.content for page in pages)
        structured_line = re.compile(
            r"^\s*(?:#{2,6} (?:class|event|concept|fn|attr|op|object)|"
            r"\* (?:filter|subclasses:|when|option)|\* `[^`]+` add)"
        )
        original_identifier = re.compile(r"(?<![A-Za-z0-9_])LuaEntity(?![A-Za-z0-9_])")

        remaining_structured = [
            line
            for line in rendered.splitlines()
            if original_identifier.search(line.partition(" - ")[0])
            and structured_line.match(line.partition(" - ")[0])
        ]

        assert "## class `ConspicuousEntityAlias`" in rendered
        assert "[LuaEntity](runtime:LuaEntity)" in rendered
        assert remaining_structured == []

    @staticmethod
    def _renderer(tmp_path: Path) -> RuntimeApiRenderer:
        return TestRuntimeApiRenderer._renderer_with_aliases(
            tmp_path,
            TypeNameRewriter.production_aliases(),
        )

    @staticmethod
    def _renderer_with_aliases(
        tmp_path: Path,
        aliases: dict[str, str],
    ) -> RuntimeApiRenderer:
        static_directory = tmp_path / "static"
        static_directory.mkdir()
        return RuntimeApiRenderer(
            TypeExpressionRenderer(),
            DocumentationRenderer(static_directory, tmp_path / "output"),
            aliases,
        )

    @staticmethod
    def _variant_method(format_: MethodFormat) -> RuntimeMethod:
        return RuntimeMethod(
            name="variant_method",
            order=0,
            description="",
            parameters=[],
            format=format_,
            return_values=[],
            variant_parameter_groups=[
                ParameterGroup(
                    name="example",
                    order=0,
                    description="",
                    parameters=[
                        RuntimeParameter(
                            name="value",
                            order=0,
                            description="",
                            type="string",
                            optional=False,
                        )
                    ],
                )
            ],
            variant_parameter_description="Other attributes may be specified depending on `type`:",
        )


class TestPrototypeApiRenderer:
    def test_signature_with_embedded_backticks_uses_double_delimiter(self) -> None:
        signature = "{color?:Color=`{r=1, g=1, b=1}`}"

        rendered = MarkdownAssembler.code(signature)

        assert rendered == "``{color?:Color=`{r=1, g=1, b=1}`}``"

    def test_adjacent_properties_apply_to_nested_struct_alternatives(self) -> None:
        renderer = TypeExpressionRenderer()
        property_ = PrototypeProperty(
            name="size",
            order=0,
            description="Size.",
            type="float",
            optional=False,
            override=False,
        )
        expression = PrototypeUnionType(
            complex_type="union",
            options=[
                PrototypeStructType(complex_type="struct"),
                PrototypeArrayType(
                    complex_type="array",
                    value=PrototypeStructType(complex_type="struct"),
                ),
            ],
            full_format=False,
        )

        rendered = renderer.render_prototype(
            expression, [property_], TypeNameRewriter.production_aliases()
        )

        assert rendered.signature == "{size:float}|{size:float}[]"
        assert rendered.details == ("* field `size` - Size.",)

    def test_struct_defaults_and_field_metadata_remain_scoped(
        self,
        tmp_path: Path,
    ) -> None:
        static_directory = tmp_path / "static"
        static_directory.mkdir()
        documentation = DocumentationRenderer(static_directory, tmp_path / "output")
        renderer = PrototypeApiRenderer(
            TypeExpressionRenderer(),
            documentation,
            TypeNameRewriter.production_aliases(),
        )
        type_ = PrototypeType(
            name="ColorLike",
            order=0,
            description="",
            abstract=False,
            inline=False,
            type=PrototypeStructType(complex_type="struct"),
            properties=[
                PrototypeProperty(
                    name="alpha",
                    order=0,
                    description="Opacity.",
                    type="boolean",
                    optional=True,
                    override=True,
                    default=PrototypeLiteralType(complex_type="literal", value=True),
                )
            ],
        )

        rendered = "\n".join(renderer.render_type(type_, Path("prototype/types.md")))

        assert "## type `ColorLike` `{alpha?:bool=true}`" in rendered
        assert "* field `alpha` - Opacity." in rendered
        assert "  * meta: override" in rendered
