"""Bounded linked and content-addressed local asset storage."""

import hashlib
import os
import stat
import tempfile
from io import BytesIO
from pathlib import Path

from fontTools.ttLib import TTFont  # type: ignore[import-untyped]

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
MAX_DECODED_FONT_BYTES = 25_000_000


class AssetMissing(FileNotFoundError):
    pass


class AssetChanged(RuntimeError):
    pass


class AssetStore:
    def __init__(self, root: Path, *, max_bytes: int = 25_000_000) -> None:
        self._root = root
        self._max_bytes = max_bytes
        self.max_bytes = max_bytes  # public: upload routes cap streaming before hashing

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
        registration, _ = self.import_managed_with_status(
            asset_id=asset_id,
            name=name,
            source=source,
            media_type=media_type,
            required=required,
        )
        return registration

    def import_managed_with_status(
        self,
        *,
        asset_id: str,
        name: str,
        source: Path,
        media_type: str,
        required: bool,
    ) -> tuple[AssetRegistration, bool]:
        """Import an asset and report whether this call created its managed blob."""

        size, content_hash = self._inspect(source, media_type)
        destination = self._root / content_hash[:2] / content_hash[2:]
        destination.parent.mkdir(parents=True, exist_ok=True)
        created = not destination.exists()
        if created:
            with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
                temporary_path = Path(temporary.name)
                with source.open("rb") as handle:
                    while chunk := handle.read(64 * 1024):
                        temporary.write(chunk)
            try:
                os.replace(temporary_path, destination)
            finally:
                temporary_path.unlink(missing_ok=True)
        return (
            AssetRegistration(
                id=asset_id,
                name=name,
                storage="managed",
                media_type=media_type,
                size_bytes=size,
                content_hash=content_hash,
                required=required,
            ),
            created,
        )

    def discard_managed(self, asset: AssetRegistration) -> None:
        """Remove a managed blob after a failed registration transaction."""

        if asset.storage != "managed":
            raise ValueError("only managed assets can be discarded")
        destination = self._root / asset.content_hash[:2] / asset.content_hash[2:]
        destination.unlink(missing_ok=True)

    def read(self, asset: AssetRegistration) -> bytes:
        """Read an asset only after revalidating its registered integrity metadata."""

        if asset.storage == "managed":
            source = self._root / asset.content_hash[:2] / asset.content_hash[2:]
        elif asset.source_path is not None:
            source = Path(asset.source_path)
        else:
            raise AssetMissing(asset.id)
        if asset.media_type not in ALLOWED_MEDIA_TYPES:
            raise ValueError("unsupported media type")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(source, flags)
        except FileNotFoundError as exc:
            raise AssetMissing(asset.id) from exc
        except OSError as exc:
            raise ValueError("asset source could not be opened safely") from exc

        digest = hashlib.sha256()
        content = bytearray()
        with os.fdopen(descriptor, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise AssetMissing(asset.id)
            while chunk := handle.read(64 * 1024):
                content.extend(chunk)
                if len(content) > self._max_bytes:
                    raise ValueError("asset exceeds the safety limit")
                digest.update(chunk)
        if len(content) != asset.size_bytes or digest.hexdigest() != asset.content_hash:
            raise AssetChanged(asset.id)
        return bytes(content)

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


def validate_font_file_header(content: bytes) -> str:
    """Parse and verify WOFF, WOFF2, TTF, and OTF font files."""
    if len(content) < 4:
        raise ValueError("File content too short to be a valid font.")
    magic = content[:4]
    formats = {
        b"wOFF": "woff",
        b"wOF2": "woff2",
        b"\x00\x01\x00\x00": "truetype",
        b"true": "truetype",
        b"OTTO": "opentype",
    }
    font_format = formats.get(magic)
    if font_format is None:
        raise ValueError(
            "Invalid font magic bytes. Only valid WOFF, WOFF2, TTF, or OTF files are accepted."
        )

    if font_format in {"woff", "woff2"} and len(content) >= 20:
        declared_size = int.from_bytes(content[16:20], "big")
        if declared_size > MAX_DECODED_FONT_BYTES:
            raise ValueError("Font decoded size exceeds the 25MB safety limit.")

    try:
        font = TTFont(BytesIO(content), lazy=False, recalcBBoxes=False, recalcTimestamp=False)
        try:
            for table_name in font.keys():
                font[table_name]
        finally:
            font.close()
    except Exception as exc:
        raise ValueError("Font file could not be parsed as a valid font.") from exc
    return font_format


def generate_font_face_css(font_family: str, media_type: str, asset_url: str) -> str:
    """Generate safe @font-face CSS declaration for uploaded brand font."""
    format_map = {
        "font/woff": "woff",
        "font/woff2": "woff2",
        "font/ttf": "truetype",
        "font/otf": "opentype",
        "application/octet-stream": "truetype",
    }
    font_fmt = format_map.get(media_type, "truetype")
    safe_family = "".join(c for c in font_family if c.isalnum() or c in " -_").strip()
    if not safe_family:
        raise ValueError("font family must contain at least one letter or number")
    return (
        f"@font-face {{\n"
        f"  font-family: '{safe_family}';\n"
        f"  src: url('{asset_url}') format('{font_fmt}');\n"
        f"  font-display: swap;\n"
        f"}}\n"
    )
