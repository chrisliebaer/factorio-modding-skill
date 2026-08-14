from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from factorio_docs.models.common import (
    ApiMetadata,
    Define,
    DocumentedMember,
    Image,
    LiteralValue,
    StrictModel,
    Visibility,
)


class PrototypeArrayType(StrictModel):
    complex_type: Literal["array"]
    value: PrototypeTypeExpression


class PrototypeDictionaryType(StrictModel):
    complex_type: Literal["dictionary"]
    key: PrototypeTypeExpression
    value: PrototypeTypeExpression


class PrototypeTupleType(StrictModel):
    complex_type: Literal["tuple"]
    values: list[PrototypeTypeExpression]


class PrototypeUnionType(StrictModel):
    complex_type: Literal["union"]
    options: list[PrototypeTypeExpression]
    full_format: bool


class PrototypeLiteralType(StrictModel):
    complex_type: Literal["literal"]
    value: LiteralValue
    description: str | None = None


class PrototypeDescribedType(StrictModel):
    complex_type: Literal["type"]
    value: PrototypeTypeExpression
    description: str


class PrototypeStructType(StrictModel):
    complex_type: Literal["struct"]


type PrototypeComplexType = Annotated[
    PrototypeArrayType
    | PrototypeDictionaryType
    | PrototypeTupleType
    | PrototypeUnionType
    | PrototypeLiteralType
    | PrototypeDescribedType
    | PrototypeStructType,
    Field(discriminator="complex_type"),
]
type PrototypeTypeExpression = str | PrototypeComplexType


class PrototypeProperty(DocumentedMember):
    type: PrototypeTypeExpression
    optional: bool
    override: bool
    default: str | PrototypeLiteralType | None = None
    alt_name: str | None = None
    visibility: list[Visibility] | None = None


class CustomProperties(StrictModel):
    description: str
    key_type: PrototypeTypeExpression
    value_type: PrototypeTypeExpression
    lists: list[str] | None = None
    examples: list[str] | None = None
    images: list[Image] | None = None


class Prototype(DocumentedMember):
    parent: str | None = None
    abstract: bool
    typename: str | None = None
    instance_limit: int | None = None
    deprecated: bool
    properties: list[PrototypeProperty]
    custom_properties: CustomProperties | None = None
    visibility: list[Visibility] | None = None


class PrototypeType(DocumentedMember):
    parent: str | None = None
    abstract: bool
    inline: bool
    type: PrototypeTypeExpression | Literal["builtin"]
    properties: list[PrototypeProperty] | None = None


class PrototypeApi(ApiMetadata):
    stage: Literal["prototype"]
    prototypes: list[Prototype]
    types: list[PrototypeType]
    defines: list[Define]
