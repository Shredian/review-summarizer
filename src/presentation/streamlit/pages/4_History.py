"""Страница истории суммаризаций (UC-04)."""

import sys
from pathlib import Path
from uuid import UUID

import streamlit as st

root_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(root_path))

from src.container import Container
from src.presentation.streamlit.utils.async_utils import run_async
from src.presentation.streamlit.utils.key_phrases_ui import bucket_key_phrases
from src.presentation.streamlit.utils.product_choices import (
    build_product_choice_map,
    load_products_with_review_counts,
)


async def load_summaries_by_product(product_id: UUID, limit: int = 50):
    app = Container.summary_application()
    return await app.list_by_product(product_id=product_id, limit=limit)


def _product_name_map(pairs: list) -> dict[UUID, str]:
    out: dict[UUID, str] = {}
    for product, _cnt in pairs:
        if product.id is not None:
            out[product.id] = product.name
    return out


def _summary_choice_labels(summaries: list, pid_to_name: dict[UUID, str]) -> dict[str, object]:
    labels: dict[str, object] = {}
    for s in summaries:
        pname = pid_to_name.get(s.product_id, "—")
        dt = s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "—"
        label = f"{pname} · {s.method} · {dt} · `{str(s.id)[:8]}`"
        candidate = label
        n = 1
        while candidate in labels:
            n += 1
            candidate = f"{label} ({n})"
        labels[candidate] = s
    return labels


st.set_page_config(page_title="History", page_icon="📜", layout="wide")

