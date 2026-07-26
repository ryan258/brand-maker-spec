import hashlib
from pathlib import Path
from uuid import UUID

import pytest

from brand_maker.brand_system.assets import AssetStore
from brand_maker.brand_system.backup import (
    InvalidWorkspaceBackup,
    create_workspace_backup,
    discard_installed_backup_assets,
    install_backup_assets,
    read_workspace_backup,
)
from brand_maker.brand_system.models import AssetRegistration, LocalOwner, WorkingDraft


def test_backup_refuses_a_missing_registered_asset(tmp_path: Path) -> None:
    draft = WorkingDraft(
        brand_id=UUID("d795ebf9-8f54-44a2-85cd-e73faacb7008"),
        brand_name="Northstar",
        owner=LocalOwner(display_name="Ryan"),
        revision=1,
        assets=[
            AssetRegistration(
                id="asset.logo",
                name="Logo",
                storage="managed",
                media_type="image/png",
                size_bytes=8,
                content_hash="0" * 64,
            )
        ],
    )

    with pytest.raises(InvalidWorkspaceBackup):
        create_workspace_backup(
            draft,
            AssetStore(tmp_path / "assets"),
            tmp_path / "backup.zip",
        )


def test_backup_deduplicates_shared_asset_content_and_round_trips(tmp_path: Path) -> None:
    source = tmp_path / "logo.png"
    source.write_bytes(b"valid-logo-bytes")
    store = AssetStore(tmp_path / "assets")
    first = store.import_managed(
        asset_id="asset.logo.primary",
        name="Primary logo",
        source=source,
        media_type="image/png",
        required=True,
    )
    draft = WorkingDraft(
        brand_id=UUID("d795ebf9-8f54-44a2-85cd-e73faacb7008"),
        brand_name="Northstar",
        owner=LocalOwner(display_name="Ryan"),
        revision=1,
        assets=[
            first,
            first.model_copy(update={"id": "asset.logo.secondary", "name": "Secondary logo"}),
        ],
    )
    destination = tmp_path / "backup.zip"

    create_workspace_backup(draft, store, destination)
    restored, payloads = read_workspace_backup(destination)

    assert [asset.id for asset in restored.assets] == [
        "asset.logo.primary",
        "asset.logo.secondary",
    ]
    assert payloads == {first.content_hash: b"valid-logo-bytes"}


def test_backup_asset_install_can_roll_back_only_new_blobs(tmp_path: Path) -> None:
    existing_payload = b"existing"
    existing_hash = hashlib.sha256(existing_payload).hexdigest()
    new_payload = b"new"
    new_hash = hashlib.sha256(new_payload).hexdigest()
    existing_path = tmp_path / existing_hash[:2] / existing_hash[2:]
    existing_path.parent.mkdir(parents=True)
    existing_path.write_bytes(existing_payload)

    created = install_backup_assets(
        tmp_path,
        {existing_hash: existing_payload, new_hash: new_payload},
    )
    discard_installed_backup_assets(created)

    assert existing_path.read_bytes() == existing_payload
    assert not (tmp_path / new_hash[:2] / new_hash[2:]).exists()
