set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

default:
    @just --list

format:
    uv run ruff format src tests tools
    uv run ruff check --fix src tests tools

format-check:
    uv run ruff format --check src tests tools

lint:
    uv run ruff check src tests tools

typecheck:
    uv run basedpyright

test:
    uv run pytest

check: format-check lint typecheck test

wheel:
    rm -rf build/wheel
    uv build --wheel --out-dir build/wheel

skill: wheel
    uv run python tools/build_skill.py skill build/wheel LICENSE dist/factorio-modding

archive: skill
    uv run python tools/archive_skill.py dist/factorio-modding dist/factorio-modding.zip

build: check archive

clean:
    rm -rf build/wheel dist/factorio-modding dist/factorio-modding.zip
