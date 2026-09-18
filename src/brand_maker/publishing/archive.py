"""Checksum-bound, traversal-safe canonical publication archives."""

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path, PurePosixPath
from uuid import uuid4
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo

from brand_maker.brand_system.amendments import SCHEMA as AMENDMENT_SCHEMA
from brand_maker.brand_system.amendments import (
    AmendmentTargetNotClerical,
    SQLiteAmendmentRepository,
)
from brand_maker.brand_system.models import PublishedVersion, RenderedPublishedVersion
from brand_maker.brand_system.publication import SCHEMA as PUBLICATION_SCHEMA
from brand_maker.brand_system.publication import canonical_content_hash
from brand_maker.models import ContractModel

MAX_ARCHIVE_BYTES = 250_000_000
MAX_ENTRY_BYTES = 25_000_000
MAX_ENTRIES = 1_000


class InvalidArchive(ValueError):
    pass


class ArchiveContents(ContractModel):
    published: PublishedVersion
    rendered: RenderedPublishedVersion


def _asset_path(root: Path, content_hash: str) -> Path:
    return root / content_hash[:2] / content_hash[2:]


def create_archive(
    published: PublishedVersion,
    asset_root: Path,
    destination: Path,
    *,
    rendered: RenderedPublishedVersion | None = None,
) -> None:
    exact = rendered or RenderedPublishedVersion(
        brand_id=published.brand_id,
        version=published.version,
        amendment_revision=0,
        rendered_change_summary=published.change_summary,
        rendered_snapshot=published.snapshot,
        amendments=[],
    )
    contents = ArchiveContents(published=published, rendered=exact)
    members: dict[str, bytes] = {"archive.json": contents.model_dump_json().encode()}
    for asset in exact.rendered_snapshot.assets:
        # Only managed blobs live under the asset root; an optional linked asset stays on the
        # owner's disk and is carried by its registration alone.
        if asset.storage != "managed":
            if asset.required:
                raise InvalidArchive(f"required asset is not managed: {asset.id}")
            continue
        source = _asset_path(asset_root, asset.content_hash)
        payload = source.read_bytes()
        if (
            len(payload) != asset.size_bytes
            or hashlib.sha256(payload).hexdigest() != asset.content_hash
        ):
            raise InvalidArchive(f"managed asset does not match registration: {asset.id}")
        members[f"assets/{asset.content_hash}"] = payload
    manifest = {
        "archive_version": "1.0",
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


def _safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in name


def _read_validated(source: Path) -> tuple[ArchiveContents, dict[str, bytes]]:
    if source.stat().st_size > MAX_ARCHIVE_BYTES:
        raise InvalidArchive("archive exceeds the safety limit")
    try:
        with ZipFile(source) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ENTRIES or len({item.filename for item in infos}) != len(infos):
                raise InvalidArchive("archive member set is invalid")
            if sum(item.file_size for item in infos) > MAX_ARCHIVE_BYTES:
                raise InvalidArchive("archive expands beyond the safety limit")
            if any(
                not _safe_name(item.filename) or item.is_dir() or item.file_size > MAX_ENTRY_BYTES
                for item in infos
            ):
                raise InvalidArchive("archive member is unsafe")
            members = {item.filename: archive.read(item) for item in infos}
    except (BadZipFile, OSError, KeyError) as exc:
        raise InvalidArchive("archive cannot be read") from exc
    try:
        manifest = json.loads(members.pop("manifest.json"))
        expected = manifest["members"]
        if manifest["archive_version"] != "1.0" or set(expected) != set(members):
            raise InvalidArchive("archive manifest does not match members")
        for name, payload in members.items():
            if hashlib.sha256(payload).hexdigest() != expected[name]:
                raise InvalidArchive("archive checksum mismatch")
        contents = ArchiveContents.model_validate_json(members.pop("archive.json"))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, InvalidArchive):
            raise
        raise InvalidArchive("archive metadata is invalid") from exc
    assets: dict[str, bytes] = {}
    for asset in contents.rendered.rendered_snapshot.assets:
        if asset.storage != "managed":
            continue
        name = f"assets/{asset.content_hash}"
        asset_payload = members.get(name)
        if asset_payload is None or len(asset_payload) != asset.size_bytes:
            raise InvalidArchive("registered asset is missing or has the wrong size")
        # Two registrations may share one blob, so validate each blob once and leave the
        # member in place for the next registration that points at it.
        if asset.content_hash not in assets:
            if hashlib.sha256(asset_payload).hexdigest() != asset.content_hash:
                raise InvalidArchive("registered asset checksum mismatch")
            assets[asset.content_hash] = asset_payload
    unregistered = set(members) - {f"assets/{content_hash}" for content_hash in assets}
    if unregistered:
        raise InvalidArchive("archive contains unregistered members")
    _validate_publication_claims(contents)
    return contents, assets


