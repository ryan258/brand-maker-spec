from uuid import UUID

from brand_maker.workshop_web import workspace_detail


def test_workshop_exposes_accessible_generation_controls() -> None:
    page = workspace_detail(UUID("d795ebf9-8f54-44a2-85cd-e73faacb7008"))

    assert 'id="generate-complete"' in page
    assert 'id="generate-section"' in page
    assert 'id="generation-progress"' in page
    assert 'role="status"' in page
    assert "Pause generation" in page
    assert "Cancel generation" in page
