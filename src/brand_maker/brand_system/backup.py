"""Checksum-bound, traversal-safe backups of mutable living workspaces."""

import hashlib
import json
import os
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo

from brand_maker.brand_system.assets import AssetChanged, AssetMissing, AssetStore
from brand_maker.brand_system.models import WorkingDraft

MAX_BACKUP_BYTES = 250_000_000
MAX_BACKUP_ENTRY_BYTES = 25_000_000
MAX_BACKUP_ENTRIES = 1_100


class InvalidWorkspaceBackup(ValueError):
    """The workspace backup is unsafe, malformed, incomplete, or checksum-invalid."""


def _safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in name


def create_workspace_backup(draft: WorkingDraft, assets: AssetStore, destination: Path) -> None:
    """Write a deterministic portable snapshot after revalidating every asset."""

    portable_assets = []
    members: dict[str, bytes] = {}
    total_bytes = 0
    try:
        for asset in draft.assets:
            asset_payload = assets.read(asset)
            total_bytes += len(asset_payload)
            if total_bytes > MAX_BACKUP_BYTES:
                raise InvalidWorkspaceBackup("workspace backup exceeds the safety limit")
            members[f"assets/{asset.content_hash}"] = asset_payload
            portable_assets.append(
                asset.model_copy(update={"storage": "managed", "source_path": None})
            )
    except (AssetMissing, AssetChanged, ValueError) as exc:
        raise InvalidWorkspaceBackup("registered asset failed integrity validation") from exc

    draft_payload = draft.model_dump(mode="json")
    draft_payload["assets"] = [asset.model_dump(mode="json") for asset in portable_assets]
    portable = WorkingDraft.model_validate(draft_payload)
    members["workspace.json"] = portable.model_dump_json().encode()
    if any(len(value) > MAX_BACKUP_ENTRY_BYTES for value in members.values()):
        raise InvalidWorkspaceBackup("workspace backup member exceeds the safety limit")
    if sum(len(value) for value in members.values()) > MAX_BACKUP_BYTES:
        raise InvalidWorkspaceBackup("workspace backup exceeds the safety limit")
    manifest = {
        "backup_version": "1.0",
        "brand_id": str(draft.brand_id),
        "members": {name: hashlib.sha256(value).hexdigest() for name, value in members.items()},
    }
    members["manifest.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        for name in sorted(members):
            info = ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, members[name])


def read_workspace_backup(source: Path) -> tuple[WorkingDraft, dict[str, bytes]]:
    """Fully validate an archive and return inert content without mutating local state."""

    if source.stat().st_size > MAX_BACKUP_BYTES:
        raise InvalidWorkspaceBackup("workspace backup exceeds the safety limit")
    try:
        with ZipFile(source) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_BACKUP_ENTRIES or len({item.filename for item in infos}) != len(
                infos
            ):
                raise InvalidWorkspaceBackup("workspace backup member set is invalid")
            if sum(item.file_size for item in infos) > MAX_BACKUP_BYTES:
                raise InvalidWorkspaceBackup("workspace backup expands beyond the safety limit")
            if any(
                not _safe_name(item.filename)
                or item.is_dir()
                or item.file_size > MAX_BACKUP_ENTRY_BYTES
                for item in infos
            ):
                raise InvalidWorkspaceBackup("workspace backup member is unsafe")
            members = {item.filename: archive.read(item) for item in infos}
    except (BadZipFile, OSError, KeyError) as exc:
        raise InvalidWorkspaceBackup("workspace backup cannot be read") from exc

    try:
        manifest = json.loads(members.pop("manifest.json"))
        expected = manifest["members"]
        if manifest["backup_version"] != "1.0" or set(expected) != set(members):
            raise InvalidWorkspaceBackup("workspace backup manifest does not match members")
        for name, payload in members.items():
            if hashlib.sha256(payload).hexdigest() != expected[name]:
                raise InvalidWorkspaceBackup("workspace backup checksum mismatch")
        draft = WorkingDraft.model_validate_json(members.pop("workspace.json"))
        if manifest["brand_id"] != str(draft.brand_id):
            raise InvalidWorkspaceBackup("workspace backup identity does not match")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, InvalidWorkspaceBackup):
            raise
        raise InvalidWorkspaceBackup("workspace backup metadata is invalid") from exc

    asset_payloads: dict[str, bytes] = {}
    registered_members: set[str] = set()
    for asset in draft.assets:
        if asset.storage != "managed" or asset.source_path is not None:
            raise InvalidWorkspaceBackup("workspace backup contains a non-portable asset")
        name = f"assets/{asset.content_hash}"
        value = members.get(name)
        if value is None or len(value) != asset.size_bytes:
            raise InvalidWorkspaceBackup("registered asset is missing or has the wrong size")
        if hashlib.sha256(value).hexdigest() != asset.content_hash:
            raise InvalidWorkspaceBackup("registered asset checksum mismatch")
        asset_payloads[asset.content_hash] = value
        registered_members.add(name)
    if set(members) != registered_members:
        raise InvalidWorkspaceBackup("workspace backup contains unregistered members")
    return draft, asset_payloads


def install_backup_assets(asset_root: Path, assets: dict[str, bytes]) -> list[Path]:
    """Install assets atomically and return newly created blobs for rollback."""

    created: list[Path] = []
    for content_hash, payload in assets.items():
        destination = asset_root / content_hash[:2] / content_hash[2:]
        destination.parent.mkdir(parents=True, exist_ok=True)
        existing_hash = (
            hashlib.sha256(destination.read_bytes()).hexdigest()
            if destination.exists() and destination.stat().st_size <= MAX_BACKUP_ENTRY_BYTES
            else None
        )
        if existing_hash == content_hash:
            continue
        was_missing = not destination.exists()
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
            temporary.write(payload)
            temporary_path = Path(temporary.name)
        try:
            os.replace(temporary_path, destination)
            if was_missing:
                created.append(destination)
        finally:
            temporary_path.unlink(missing_ok=True)
    return created


def discard_installed_backup_assets(paths: list[Path]) -> None:
    """Remove only blobs created by a restore whose database transaction failed."""

    for path in paths:
        path.unlink(missing_ok=True)
        try:
            path.parent.rmdir()
        except OSError:
            pass