def _validate_publication_claims(contents: ArchiveContents) -> None:
    """Member checksums only prove the ZIP is intact; check what the publication claims."""

    published = contents.published
    rendered = contents.rendered
    if canonical_content_hash(published.snapshot) != published.content_hash:
        raise InvalidArchive("published content hash does not match its snapshot")
    if published.manifest.draft_revision != published.snapshot.revision:
        raise InvalidArchive("published manifest does not match its snapshot revision")
    if published.manifest.section_ids != [item.id for item in published.snapshot.sections]:
        raise InvalidArchive("published manifest does not match its snapshot sections")
    if any(
        approval.brand_id != published.brand_id
        or approval.draft_revision != published.draft_revision
        for approval in published.approvals
    ):
        raise InvalidArchive("approval does not belong to this published version")
    if rendered.brand_id != published.brand_id or rendered.version != published.version:
        raise InvalidArchive("rendered publication does not match its published version")
    if rendered.amendment_revision != len(rendered.amendments):
        raise InvalidArchive("rendered amendment revision does not match its amendments")
    if any(
        amendment.brand_id != published.brand_id
        or amendment.version != published.version
        or amendment.amendment_revision != index
        for index, amendment in enumerate(rendered.amendments, start=1)
    ):
        raise InvalidArchive("amendment does not belong to this published version")
    try:
        snapshot, summary = SQLiteAmendmentRepository._render(published, list(rendered.amendments))
    except (AmendmentTargetNotClerical, ValueError) as exc:
        raise InvalidArchive("archived amendments cannot be reapplied") from exc
    if snapshot != rendered.rendered_snapshot or summary != rendered.rendered_change_summary:
        raise InvalidArchive("rendered snapshot does not match its amendments")


def restore_archive(source: Path, asset_root: Path) -> ArchiveContents:
    contents, assets = _read_validated(source)
    _install_assets(asset_root, assets)
    return contents


def _install_assets(asset_root: Path, assets: dict[str, bytes]) -> None:
    asset_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="brand-restore-", dir=asset_root.parent))
    backup = asset_root.parent / f".brand-assets-backup-{uuid4()}"
    try:
        if asset_root.exists():
            shutil.copytree(asset_root, temporary, dirs_exist_ok=True)
        for content_hash, payload in assets.items():
            destination = _asset_path(temporary, content_hash)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        if asset_root.exists():
            os.replace(asset_root, backup)
        try:
            os.replace(temporary, asset_root)
        except Exception:
            if backup.exists():
                os.replace(backup, asset_root)
            raise
        shutil.rmtree(backup, ignore_errors=True)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def import_archive(source: Path, *, asset_root: Path, database_path: Path) -> ArchiveContents:
    contents, assets = _read_validated(source)
    published = contents.published
    with sqlite3.connect(database_path, timeout=5.0) as connection:
        connection.executescript(PUBLICATION_SCHEMA)
        connection.execute(AMENDMENT_SCHEMA)
        existing = connection.execute(
            """SELECT content_hash, snapshot_json FROM published_brand_versions
               WHERE brand_id=? AND version=?""",
            (str(published.brand_id), published.version),
        ).fetchone()
        if existing is not None:
            if existing != (published.content_hash, published.snapshot.model_dump_json()):
                raise InvalidArchive("published version conflicts with local data")
        else:
            connection.execute(
                "INSERT INTO published_brand_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(published.brand_id),
                    published.version,
                    published.published_at.isoformat(),
                    published.publisher_id,
                    published.draft_revision,
                    published.change_summary,
                    published.content_hash,
                    published.manifest.model_dump_json(),
                    json.dumps([item.model_dump(mode="json") for item in published.approvals]),
                    published.snapshot.model_dump_json(),
                ),
            )
        for amendment in contents.rendered.amendments:
            amendment_values = (
                str(amendment.id),
                str(amendment.brand_id),
                amendment.version,
                amendment.amendment_revision,
                amendment.target_id,
                amendment.field,
                amendment.category,
                amendment.before,
                amendment.after,
                amendment.rationale,
                amendment.owner_id,
                amendment.approved_at.isoformat(),
            )
            existing_amendment = connection.execute(
                """SELECT id, brand_id, version, amendment_revision, target_id,
                          field, category, before_value, after_value, rationale,
                          owner_id, approved_at FROM publication_amendments
                   WHERE brand_id=? AND version=? AND amendment_revision=?""",
                (
                    str(amendment.brand_id),
                    amendment.version,
                    amendment.amendment_revision,
                ),
            ).fetchone()
            if existing_amendment is not None:
                if existing_amendment != amendment_values:
                    raise InvalidArchive("amendment conflicts with local data")
                continue
            connection.execute(
                "INSERT INTO publication_amendments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                amendment_values,
            )
        # Last inside the transaction: a database conflict must not leave a replaced asset
        # tree behind, and a failed asset swap rolls the inserts back on the way out.
        _install_assets(asset_root, assets)
    return contents
