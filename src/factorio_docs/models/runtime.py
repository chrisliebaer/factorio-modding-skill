from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from factorio_docs.models.common import (
    ApiMetadata,
    Define,
    DocumentedMember,
    LiteralValue,
    StrictModel,
    Visibility,
)


class RuntimeParameter(StrictModel):
    name: str
    order: int
    description: str
    type: RuntimeTypeExpression
    optional: bool


class RuntimeReturnValue(StrictModel):
    order: int
    description: str
    type: RuntimeTypeExpression
    optional: bool


class RuntimeGlobalObject(StrictModel):
    name: str
    order: int
    description: str
    type: RuntimeTypeExpression


class ParameterGroup(StrictModel):
    name: str
    order: int
    description: str
    parameters: list[RuntimeParameter]


class RuntimeArrayType(StrictModel):
    complex_type: Literal["array"]
    value: RuntimeTypeExpression


class RuntimeDictionaryType(StrictModel):
    complex_type: Literal["dictionary", "LuaCustomTable"]
    key: RuntimeTypeExpression
    value: RuntimeTypeExpression


class RuntimeTupleType(StrictModel):
    complex_type: Literal["tuple"]
    values: list[RuntimeTypeExpression]


class RuntimeUnionType(StrictModel):
    complex_type: Literal["union"]
    options: list[RuntimeTypeExpression]
    full_format: bool


class RuntimeLiteralType(StrictModel):
    complex_type: Literal["literal"]
    value: LiteralValue
    description: str | None = None


class RuntimeDescribedType(StrictModel):
    complex_type: Literal["type"]
    value: RuntimeTypeExpression
    description: str


class RuntimeTableType(StrictModel):
    complex_type: Literal["table"]
    parameters: list[RuntimeParameter]
    variant_parameter_groups: list[ParameterGroup] | None = None
    variant_parameter_description: str | None = None


class RuntimeFunctionType(StrictModel):
    complex_type: Literal["function"]
    parameters: list[RuntimeTypeExpression]


class RuntimeLazyLoadedValueType(StrictModel):
    complex_type: Literal["LuaLazyLoadedValue"]
    value: RuntimeTypeExpression


class RuntimeBuiltinType(StrictModel):
    complex_type: Literal["builtin"]


class RuntimeLuaStructType(StrictModel):
    complex_type: Literal["LuaStruct"]
    attributes: list[RuntimeAttribute]


type RuntimeComplexType = Annotated[
    RuntimeArrayType
    | RuntimeDictionaryType
    | RuntimeTupleType
    | RuntimeUnionType
    | RuntimeLiteralType
    | RuntimeDescribedType
    | RuntimeTableType
    | RuntimeFunctionType
    | RuntimeLazyLoadedValueType
    | RuntimeBuiltinType
    | RuntimeLuaStructType,
    Field(discriminator="complex_type"),
]
type RuntimeTypeExpression = str | RuntimeComplexType


class EventRaised(StrictModel):
    name: str
    order: int
    description: str
    timeframe: str
    optional: bool


class VariadicParameter(StrictModel):
    type: RuntimeTypeExpression | None = None
    description: str | None = None


class MethodFormat(StrictModel):
    takes_table: bool
    table_optional: bool | None = None


class RuntimeMethod(DocumentedMember):
    parameters: list[RuntimeParameter]
    format: MethodFormat
    return_values: list[RuntimeReturnValue]
    visibility: list[Visibility] | None = None
    raises: list[EventRaised] | None = None
    subclasses: list[str] | None = None
    variant_parameter_groups: list[ParameterGroup] | None = None
    variant_parameter_description: str | None = None
    variadic_parameter: VariadicParameter | None = None


class RuntimeAttribute(DocumentedMember):
    read_type: RuntimeTypeExpression | None = None
    write_type: RuntimeTypeExpression | None = None
    optional: bool
    visibility: list[Visibility] | None = None
    raises: list[EventRaised] | None = None
    subclasses: list[str] | None = None


type RuntimeOperator = RuntimeMethod | RuntimeAttribute


class RuntimeClass(DocumentedMember):
    parent: str | None = None
    abstract: bool
    methods: list[RuntimeMethod]
    attributes: list[RuntimeAttribute]
    operators: list[RuntimeOperator]
    visibility: list[Visibility] | None = None


class RuntimeEvent(DocumentedMember):
    data: list[RuntimeParameter]
    filter: str | None = None


class RuntimeConcept(DocumentedMember):
    type: RuntimeTypeExpression


class RuntimeApi(ApiMetadata):
    stage: Literal["runtime"]
    classes: list[RuntimeClass]
    events: list[RuntimeEvent]
    concepts: list[RuntimeConcept]
    defines: list[Define]
    global_objects: list[RuntimeGlobalObject]
    global_functions: list[RuntimeMethod]
