from __future__ import annotations

import shutil
from pathlib import Path


class ImageAssetPublisher:
    """Publish official static assets into a generated documentation tree."""

    @staticmethod
    def publish(source_static_directory: Path, output_directory: Path) -> Path:
        source_static_directory = source_static_directory.resolve(strict=True)
        if not source_static_directory.is_dir():
            message = f"Documentation static source is not a directory: {source_static_directory}"
            raise NotADirectoryError(message)
        source_images = source_static_directory / "images"
        if not source_images.is_dir():
            message = f"Documentation image source is not a directory: {source_images}"
            raise NotADirectoryError(message)
        source_root_assets = tuple(
            path
            for path in source_static_directory.iterdir()
            if path.is_file() and path.suffix != ".html"
        )

        published_static_directory = output_directory.resolve() / "static"
        if published_static_directory.is_symlink() or (
            published_static_directory.exists() and not published_static_directory.is_dir()
        ):
            message = (
                f"Documentation static destination is not a directory: {published_static_directory}"
            )
            raise NotADirectoryError(message)
        published_images = published_static_directory / "images"
        if published_images.exists() or published_images.is_symlink():
            message = f"Documentation image destination already exists: {published_images}"
            raise FileExistsError(message)

        published_static_directory.mkdir(parents=True, exist_ok=True)
        for source_asset in source_root_assets:
            shutil.copy2(source_asset, published_static_directory / source_asset.name)
        shutil.copytree(source_images, published_images)
        return published_static_directory
