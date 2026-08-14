from __future__ import annotations

import shutil
from pathlib import Path


class ImageAssetPublisher:
    """Publish official documentation images into a generated documentation tree."""

    @staticmethod
    def publish(source_static_directory: Path, output_directory: Path) -> Path:
        source_images = source_static_directory.resolve(strict=True) / "images"
        if not source_images.is_dir():
            message = f"Documentation image source is not a directory: {source_images}"
            raise NotADirectoryError(message)

        published_static_directory = output_directory.resolve() / "static"
        published_images = published_static_directory / "images"
        if published_images.exists() or published_images.is_symlink():
            message = f"Documentation image destination already exists: {published_images}"
            raise FileExistsError(message)

        published_static_directory.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_images, published_images)
        return published_static_directory
