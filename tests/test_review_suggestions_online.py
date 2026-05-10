import uuid

from src.domain.review_suggestions.entities import SuggestionCandidate, TextInputState
from src.infrastructure.review_suggestions.online.generators import PrefixCandidateGenerator
from src.infrastructure.review_suggestions.online.ranking import rank_candidates
from src.infrastructure.review_suggestions.online.safety_filter import SuggestionSafetyFilter


def _state(field: str = "comment", rating: float | None = None) -> TextInputState:
    return TextInputState(
        raw_text="x",
        text_before_cursor="",
        current_token=None,
        last_surface_tokens=[],
        last_lemmas=[],
        is_empty=True,
        ends_with_space=False,
        field=field,
        rating=rating,
    )


def test_safety_filter_removes_price_like() -> None:
    f = SuggestionSafetyFilter()
    st = _state()
    bad = SuggestionCandidate(
        id="1",
        text="купил за 4990 рублей",
        insert_text="купил за 4990 рублей",
        type="phrase_completion",
        insert_mode="append",
        aspect_id=None,
        aspect_label=None,
        confidence=0.5,
        source="x",
    )
    good = SuggestionCandidate(
        id="2",
        text="по ощущениям",
        insert_text="по ощущениям",
        type="generic_fallback",
        insert_mode="append",
        aspect_id=None,
        aspect_label=None,
        confidence=0.5,
        source="generic",
    )
    out = f.filter([bad, good], st)
    assert len(out) == 1
    assert "по ощущениям" in out[0].insert_text


def test_prefix_replace_when_insert_extends_partial_token() -> None:
    """Частичный ввод («хор») + слово из банка («хороший»): replace токена, не append."""
    state = TextInputState(
        raw_text="хор",
        text_before_cursor="хор",
        current_token="хор",
        last_surface_tokens=["хор"],
        last_lemmas=["хор"],
        is_empty=False,
        ends_with_space=False,
        field="comment",
        rating=None,
    )
    profile = {
        "prefix_index": {
            "хор": [
                {
                    "text": "совсем хороший",
                    "insert_text": "хороший",
                    "score": 0.8,
                }
            ]
        }
    }
    out = PrefixCandidateGenerator().generate(state, profile)
    assert len(out) == 1
    assert out[0].insert_mode == "replace_current_token"
    assert out[0].insert_text == "хороший"


def test_ranking_boosts_positive_for_plus_field() -> None:
    st = _state(field="plus")
    pos = SuggestionCandidate(
        id=str(uuid.uuid4()),
        text="отлично",
        insert_text="отлично",
        type="phrase_completion",
        insert_mode="append",
        aspect_id=None,
        aspect_label=None,
        confidence=0.5,
        source="ngram",
        sentiment_score=0.4,
        metadata={"weak_sentiment": "positive"},
    )
    neg = SuggestionCandidate(
        id=str(uuid.uuid4()),
        text="плохо",
        insert_text="плохо",
        type="phrase_completion",
        insert_mode="append",
        aspect_id=None,
        aspect_label=None,
        confidence=0.5,
        source="ngram",
        sentiment_score=0.4,
        metadata={"weak_sentiment": "negative"},
    )
    ranked = rank_candidates([neg, pos], st, max_n=2)
    assert ranked[0].metadata.get("weak_sentiment") == "positive"
