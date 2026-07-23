"""Bounded linked and content-addressed local asset storage."""

import hashlib
import os
import tempfile
from pathlib import Path

from brand_maker.brand_system.models import AssetRegistration, WorkingDraft

ALLOWED_MEDIA_TYPES = {
    "application/octet-stream",
    "application/pdf",
    "font/otf",
    "font/ttf",
    "font/woff",
    "font/woff2",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
    "image/webp",
}


class AssetMissing(FileNotFoundError):
    pass


class AssetChanged(RuntimeError):
    pass


class AssetStore:
    def __init__(self, root: Path, *, max_bytes: int = 25_000_000) -> None:
        self._root = root
        self._max_bytes = max_bytes

    def _inspect(self, source: Path, media_type: str) -> tuple[int, str]:
        if media_type not in ALLOWED_MEDIA_TYPES:
            raise ValueError("unsupported media type")
        if source.is_symlink():
            raise ValueError("symbolic links are not accepted as assets")
        if not source.exists() or not source.is_file():
            raise AssetMissing(str(source))
        size = source.stat().st_size
        if size < 1 or size > self._max_bytes:
            raise ValueError("asset exceeds the safety limit")
        digest = hashlib.sha256()
        observed = 0
        with source.open("rb") as handle:
            while chunk := handle.read(64 * 1024):
                observed += len(chunk)
                if observed > self._max_bytes:
                    raise ValueError("asset exceeds the safety limit")
                digest.update(chunk)
        if observed != size:
            raise AssetChanged("asset changed while being read")
        return size, digest.hexdigest()

    def register_linked(
        self,
        *,
        asset_id: str,
        name: str,
        source: Path,
        media_type: str,
        required: bool,
    ) -> AssetRegistration:
        size, content_hash = self._inspect(source, media_type)
        return AssetRegistration(
            id=asset_id,
            name=name,
            storage="linked",
            media_type=media_type,
            size_bytes=size,
            content_hash=content_hash,
            source_path=str(source.resolve()),
            required=required,
        )

    def import_managed(
        self,
        *,
        asset_id: str,
        name: str,
        source: Path,
        media_type: str,
        required: bool,
    ) -> AssetRegistration:
        size, content_hash = self._inspect(source, media_type)
        destination = self._root / content_hash[:2] / content_hash[2:]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
                temporary_path = Path(temporary.name)
                with source.open("rb") as handle:
                    while chunk := handle.read(64 * 1024):
                        temporary.write(chunk)
            try:
                os.replace(temporary_path, destination)
            finally:
                temporary_path.unlink(missing_ok=True)
        return AssetRegistration(
            id=asset_id,
            name=name,
            storage="managed",
            media_type=media_type,
            size_bytes=size,
            content_hash=content_hash,
            required=required,
        )

    def prepare_publication(self, draft: WorkingDraft) -> WorkingDraft:
        assets: list[AssetRegistration] = []
        for asset in draft.assets:
            if asset.storage == "managed" or not asset.required:
                assets.append(asset)
                continue
            if asset.source_path is None:
                raise AssetMissing(asset.id)
            source = Path(asset.source_path)
            try:
                size, content_hash = self._inspect(source, asset.media_type)
            except FileNotFoundError as exc:
                raise AssetMissing(asset.id) from exc
            if size != asset.size_bytes or content_hash != asset.content_hash:
                raise AssetChanged(asset.id)
            assets.append(
                self.import_managed(
                    asset_id=asset.id,
                    name=asset.name,
                    source=source,
                    media_type=asset.media_type,
                    required=asset.required,
                )
            )
        payload = draft.model_dump(mode="json")
        payload["assets"] = [asset.model_dump(mode="json") for asset in assets]
        return WorkingDraft.model_validate(payload)
