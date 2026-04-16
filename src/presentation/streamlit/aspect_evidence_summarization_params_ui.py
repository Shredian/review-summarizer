"""Виджеты Streamlit для параметров метода `aspect_evidence_guided_v1`."""

from __future__ import annotations

import streamlit as st

from src.infrastructure.services.summarization.aspect_evidence_guided.schemas import (
    AspectEvidenceGuidedParams,
)

ASPECT_EVIDENCE_GUIDED_METHOD_CODE = "aspect_evidence_guided_v1"

_SESSION_PREFIX = "aeg_ui_"
_PROFILE_KEY = "aeg_profile_choice"
_EMB_SOURCE_KEY = "aeg_emb_source"
_EMB_LIST_KEY = "aeg_emb_from_list"
_EMB_CUSTOM_KEY = "aeg_emb_custom_text"

_PROFILE_LABELS = ("Стандарт", "Максимум качества (KeyBERT + LLM)", "Без ML (шаблон, быстрее)")

_EMBEDDING_PRESETS: list[tuple[str, str]] = [
    ("paraphrase-multilingual-MiniLM-L12-v2 (рекомендуется)", "paraphrase-multilingual-MiniLM-L12-v2"),
    ("distiluse-base-multilingual-cased-v2", "distiluse-base-multilingual-cased-v2"),
    ("paraphrase-multilingual-mpnet-base-v2 (точнее, тяжелее)", "paraphrase-multilingual-mpnet-base-v2"),
]


def _defaults_for_profile(label: str) -> AspectEvidenceGuidedParams:
    if label == _PROFILE_LABELS[1]:
        return AspectEvidenceGuidedParams(enable_keybert_refinement=True, enable_llm_refinement=True)
    if label == _PROFILE_LABELS[2]:
        return AspectEvidenceGuidedParams(enable_keybert_refinement=False, enable_llm_refinement=False)
    return AspectEvidenceGuidedParams()


def _apply_profile_to_session(profile_label: str) -> None:
    data = _defaults_for_profile(profile_label).model_dump()
    for key, value in data.items():
        st.session_state[_SESSION_PREFIX + key] = value
    # синхронизировать выбор модели из списка
    emb = data["embedding_model_name"]
    ids = [p[1] for p in _EMBEDDING_PRESETS]
    if emb in ids:
        st.session_state[_EMB_LIST_KEY] = emb
    st.session_state[_EMB_CUSTOM_KEY] = emb


def _init_aeg_session_state() -> None:
    sample = AspectEvidenceGuidedParams().model_dump()
    for key, value in sample.items():
        sk = _SESSION_PREFIX + key
        if sk not in st.session_state:
            st.session_state[sk] = value
    if _PROFILE_KEY not in st.session_state:
        st.session_state[_PROFILE_KEY] = _PROFILE_LABELS[0]
    if _EMB_SOURCE_KEY not in st.session_state:
        st.session_state[_EMB_SOURCE_KEY] = "Из списка"
    ids = [p[1] for p in _EMBEDDING_PRESETS]
    if _EMB_LIST_KEY not in st.session_state:
        st.session_state[_EMB_LIST_KEY] = ids[0]
    if _EMB_CUSTOM_KEY not in st.session_state:
        st.session_state[_EMB_CUSTOM_KEY] = sample["embedding_model_name"]


def _on_profile_change() -> None:
    _apply_profile_to_session(st.session_state[_PROFILE_KEY])


def _embedding_model_value() -> str:
    if st.session_state[_EMB_SOURCE_KEY] == "Своя (Hugging Face id)":
        return (st.session_state.get(_EMB_CUSTOM_KEY) or "").strip() or AspectEvidenceGuidedParams().embedding_model_name
    return st.session_state[_EMB_LIST_KEY]


