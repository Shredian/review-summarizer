"""Страница проверки контекстных подсказок при написании отзыва (prepare / suggest / feedback)."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

import streamlit as st

root_path = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.container import Container
from src.domain.review_suggestions.source_hash import (
    compute_product_source_hash,
    compute_user_source_hash,
)
from src.presentation.streamlit.utils.async_utils import run_async
from src.utils.config import CONFIG


def _apply_suggestion_to_draft(draft: str, cursor: int, spec: dict) -> str:
    """Согласовано с API: append / replace_current_token (замена незавершённого слова)."""
    mode = spec.get("insert_mode") or "append"
    ins = str(spec.get("insert_text") or "")
    cur = max(0, min(int(cursor), len(draft)))
    before = draft[:cur]
    if mode == "replace_current_token":
        token_m = list(re.finditer(r"[\w\-]+", before, flags=re.UNICODE))
        if not token_m:
            return before + ins + draft[cur:]
        token_start = token_m[-1].start()
        return draft[:token_start] + ins + draft[cur:]
    if mode == "replace_suffix":
        return before + ins + draft[cur:]
    return before + ins + draft[cur:]


async def _load_products(limit: int = 200, offset: int = 0):
    app = Container.product_application()
    return await app.list_with_reviews_count(limit=limit, offset=offset)


async def _prepare(product_id: UUID, user_id: UUID | None, rating: float | None, field: str):
    app = Container.review_suggestion_application()
    return await app.prepare_context(
        product_id=product_id,
        user_id=user_id,
        rating=rating,
        field=field,
    )


async def _suggest(context_id: str, text: str, cursor: int, field: str, limit: int):
    app = Container.review_suggestion_application()
    return await app.suggest(
        context_id=context_id,
        current_text=text,
        cursor_position=cursor,
        field=field,
        limit=limit,
    )


async def _profile_status_snapshot(product_id: UUID, user_id: UUID | None) -> dict[str, Any]:
    """Срез БД по NLP-профилям: ждать worker или нет, без просмотра docker logs."""
    review_repo = Container.review_repository()
    prod_repo = Container.product_suggestion_profile_repository()
    user_prof_repo = Container.user_suggestion_profile_repository()

    reviews_p = await review_repo.list_by_product_unbounded(product_id)
    exp_ph = compute_product_source_hash(product_id, reviews_p)
    prow = await prod_repo.get_by_product_id(product_id)
    product_info: dict[str, Any] = {
        "reviews_in_db": len(reviews_p),
        "row_present": prow is not None,
        "status": prow.status if prow else None,
        "hash_matches_data": (prow.source_hash == exp_ph) if prow else False,
        "last_error": prow.last_error if prow else None,
        "built_at": prow.built_at.isoformat() if prow and prow.built_at else None,
    }
    out: dict[str, Any] = {"product": product_info, "user": None}
    if user_id is not None:
        reviews_u = await review_repo.list_by_user_unbounded(user_id)
        exp_uh = compute_user_source_hash(user_id, reviews_u)
        urow = await user_prof_repo.get_by_user_id(user_id)
        out["user"] = {
            "reviews_in_db": len(reviews_u),
            "row_present": urow is not None,
            "status": urow.status if urow else None,
            "hash_matches_data": (urow.source_hash == exp_uh) if urow else False,
            "last_error": urow.last_error if urow else None,
            "built_at": urow.built_at.isoformat() if urow and urow.built_at else None,
        }
    return out


async def _feedback(
    *,
    context_id: str,
    product_id: UUID,
    user_id: UUID | None,
    field: str,
    event_type: str,
    current_text_before: str | None,
    selected: str | None,
    current_text_after: str | None,
    suggestions_snapshot: list,
):
    app = Container.review_suggestion_application()
    await app.register_feedback(
        context_id=context_id,
        product_id=product_id,
        user_id=user_id,
        field=field,
        event_type=event_type,
        current_text_before=current_text_before,
        selected_suggestion=selected,
        current_text_after=current_text_after,
        suggestions=suggestions_snapshot,
    )


st.set_page_config(
    page_title="Подсказки отзыва",
    page_icon="✍️",
    layout="wide",
)

st.title("✍️ Подсказки при написании отзыва")
st.markdown(
    "Тестовая среда: **prepare** → ввод текста → **подсказки** и вставка. "
    "Тот же контур, что REST API (Container, БД, Redis)."
)

with st.sidebar:
    st.subheader("Ссылки")
    st.markdown(f"[Документация OpenAPI]({CONFIG.public_api_base_url.rstrip('/')}/docs)")
    st.caption(
        "В Docker при открытии UI с хоста укажите порты: Streamlit — :8501, API — :8000. "
        "Переменная `APP_PUBLIC_API_BASE_URL` задаёт ссылку на API в браузере."
    )
    st.subheader("Worker")
    st.info(
        "Чтобы профили товара и пользователя стали **ready** с богатыми фразами, "
        "должен работать сервис **`review_suggestions_worker`** в `docker-compose` "
        "(первый прогон может занять несколько минут из‑за загрузки моделей)."
    )
    st.caption(
        "Логи воркера (диагностика):  \n`docker logs review-summarizer-review-suggestions-worker --tail 80`"
    )

if "rs_product_id" not in st.session_state:
    st.session_state.rs_product_id = None
if "rs_user_id" not in st.session_state:
    st.session_state.rs_user_id = None
if "rs_context_id" not in st.session_state:
    st.session_state.rs_context_id = None
if "rs_field" not in st.session_state:
    st.session_state.rs_field = "comment"
if "rs_last_suggestions" not in st.session_state:
    st.session_state.rs_last_suggestions = []
if "rs_last_meta" not in st.session_state:
    st.session_state.rs_last_meta = None

if "rs_draft" not in st.session_state:
    st.session_state.rs_draft = ""

if "_rs_apply_suggestion" in st.session_state:
    _spec = st.session_state.pop("_rs_apply_suggestion")
    _cur = len(st.session_state.rs_draft)
    st.session_state.rs_draft = _apply_suggestion_to_draft(st.session_state.rs_draft, _cur, _spec)

try:
    products_with_counts = run_async(_load_products())
except Exception as e:
    st.error(f"Не удалось загрузить продукты: {e}")
    st.stop()

if not products_with_counts:
    st.warning("В базе нет продуктов. Добавьте продукт и отзывы на странице продуктов / импорте.")
    st.stop()

_sess_ctx = bool(st.session_state.rs_context_id)
with st.expander("⚙️ Параметры сессии и **prepare**", expanded=not _sess_ctx):
    product_choices = {f"{p.name} ({cnt} отз.)": p for p, cnt in products_with_counts}
    selected_label = st.selectbox("Продукт", options=list(product_choices.keys()))
    product = product_choices[selected_label]
    st.session_state.rs_product_id = product.id

    col_u, col_r, col_f = st.columns(3)
    with col_u:
        user_raw = st.text_input(
            "User ID (опционально)",
            placeholder="uuid или пусто",
            help="Если указан, подтянется профиль стиля пользователя (после worker).",
        )
    with col_r:
        use_rating = st.checkbox("Передать рейтинг в контекст", value=False)
        rating_val = (
            st.number_input("Рейтинг", min_value=0.0, max_value=5.0, value=4.0, step=0.5)
            if use_rating
            else None
        )
    with col_f:
        field = st.selectbox(
            "Поле отзыва",
            options=["comment", "plus", "minus", "title"],
            index=["comment", "plus", "minus", "title"].index(st.session_state.rs_field),
        )
        st.session_state.rs_field = field

    user_id = None
    if user_raw.strip():
        try:
            user_id = UUID(user_raw.strip())
        except ValueError:
            st.error("Некорректный UUID пользователя")
            st.stop()
    st.session_state.rs_user_id = user_id

    if st.checkbox("Показать статус профилей (БД)", value=False, key="rs_show_profile_status"):
        try:
            snap = run_async(_profile_status_snapshot(product.id, user_id))
        except Exception as e:
            st.warning(f"Не удалось прочитать статус: {e}")
            snap = None
        if snap:
            pi = snap["product"]
            st.markdown("**Товар**")
            if not pi["row_present"]:
                st.write("Записи профиля нет — после **prepare** задача уйдёт в Redis, воркер создаст строку.")
            else:
                st.write(f"- **status:** `{pi['status']}`")
                st.write(f"- **отзывов в БД по товару:** `{pi['reviews_in_db']}`")
                if pi["status"] == "ready":
                    st.write(
                        "- **hash совпадает с отзывами:** "
                        f"{'да' if pi['hash_matches_data'] else 'нет (нужна пересборка)'} "
                    )
                if pi["built_at"]:
                    st.caption(f"built_at: {pi['built_at']}")
                if pi.get("last_error"):
                    st.error(f"**last_error (воркер):** {pi['last_error']}")
            if user_id is not None and snap.get("user") is not None:
                ui = snap["user"]
                st.markdown("**Пользователь**")
                if not ui["row_present"]:
                    st.write("Записи профиля нет — воркер создаст после **prepare** с этим User ID.")
                else:
                    st.write(f"- **status:** `{ui['status']}`")
                    st.write(f"- **отзывов в БД у пользователя:** `{ui['reviews_in_db']}`")
                    if ui["status"] == "ready":
                        st.write(
                            "- **hash совпадает с отзывами:** "
                            f"{'да' if ui['hash_matches_data'] else 'нет (нужна пересборка)'} "
                        )
                    if ui["built_at"]:
                        st.caption(f"built_at: {ui['built_at']}")
                    if ui.get("last_error"):
                        st.error(f"**last_error (воркер):** {ui['last_error']}")

    if st.button("Подготовить контекст (**prepare**)", type="primary"):
        try:
            with st.spinner("Подготовка…"):
                res = run_async(
                    _prepare(
                        product.id,
                        user_id,
                        rating_val,
                        field,
                    )
                )
            st.session_state.rs_context_id = res["context_id"]
            st.success(
                f"**context_id:** `{res['context_id']}` · **status:** {res['status']} · "
                f"**fallback_used:** {res['fallback_used']} · **profile_status:** `{res['profile_status']}`"
            )
            if res.get("fallback_used"):
                ps = res.get("profile_status") or {}
                parts = []
                if ps.get("product_profile") == "pending":
                    parts.append(
                        "профиль **товара** ещё строится (дождитесь worker) или не совпадает с отзывами"
                    )
                if ps.get("user_profile") == "pending":
                    parts.append(
                        "профиль **пользователя** не готов — очистите **User ID**, если нужен только товар"
                    )
                hint = " ".join(parts) if parts else "профиль ещё не готов или устарел."
                st.info(f"Fallback: {hint} Затем снова **prepare**.")
        except Exception as e:
            st.error(f"Ошибка prepare: {e}")

    _cid = st.session_state.rs_context_id
    if _cid:
        st.caption(f"Текущий **context_id:** `{_cid}`")
    else:
        st.caption("Сначала выполните **prepare** выше.")

ctx_id = st.session_state.rs_context_id

st.markdown("### Демонстрация")
st.caption(
    "Подсказки запрашиваются так, как будто каретка **в конце** текста. "
    "Вставка учитывает режим с сервера (**replace** заменяет недописанное слово, **append** дописывает после курсора)."
)

demo_left, demo_right = st.columns([1.2, 1], gap="large")
with demo_left:
    draft = st.text_area(
        "Черновик отзыва",
        height=220,
        placeholder="Например введите начало слова…",
        key="rs_draft",
        label_visibility="visible",
    )
    _cursor_end = len(draft)
    if st.button("Получить подсказки", type="primary", use_container_width=True):
        if not ctx_id:
            st.warning("Нет context_id — сначала **prepare** в параметрах выше.")
        else:
            try:
                with st.spinner("Запрос подсказок…"):
                    out = run_async(
                        _suggest(
                            ctx_id,
                            draft,
                            _cursor_end,
                            field,
                            CONFIG.review_suggestions_max_suggestions,
                        )
                    )
                st.session_state.rs_last_suggestions = out.get("suggestions") or []
                st.session_state.rs_last_meta = out.get("metadata")
            except Exception as e:
                st.error(f"Ошибка suggest: {e}")

with demo_right:
    st.markdown("##### Подсказки")
    suggestions = st.session_state.rs_last_suggestions
    meta = st.session_state.rs_last_meta
    if meta:
        st.caption(
            f"latency **{meta.get('latency_ms')} ms**, fallback **{meta.get('fallback_used')}**"
        )
    if not suggestions:
        st.info("Запросите подсказки слева — здесь появятся варианты и кнопки вставки.")
    else:
        for i, s in enumerate(suggestions):
            disp = str(s.get("text") or s.get("insert_text") or "")
            mode = s.get("insert_mode") or "append"
            src = s.get("source") or "?"
            conf = float(s.get("confidence") or 0)
            st.markdown(f"**{disp}**  \n`{src}` · `{mode}` · conf {conf:.2f}")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Вставить", key=f"ins_{i}", use_container_width=True):
                    st.session_state["_rs_apply_suggestion"] = {
                        "insert_mode": mode,
                        "insert_text": str(s.get("insert_text") or s.get("text") or ""),
                    }
                    st.rerun()
            with b2:
                if st.button("accepted", key=f"acc_{i}", use_container_width=True):
                    if not ctx_id:
                        st.error("Нет context_id.")
                    else:
                        try:
                            _ins = str(s.get("insert_text") or s.get("text") or "")
                            _after = _apply_suggestion_to_draft(
                                draft,
                                len(draft),
                                {"insert_mode": mode, "insert_text": _ins},
                            )
                            run_async(
                                _feedback(
                                    context_id=ctx_id,
                                    product_id=product.id,
                                    user_id=user_id,
                                    field=field,
                                    event_type="accepted",
                                    current_text_before=draft,
                                    selected=_ins,
                                    current_text_after=_after,
                                    suggestions_snapshot=suggestions,
                                )
                            )
                            st.success("Событие accepted записано")
                        except Exception as e:
                            st.error(str(e))
            st.divider()

    with st.expander("Отладка: сырой ответ API"):
        if suggestions:
            st.json(
                {
                    "suggestions": suggestions,
                    "metadata": meta,
                }
            )
        else:
            st.caption("Пока нет последнего ответа suggest.")

st.markdown("---")
st.caption(
    "События пишутся в таблицу `review_suggestion_events`. "
    "Миграции Alembic выполняются при старте контейнеров (`alembic upgrade head` в entrypoint)."
)
