from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Base model for immutable, non-coercing documentation input."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Image(StrictModel):
    filename: str
    caption: str | None = None


class DocumentedMember(StrictModel):
    name: str
    order: int
    description: str
    lists: list[str] | None = None
    examples: list[str] | None = None
    images: list[Image] | None = None


class DefineValue(DocumentedMember):
    pass


class Define(DocumentedMember):
    values: list[DefineValue] | None = None
    subkeys: list[Define] | None = None


class ApiMetadata(StrictModel):
    application: Literal["factorio"]
    application_version: str
    api_version: int


type Visibility = Literal["space_age"]
type LiteralValue = str | bool | int | float
