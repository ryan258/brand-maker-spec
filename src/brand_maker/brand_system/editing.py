"""Dependency-aware, fully validated canonical section edits."""

from pydantic import ValidationError

from brand_maker.brand_system.models import (
    BrandExample,
    BrandPattern,
    BrandRule,
    BrandSection,
    BrandToken,
    EditImpact,
    NarrativeBlock,
    ValidationIssue,
    WorkingDraft,
)


def _items(section: BrandSection) -> dict[str, object]:
    result: dict[str, object] = {section.id: section}
    result.update({item.id: item for item in section.blocks})
    result.update({item.id: item for item in section.rules})
    result.update({item.id: item for item in section.tokens})
    result.update({item.id: item for item in section.examples})
    result.update({item.id: item for item in section.patterns})
    return result


def _has_changed_reference(
    item: NarrativeBlock | BrandRule | BrandToken | BrandExample | BrandPattern,
    changed: list[str],
) -> bool:
    return any(reference.target_id in changed for reference in item.references)


def preview_section_edit(
    draft: WorkingDraft, replacement: BrandSection
) -> tuple[EditImpact, WorkingDraft | None]:
    """Return downstream impact and a validated candidate when the edit is safe."""

    current = next((item for item in draft.sections if item.id == replacement.id), None)
    if current is None:
        raise LookupError("section not found")
    before = _items(current)
    after = _items(replacement)
    changed = sorted(
        canonical_id
        for canonical_id in before.keys() | after.keys()
        if before.get(canonical_id) != after.get(canonical_id)
    )
    affected_ids: set[str] = set()
    for section in draft.sections:
        for block in section.blocks:
            if _has_changed_reference(block, changed):
                affected_ids.add(block.id)
        for rule in section.rules:
            if _has_changed_reference(rule, changed):
                affected_ids.add(rule.id)
        for token in section.tokens:
            if _has_changed_reference(token, changed):
                affected_ids.add(token.id)
        for example in section.examples:
            if _has_changed_reference(example, changed):
                affected_ids.add(example.id)
        for pattern in section.patterns:
            if _has_changed_reference(pattern, changed):
                affected_ids.add(pattern.id)
    affected = sorted(affected_ids)
    sections = [replacement if item.id == replacement.id else item for item in draft.sections]
    payload = draft.model_dump(mode="json")
    payload.update({"sections": [item.model_dump(mode="json") for item in sections]})
    try:
        candidate = WorkingDraft.model_validate(payload)
        errors: list[ValidationIssue] = []
    except ValidationError as exc:
        candidate = None
        errors = [
            ValidationIssue(
                location=".".join(str(part) for part in error["loc"]),
                message=str(error["msg"]),
            )
            for error in exc.errors(include_url=False)
        ]
    return (
        EditImpact(
            changed_ids=changed,
            affected_ids=affected,
            blocking_errors=errors,
            warnings=[
                ValidationIssue(
                    location=canonical_id,
                    message="This item references content changed by the proposed edit.",
                )
                for canonical_id in affected
            ],
            advice=(
                []
                if changed
                else [
                    ValidationIssue(
                        location=replacement.id,
                        message="The proposed section is identical to the current section.",
                    )
                ]
            ),
            can_apply=candidate is not None,
        ),
        candidate,
    )
