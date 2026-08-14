from __future__ import annotations

import argparse
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class SkillDistributionBuilder:
    """Assemble a distributable skill directory from its sources and wheel."""

    source_directory: Path
    wheel_directory: Path
    license_file: Path
    output_directory: Path

    _wheel_marker: ClassVar[str] = "{{WHEEL_FILENAME}}"

    def build(self) -> None:
        source_directory = self.source_directory.resolve(strict=True)
        if not source_directory.is_dir():
            message = f"Skill source is not a directory: {source_directory}"
            raise NotADirectoryError(message)

        wheel_directory = self.wheel_directory.resolve(strict=True)
        if not wheel_directory.is_dir():
            message = f"Wheel source is not a directory: {wheel_directory}"
            raise NotADirectoryError(message)
        wheels = tuple(wheel_directory.glob("*.whl"))
        if len(wheels) != 1:
            message = f"Expected exactly one wheel in {wheel_directory}, found {len(wheels)}"
            raise ValueError(message)
        wheel = wheels[0]

        license_file = self.license_file.resolve(strict=True)
        if not license_file.is_file():
            message = f"Skill license source is not a file: {license_file}"
            raise FileNotFoundError(message)

        source_skill = source_directory / "SKILL.md"
        template = source_skill.read_text(encoding="utf-8")
        if template.count(self._wheel_marker) != 1:
            message = (
                f"Expected exactly one wheel marker in {source_skill}, "
                f"found {template.count(self._wheel_marker)}"
            )
            raise ValueError(message)

        output_parent = self.output_directory.parent
        output_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=output_parent,
            prefix=f".{self.output_directory.name}-",
        ) as temporary_name:
            staged = Path(temporary_name) / self.output_directory.name
            shutil.copytree(source_directory, staged)
            shutil.copy2(license_file, staged / "LICENSE")
            shutil.copy2(wheel, staged / wheel.name)
            (staged / "ref").mkdir()
            (staged / "SKILL.md").write_text(
                template.replace(self._wheel_marker, wheel.name),
                encoding="utf-8",
            )
            self._publish(staged)

    def _publish(self, staged: Path) -> None:
        output = self.output_directory
        if output.is_symlink() or (output.exists() and not output.is_dir()):
            message = f"Skill distribution target is not a directory: {output}"
            raise NotADirectoryError(message)
        if output.is_dir():
            shutil.rmtree(output)
        staged.rename(output)


class _Arguments(argparse.Namespace):
    source_directory: Path
    wheel_directory: Path
    license_file: Path
    output_directory: Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Factorio modding skill directory")
    parser.add_argument("source_directory", type=Path)
    parser.add_argument("wheel_directory", type=Path)
    parser.add_argument("license_file", type=Path)
    parser.add_argument("output_directory", type=Path)
    arguments = _Arguments()
    parser.parse_args(namespace=arguments)
    SkillDistributionBuilder(
        arguments.source_directory,
        arguments.wheel_directory,
        arguments.license_file,
        arguments.output_directory,
    ).build()


if __name__ == "__main__":
    main()
