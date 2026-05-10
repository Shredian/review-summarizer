from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from src.container import Container

router = APIRouter(tags=["Review suggestions"], prefix="/review-suggestions")


class PrepareRequest(BaseModel):
    product_id: UUID
    user_id: UUID | None = None
    rating: float | None = Field(None, ge=0, le=5)
    field: str = Field(..., pattern="^(title|plus|minus|comment)$")


class PrepareResponse(BaseModel):
    context_id: str
    status: str
    fallback_used: bool
    profile_status: dict[str, str]


class SuggestRequest(BaseModel):
    context_id: str
    current_text: str
    cursor_position: int = Field(..., ge=0)
    field: str = Field(..., pattern="^(title|plus|minus|comment)$")
    limit: int = Field(3, ge=1, le=10)


class SuggestionItem(BaseModel):
    id: str
    text: str
    insert_text: str
    type: str
    insert_mode: str
    aspect_id: str | None = None
    aspect_label: str | None = None
    confidence: float
    source: str


class SuggestResponse(BaseModel):
    context_id: str
    suggestions: list[SuggestionItem]
    metadata: dict[str, Any]


class FeedbackRequest(BaseModel):
    context_id: str
    product_id: UUID
    user_id: UUID | None = None
    field: str = Field(..., pattern="^(title|plus|minus|comment)$")
    event_type: str = Field(..., pattern="^(shown|accepted|ignored|edited|dismissed)$")
    current_text_before: str | None = None
    selected_suggestion: str | None = None
    current_text_after: str | None = None
    suggestions: list[Any] | None = None


@router.post("/prepare", response_model=PrepareResponse)
async def prepare_review_suggestions(body: PrepareRequest) -> PrepareResponse:
    app = Container.review_suggestion_application()
    data = await app.prepare_context(
        product_id=body.product_id,
        user_id=body.user_id,
        rating=body.rating,
        field=body.field,
    )
    return PrepareResponse(**data)


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_review_continuations(body: SuggestRequest) -> SuggestResponse:
    app = Container.review_suggestion_application()
    data = await app.suggest(
        context_id=body.context_id,
        current_text=body.current_text,
        cursor_position=body.cursor_position,
        field=body.field,
        limit=body.limit,
    )
    items = [SuggestionItem(**s) for s in data.get("suggestions", [])]
    return SuggestResponse(
        context_id=data["context_id"],
        suggestions=items,
        metadata=data.get("metadata") or {},
    )


@router.post(
    "/feedback",
    status_code=204,
    response_class=Response,
    response_model=None,
)
async def feedback_review_suggestions(body: FeedbackRequest) -> Response:
    app = Container.review_suggestion_application()
    await app.register_feedback(
        context_id=body.context_id,
        product_id=body.product_id,
        user_id=body.user_id,
        field=body.field,
        event_type=body.event_type,
        current_text_before=body.current_text_before,
        selected_suggestion=body.selected_suggestion,
        current_text_after=body.current_text_after,
        suggestions=body.suggestions,
    )
    return Response(status_code=204)
