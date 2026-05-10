from __future__ import annotations

from src.domain.evaluation.dto import ReferenceAspectDTO, ReferenceEvidenceDTO
from src.infrastructure.db.models.reference_ledger import ReferenceLedgerDB


def ledger_orm_to_aspect_dtos(ledger: ReferenceLedgerDB) -> list[ReferenceAspectDTO]:
    """Конвертация загруженного ORM ledger в DTO для метрик."""
    aspects: list[ReferenceAspectDTO] = []
    for asp in ledger.aspects:
        evs = [
            ReferenceEvidenceDTO(
                review_id=ev.review_id,
                text=ev.text,
                section_type=ev.section_type,
                polarity=ev.polarity,
                evidence_strength=ev.evidence_strength,
            )
            for ev in asp.evidences
        ]
        aspects.append(
            ReferenceAspectDTO(
                aspect_name=asp.aspect_name,
                aliases=list(asp.aliases_json or []),
                salience_weight=float(asp.salience_weight),
                expected_polarity=asp.expected_polarity,
                polarity_distribution=dict(asp.polarity_distribution_json or {}),
                rare_but_important=bool(asp.rare_but_important),
                evidence_items=evs,
            )
        )
    return aspects