def render_aspect_evidence_guided_params() -> dict:
    """Рисует форму и возвращает dict для `params` (проверенный Pydantic)."""
    _init_aeg_session_state()

    st.markdown("**Параметры Aspect Evidence Guided**")

    st.selectbox(
        "Профиль",
        options=list(_PROFILE_LABELS),
        key=_PROFILE_KEY,
        on_change=_on_profile_change,
        help="«Максимум качества» включает KeyBERT и LLM-рефайнинг (нужны зависимости и APP_OPENAI_API_KEY для LLM).",
    )

    st.caption(
        "Текущий профиль подставляет значения ниже; их можно править вручную после выбора профиля."
    )

    with st.expander("Категория, сегментация и кандидаты", expanded=True):
        st.text_input("Категория товара (`category`)", key=_SESSION_PREFIX + "category")
        st.slider(
            "Макс. спанов на отзыв (`max_spans_per_review`)",
            3,
            200,
            key=_SESSION_PREFIX + "max_spans_per_review",
        )
        st.slider(
            "Мин. длина кандидата (`min_candidate_len`)",
            2,
            50,
            key=_SESSION_PREFIX + "min_candidate_len",
        )
        st.slider(
            "Макс. кандидатов аспектов (`max_candidates`)",
            10,
            1000,
            key=_SESSION_PREFIX + "max_candidates",
        )

    with st.expander("Планировщик и evidence", expanded=False):
        st.slider(
            "Мин. выбранных аспектов (`min_selected_aspects`)",
            2,
            20,
            key=_SESSION_PREFIX + "min_selected_aspects",
        )
        st.slider(
            "Макс. выбранных аспектов (`max_selected_aspects`)",
            3,
            30,
            key=_SESSION_PREFIX + "max_selected_aspects",
        )
        st.slider(
            "Фрагментов evidence на аспект (`evidence_per_aspect`)",
            1,
            10,
            key=_SESSION_PREFIX + "evidence_per_aspect",
        )
        st.slider(
            "Мин. упоминаний для «минорного» аспекта (`minority_aspect_min_mentions`)",
            1,
            30,
            key=_SESSION_PREFIX + "minority_aspect_min_mentions",
        )
        st.slider(
            "Порог редкости доли (`rarity_share_threshold`)",
            0.01,
            0.5,
            0.01,
            key=_SESSION_PREFIX + "rarity_share_threshold",
        )

    with st.expander("Веса скоринга (0–1)", expanded=False):
        st.slider("Превалентность (`prevalence_weight`)", 0.0, 1.0, 0.05, key=_SESSION_PREFIX + "prevalence_weight")
        st.slider("Полярность (`polarity_weight`)", 0.0, 1.0, 0.05, key=_SESSION_PREFIX + "polarity_weight")
        st.slider(
            "Информативность (`informativeness_weight`)",
            0.0,
            1.0,
            0.05,
            key=_SESSION_PREFIX + "informativeness_weight",
        )
        st.slider("Разнообразие (`diversity_weight`)", 0.0, 1.0, 0.05, key=_SESSION_PREFIX + "diversity_weight")
        st.slider("Бонус редкости (`rarity_bonus`)", 0.0, 1.0, 0.05, key=_SESSION_PREFIX + "rarity_bonus")

    with st.expander("Эмбеддинги и LLM", expanded=True):
        st.radio(
            "Как задать модель эмбеддингов (`embedding_model_name`)",
            ["Из списка", "Своя (Hugging Face id)"],
            horizontal=True,
            key=_EMB_SOURCE_KEY,
        )
        if st.session_state[_EMB_SOURCE_KEY] == "Из списка":
            st.selectbox(
                "Предобученная модель",
                options=[p[1] for p in _EMBEDDING_PRESETS],
                format_func=lambda mid: next(l for l, m in _EMBEDDING_PRESETS if m == mid),
                key=_EMB_LIST_KEY,
            )
        else:
            st.text_input(
                "Полное имя модели (например paraphrase-multilingual-MiniLM-L12-v2)",
                key=_EMB_CUSTOM_KEY,
            )

        st.toggle("KeyBERT (`enable_keybert_refinement`)", key=_SESSION_PREFIX + "enable_keybert_refinement")
        st.toggle(
            "LLM-рефайнинг (`enable_llm_refinement`, нужен APP_OPENAI_API_KEY)",
            key=_SESSION_PREFIX + "enable_llm_refinement",
        )
        st.slider(
            "Предложений в overall при LLM (`llm_overall_sentences`)",
            2,
            12,
            key=_SESSION_PREFIX + "llm_overall_sentences",
        )

    raw: dict = {}
    for field in AspectEvidenceGuidedParams.model_fields:
        if field == "embedding_model_name":
            raw[field] = _embedding_model_value()
        else:
            raw[field] = st.session_state[_SESSION_PREFIX + field]

    try:
        validated = AspectEvidenceGuidedParams.model_validate(raw)
    except Exception as e:
        st.error(f"Параметры не прошли проверку: {e}")
        raise
    result = validated.model_dump()
    with st.expander("Итоговый JSON параметров", expanded=False):
        st.json(result)
    return result