st.markdown(
    """
    <style>
    .positive { color: #09ab3b; font-weight: bold; }
    .negative { color: #ff2b2b; font-weight: bold; }
    .neutral { color: #666666; }
    .summary-text {
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        line-height: 1.6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📜 История суммаризаций")

try:
    pairs = run_async(load_products_with_review_counts(limit=1000, offset=0))
    if not pairs:
        st.warning("Нет продуктов в базе данных")
        st.stop()

    pid_to_name = _product_name_map(pairs)
    scope_options: dict[str, UUID | None] = {"Все продукты": None}
    for label, prod in build_product_choice_map(pairs).items():
        scope_options[label] = prod.id

    scope_keys = list(scope_options.keys())
    selected_scope = st.selectbox("Фильтр по продукту", scope_keys)
    selected_pid = scope_options[selected_scope]

    if selected_pid:
        summaries = run_async(load_summaries_by_product(selected_pid))
    else:
        app = Container.summary_application()
        summaries = run_async(app.list(limit=100))

    if not summaries:
        st.info("История суммаризаций пуста")
        st.stop()

    st.caption(f"Найдено записей: **{len(summaries)}**")

    left_col, right_col = st.columns([1.65, 1], gap="large")

    with left_col:
        table_data = []
        for s in summaries:
            product_name = pid_to_name.get(s.product_id, "—")
            table_data.append(
                {
                    "Продукт": product_name[:48] + ("…" if len(product_name) > 48 else ""),
                    "Метод": s.method,
                    "Отзывов": s.reviews_count,
                    "Дата": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "—",
                }
            )
        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Продукт": st.column_config.TextColumn("Продукт", width="large"),
                "Метод": st.column_config.TextColumn("Метод", width="medium"),
                "Отзывов": st.column_config.NumberColumn("Отзывов", width="small"),
                "Дата": st.column_config.TextColumn("Дата", width="medium"),
            },
        )

        summary_map = _summary_choice_labels(summaries, pid_to_name)
        selected_summary_key = st.selectbox("Запись", list(summary_map.keys()))
        selected_summary = summary_map[selected_summary_key]

    with right_col:
        st.subheader("Метаданные")
        st.markdown(f"**ID:** `{selected_summary.id}`")
        st.markdown(
            f"**Метод:** {selected_summary.method} ({selected_summary.method_version or '—'})"
        )
        st.markdown(f"**Отзывов:** {selected_summary.reviews_count}")
        st.markdown(f"**Дата:** {selected_summary.created_at}")
        ra = selected_summary.rating_avg
        st.markdown(f"**Средний рейтинг (вход):** {ra:.1f}" if ra is not None else "**Средний рейтинг:** —")
        if selected_summary.params:
            with st.expander("Параметры генерации"):
                st.json(selected_summary.params)
        with st.expander("Диапазон дат отзывов"):
            st.caption(
                f"min: {selected_summary.date_min.strftime('%Y-%m-%d') if selected_summary.date_min else '—'}"
            )
            st.caption(
                f"max: {selected_summary.date_max.strftime('%Y-%m-%d') if selected_summary.date_max else '—'}"
            )

    st.divider()
    st.subheader("Результат")

    if selected_summary.has_overall_summary():
        st.markdown("### Общее резюме")
        st.markdown(
            f'<div class="summary-text">{selected_summary.text_overall}</div>',
            unsafe_allow_html=True,
        )

    if selected_summary.has_structured_summary():
        result_cols = st.columns(3)

        with result_cols[0]:
            st.markdown("### Нейтральное")
            if selected_summary.text_neutral:
                st.markdown(
                    f'<div class="summary-text neutral">{selected_summary.text_neutral}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Не заполнено")

        with result_cols[1]:
            st.markdown("### Плюсы")
            if selected_summary.text_pros:
                pros_text = selected_summary.text_pros.replace("\n", "<br>")
                st.markdown(
                    f'<div class="summary-text" style="background-color: #e8f5e9; border-left: 4px solid #09ab3b;">'
                    f'<span class="positive">{pros_text}</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Не заполнено")

        with result_cols[2]:
            st.markdown("### Минусы")
            if selected_summary.text_cons:
                cons_text = selected_summary.text_cons.replace("\n", "<br>")
                st.markdown(
                    f'<div class="summary-text" style="background-color: #ffebee; border-left: 4px solid #ff2b2b;">'
                    f'<span class="negative">{cons_text}</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Не заполнено")

    if selected_summary.has_key_phrases():
        st.markdown("---")
        st.markdown("### Ключевые фразы")

        positive_phrases, negative_phrases, neutral_phrases, other_phrases = bucket_key_phrases(
            selected_summary.key_phrases
        )

        if positive_phrases or negative_phrases or neutral_phrases:
            phrase_cols = st.columns(3)

            with phrase_cols[0]:
                if positive_phrases:
                    st.markdown("#### Положительные")
                    for kp in sorted(positive_phrases, key=lambda x: x.count, reverse=True)[:10]:
                        share_text = f" ({kp.share * 100:.1f}%)" if kp.share else ""
                        st.markdown(
                            f'<span class="positive">• {kp.phrase}</span> '
                            f"<small>({kp.count}{share_text})</small>",
                            unsafe_allow_html=True,
                        )

            with phrase_cols[1]:
                if negative_phrases:
                    st.markdown("#### Отрицательные")
                    for kp in sorted(negative_phrases, key=lambda x: x.count, reverse=True)[:10]:
                        share_text = f" ({kp.share * 100:.1f}%)" if kp.share else ""
                        st.markdown(
                            f'<span class="negative">• {kp.phrase}</span> '
                            f"<small>({kp.count}{share_text})</small>",
                            unsafe_allow_html=True,
                        )

            with phrase_cols[2]:
                if neutral_phrases:
                    st.markdown("#### Нейтральные")
                    for kp in sorted(neutral_phrases, key=lambda x: x.count, reverse=True)[:10]:
                        share_text = f" ({kp.share * 100:.1f}%)" if kp.share else ""
                        st.markdown(
                            f'<span class="neutral">• {kp.phrase}</span> '
                            f"<small>({kp.count}{share_text})</small>",
                            unsafe_allow_html=True,
                        )

        if other_phrases:
            with st.expander("Другие значения тональности"):
                for kp in sorted(other_phrases, key=lambda x: x.count, reverse=True):
                    share_text = f" ({kp.share * 100:.1f}%)" if kp.share else ""
                    st.markdown(
                        f"• **{kp.phrase}** — `{kp.sentiment}` ({kp.count}{share_text})",
                        unsafe_allow_html=False,
                    )

        with st.expander("Полная таблица ключевых фраз"):
            phrases_data = []
            for kp in selected_summary.key_phrases:
                raw = kp.sentiment
                sentiment_emoji = {
                    "positive": "🟢",
                    "negative": "🔴",
                    "neutral": "⚪",
                }.get((raw or "").strip().lower(), "❔")

                phrases_data.append(
                    {
                        "Фраза": kp.phrase,
                        "Тональность": f"{sentiment_emoji} {raw}",
                        "Упоминаний": kp.count,
                        "Доля": f"{kp.share * 100:.1f}%" if kp.share else "-",
                    }
                )

            st.dataframe(phrases_data, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Ошибка при загрузке данных: {e}")
    st.info("Убедитесь, что база данных доступна и миграции выполнены")
