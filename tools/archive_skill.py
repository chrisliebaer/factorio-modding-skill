from __future__ import annotations

import argparse
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SkillArchiver:
    """Create a ZIP archive containing one complete skill directory."""

    source_directory: Path
    output_archive: Path

    def archive(self) -> None:
        source = self.source_directory.resolve(strict=True)
        if not source.is_dir():
            message = f"Skill distribution is not a directory: {source}"
            raise NotADirectoryError(message)
        if self.output_archive.suffix != ".zip":
            message = f"Skill archive must use the .zip extension: {self.output_archive}"
            raise ValueError(message)

        output_parent = self.output_archive.parent
        output_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=output_parent,
            prefix=f".{self.output_archive.name}-",
            suffix=".zip",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        try:
            with zipfile.ZipFile(
                temporary_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            ) as archive:
                archive.write(source, source.name)
                for path in sorted(source.rglob("*")):
                    archive.write(path, Path(source.name) / path.relative_to(source))
            temporary_path.replace(self.output_archive)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise


class _Arguments(argparse.Namespace):
    source_directory: Path
    output_archive: Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive the Factorio modding skill")
    parser.add_argument("source_directory", type=Path)
    parser.add_argument("output_archive", type=Path)
    arguments = _Arguments()
    parser.parse_args(namespace=arguments)
    SkillArchiver(arguments.source_directory, arguments.output_archive).archive()


if __name__ == "__main__":
    main()
