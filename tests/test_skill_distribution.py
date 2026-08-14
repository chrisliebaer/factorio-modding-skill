from pathlib import Path
from zipfile import ZipFile

from tools.archive_skill import SkillArchiver
from tools.build_skill import SkillDistributionBuilder


class TestSkillDistribution:
    def test_builds_skill_directory_with_rendered_wheel_and_empty_ref(
        self,
        tmp_path: Path,
    ) -> None:
        source = tmp_path / "skill"
        source.mkdir()
        (source / "SKILL.md").write_text(
            "run {{WHEEL_FILENAME}}\n",
            encoding="utf-8",
        )
        (source / "guide.md").write_text("guide\n", encoding="utf-8")
        wheels = tmp_path / "wheels"
        wheels.mkdir()
        wheel = wheels / "factorio_docs-0.1.0-py3-none-any.whl"
        wheel.write_bytes(b"wheel")
        license_file = tmp_path / "LICENSE"
        license_file.write_text("license\n", encoding="utf-8")
        output = tmp_path / "dist" / "factorio-modding"

        SkillDistributionBuilder(source, wheels, license_file, output).build()

        assert (output / "SKILL.md").read_text(encoding="utf-8") == f"run {wheel.name}\n"
        assert (output / wheel.name).read_bytes() == b"wheel"
        assert (output / "LICENSE").read_text(encoding="utf-8") == "license\n"
        assert (output / "guide.md").read_text(encoding="utf-8") == "guide\n"
        assert tuple((output / "ref").iterdir()) == ()

    def test_archives_distribution_with_empty_ref_directory(self, tmp_path: Path) -> None:
        source = tmp_path / "factorio-modding"
        source.mkdir()
        (source / "SKILL.md").write_text("skill\n", encoding="utf-8")
        (source / "ref").mkdir()
        output = tmp_path / "factorio-modding.zip"

        SkillArchiver(source, output).archive()

        with ZipFile(output) as archive:
            assert set(archive.namelist()) == {
                "factorio-modding/",
                "factorio-modding/SKILL.md",
                "factorio-modding/ref/",
            }
