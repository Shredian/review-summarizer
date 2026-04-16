from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    ContentPlan,
    EvidenceItem,
    GenerationOutput,
    VerificationResult,
)


class SummaryVerifier:
    """Проверка покрытия плана и grounded-ограничений."""

    def verify(
        self,
        plan: ContentPlan,
        evidence_items: list[EvidenceItem],
        output: GenerationOutput,
    ) -> VerificationResult:
        errors: list[str] = []
        warnings: list[str] = []
        evidence_aspects = {item.aspect_name for item in evidence_items}
        planned_aspects = {item.aspect_name for item in plan.selected_aspects}

        missing_aspects = sorted(planned_aspects - evidence_aspects)
        if missing_aspects:
            errors.append(f"Нет evidence для аспектов: {', '.join(missing_aspects)}")

        text_blob = " ".join(
            filter(
                None,
                [output.text_overall, output.text_pros, output.text_cons, output.text_neutral],
            )
        ).lower()
        for aspect_name in planned_aspects:
            if aspect_name.lower() not in text_blob:
                warnings.append(f"Аспект '{aspect_name}' не отражен явно в тексте")

        if not output.text_overall and not output.text_pros and not output.text_cons:
            errors.append("Пустой результат генерации")

        return VerificationResult(
            passed=not errors,
            errors=errors,
            warnings=warnings,
            revised_output=self._revise(output, warnings) if not errors and warnings else None,
        )

    def _revise(self, output: GenerationOutput, warnings: list[str]) -> GenerationOutput:
        if not warnings:
            return output

        revised = output.model_copy(deep=True)
        diagnostics_tail = f"\nКонтроль покрытия: {len(warnings)} замечаний."
        if revised.text_overall:
            revised.text_overall += diagnostics_tail
        else:
            revised.text_overall = diagnostics_tail.strip()
        return revised
