from __future__ import annotations

import logging
from pathlib import Path

from pydantic import TypeAdapter

from factorio_docs.models.prototype import PrototypeApi
from factorio_docs.models.runtime import RuntimeApi


class ApiPair:
    """A matching runtime and prototype API export."""

    def __init__(self, runtime: RuntimeApi, prototype: PrototypeApi) -> None:
        if runtime.application_version != prototype.application_version:
            msg = (
                "Runtime and prototype documentation versions differ: "
                f"{runtime.application_version!r} != {prototype.application_version!r}"
            )
            raise ValueError(msg)
        if runtime.api_version != prototype.api_version:
            msg = (
                "Runtime and prototype API format versions differ: "
                f"{runtime.api_version!r} != {prototype.api_version!r}"
            )
            raise ValueError(msg)
        self.runtime = runtime
        self.prototype = prototype


class ApiLoader:
    """Read and validate Factorio API JSON exports."""

    def __init__(self) -> None:
        self._runtime_adapter = TypeAdapter(RuntimeApi)
        self._prototype_adapter = TypeAdapter(PrototypeApi)

    def load_pair(self, runtime_path: Path, prototype_path: Path) -> ApiPair:
        runtime_json = runtime_path.read_bytes()
        prototype_json = prototype_path.read_bytes()
        runtime = self._runtime_adapter.validate_json(runtime_json)
        prototype = self._prototype_adapter.validate_json(prototype_json)
        return ApiPair(runtime, prototype)


class ValidationReporter:
    """Report a successfully validated API pair."""

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def report(self, pair: ApiPair) -> None:
        runtime = pair.runtime
        prototype = pair.prototype
        self._logger.info(
            "Validated runtime API for Factorio %s using API format %d: "
            "%d classes, %d events, %d concepts, %d global objects, "
            "%d global functions, %d defines",
            runtime.application_version,
            runtime.api_version,
            len(runtime.classes),
            len(runtime.events),
            len(runtime.concepts),
            len(runtime.global_objects),
            len(runtime.global_functions),
            len(runtime.defines),
        )
        self._logger.info(
            "Validated prototype API for Factorio %s using API format %d: "
            "%d prototypes, %d types, %d defines",
            prototype.application_version,
            prototype.api_version,
            len(prototype.prototypes),
            len(prototype.types),
            len(prototype.defines),
        )
