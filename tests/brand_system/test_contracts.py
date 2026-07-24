from copy import deepcopy
from uuid import UUID

import pytest
from pydantic import ValidationError

from brand_maker.brand_system.models import WorkingDraft, WorkspaceSummary


def valid_draft() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "brand_id": "d795ebf9-8f54-44a2-85cd-e73faacb7008",
        "brand_name": "Northstar Studio",
        "owner": {"id": "local-owner", "display_name": "Ryan"},
        "revision": 1,
        "status": "draft",
        "sections": [
            {
                "id": "section.strategy",
                "title": "Strategy",
                "status": "draft",
                "locked": False,
                "blocks": [
                    {
                        "id": "block.purpose",
                        "type": "paragraph",
                        "text": "Make complex work feel navigable.",
                        "references": [{"kind": "rule", "target_id": "rule.voice.direct"}],
                    }
                ],
                "rules": [
                    {
                        "id": "rule.voice.direct",
                        "name": "Use direct language",
                        "description": "Prefer concrete language and active voice.",
                        "enforcement": "advisory",
                        "references": [],
                    }
                ],
                "tokens": [
                    {
                        "id": "token.color.primary",
                        "name": "Primary color",
                        "value_type": "color",
                        "value": "#112233",
                        "references": [],
                    }
                ],
                "examples": [
                    {
                        "id": "example.voice.do",
                        "kind": "do",
                        "text": "Lead with the decision.",
                        "references": [{"kind": "token", "target_id": "token.color.primary"}],
                    }
                ],
                "patterns": [
                    {
                        "id": "pattern.voice.say-never-say",
                        "name": "Say and never say",
                        "kind": "say_never_say",
                        "summary": "Translate the voice into repeatable language choices.",
                        "specifications": [
                            {
                                "label": "Audience posture",
                                "value": "Speak as a capable guide, never an authority figure.",
                            }
                        ],
                        "do_guidance": ["Say: Here is the clearest next step."],
                        "dont_guidance": ["Never say: Trust us, we know best."],
                        "references": [],
                    }
                ],
            }
        ],
    }


def test_valid_draft_round_trips_through_canonical_json() -> None:
    draft = WorkingDraft.model_validate(valid_draft())

    restored = WorkingDraft.model_validate_json(draft.model_dump_json())

    assert restored == draft
    assert restored.schema_version == "1.0"
    assert restored.brand_id == UUID("d795ebf9-8f54-44a2-85cd-e73faacb7008")
    assert WorkspaceSummary.from_draft(restored).model_dump(mode="json") == {
        "brand_id": "d795ebf9-8f54-44a2-85cd-e73faacb7008",
        "brand_name": "Northstar Studio",
        "revision": 1,
        "status": "draft",
        "section_count": 1,
        "complete_section_count": 0,
    }


def test_unsupported_narrative_block_type_is_rejected() -> None:
    payload = valid_draft()
    payload["sections"][0]["blocks"][0]["type"] = "raw_html"  # type: ignore[index]

    with pytest.raises(ValidationError, match="type"):
        WorkingDraft.model_validate(payload)


@pytest.mark.parametrize(
    "text",
    [
        "<script>alert('nope')</script>",
        '<img src=x onerror="alert(1)">',
        "A safe-looking <strong>HTML fragment</strong>.",
    ],
)
def test_raw_html_is_rejected_from_narrative_text(text: str) -> None:
    payload = valid_draft()
    payload["sections"][0]["blocks"][0]["text"] = text  # type: ignore[index]

    with pytest.raises(ValidationError, match="raw HTML"):
        WorkingDraft.model_validate(payload)


def test_raw_html_is_rejected_from_pattern_specifications() -> None:
    payload = valid_draft()
    payload["sections"][0]["patterns"][0]["specifications"][0][  # type: ignore[index]
        "value"
    ] = '<button onclick="alert(1)">Act</button>'

    with pytest.raises(ValidationError, match="raw HTML"):
        WorkingDraft.model_validate(payload)


def test_duplicate_stable_ids_are_rejected_across_canonical_elements() -> None:
    payload = valid_draft()
    payload["sections"][0]["examples"][0]["id"] = "rule.voice.direct"  # type: ignore[index]

    with pytest.raises(ValidationError, match=r"duplicate canonical id: rule\.voice\.direct"):
        WorkingDraft.model_validate(payload)


def test_dangling_semantic_references_are_rejected() -> None:
    payload = valid_draft()
    payload["sections"][0]["blocks"][0]["references"][0][  # type: ignore[index]
        "target_id"
    ] = "rule.missing"

    with pytest.raises(ValidationError, match=r"dangling reference: rule\.missing"):
        WorkingDraft.model_validate(payload)


def test_token_reference_cycles_are_rejected() -> None:
    payload = valid_draft()
    first_token = payload["sections"][0]["tokens"][0]  # type: ignore[index]
    first_token["references"] = [  # type: ignore[index]
        {"kind": "token", "target_id": "token.color.secondary"}
    ]
    second_token = deepcopy(first_token)
    second_token.update(
        {
            "id": "token.color.secondary",
            "name": "Secondary color",
            "value": "#445566",
            "references": [{"kind": "token", "target_id": "token.color.primary"}],
        }
    )
    payload["sections"][0]["tokens"].append(second_token)  # type: ignore[index]

    with pytest.raises(ValidationError, match="token reference cycle"):
        WorkingDraft.model_validate(payload)


def test_blank_and_malformed_stable_ids_are_rejected() -> None:
    payload = valid_draft()
    payload["sections"][0]["id"] = " ../unsafe "  # type: ignore[index]

    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        WorkingDraft.model_validate(payload)
