"""Страница генерации суммаризации (UC-03)."""

import json
import sys
from pathlib import Path
from uuid import UUID

import streamlit as st

root_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(root_path))

from src.container import Container
from src.presentation.streamlit.aspect_evidence_summarization_params_ui import (
    ASPECT_EVIDENCE_GUIDED_METHOD_CODE,
    render_aspect_evidence_guided_params,
)
from src.presentation.streamlit.utils.async_utils import run_async
from src.presentation.streamlit.utils.key_phrases_ui import bucket_key_phrases
from src.presentation.streamlit.utils.product_choices import (
    build_product_choice_map,
    load_products_with_review_counts,
)


async def load_reviews_count(product_id: UUID):
    app = Container.review_application()
    return await app.count_by_product(product_id)


async def generate_summary(product_id: UUID, method: str, params: dict):
    app = Container.summary_application()
    return await app.generate(
        product_id=product_id,
        method_code=method,
        params=params,
    )


def get_available_methods():
    app = Container.summary_application()
    return app.get_available_methods()


def get_method_info(method_code: str):
    app = Container.summary_application()
    return app.get_method_info(method_code)


st.set_page_config(page_title="Summarization", page_icon="✨", layout="wide")

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

st.title("✨ Генерация суммаризации")

try:
    pairs = run_async(load_products_with_review_counts(limit=1000, offset=0))

    if not pairs:
        st.warning("Нет продуктов в базе данных")
        st.stop()

    choice_map = build_product_choice_map(pairs)
    count_by_product_id = {p.id: c for p, c in pairs}

    selected_label = st.selectbox("Выберите продукт", list(choice_map.keys()))
    selected_product = choice_map[selected_label]

    reviews_count = count_by_product_id.get(selected_product.id, 0)
    if reviews_count == 0 and selected_product.id is not None:
        reviews_count = run_async(load_reviews_count(selected_product.id))

    if reviews_count == 0:
        st.warning("У этого продукта нет отзывов. Суммаризация невозможна.")
        st.stop()

    st.markdown("---")

    # Выбор метода суммаризации
    st.subheader("Настройки суммаризации")

    col1, col2 = st.columns([1, 2])

    with col1:
        methods = get_available_methods()
        selected_method = st.selectbox("Метод суммаризации", methods)

        # Информация о методе
        if selected_method:
            method_info = get_method_info(selected_method)
            st.caption(f"**{method_info['name']}**")
            st.caption(f"Версия: {method_info['version']}")
            if method_info["description"]:
                st.caption(method_info["description"])

    with col2:
        if selected_method == ASPECT_EVIDENCE_GUIDED_METHOD_CODE:
            params_for_run = render_aspect_evidence_guided_params()
            params_json = None
        else:
            st.markdown("**Параметры метода (JSON)**")
            default_params = {
                "output_type": "structured",
            }
            params_json = st.text_area(
                "Параметры",
                value=json.dumps(default_params, indent=2, ensure_ascii=False),
                height=150,
                help="Параметры передаются методу суммаризации. output_type: 'structured' (pros/cons/neutral) или 'overall' (единый текст)",
            )
            params_for_run = None

    st.markdown("---")

    # Кнопка генерации
    if st.button("🚀 Сгенерировать суммаризацию", type="primary", use_container_width=True):
        try:
            # Параметры: форма AEG или JSON для остальных методов
            try:
                if selected_method == ASPECT_EVIDENCE_GUIDED_METHOD_CODE:
                    params = params_for_run if params_for_run is not None else {}
                else:
                    params = json.loads(params_json) if params_json and params_json.strip() else {}
            except json.JSONDecodeError as e:
                st.error(f"Ошибка в JSON параметрах: {e}")
                st.stop()

            with st.spinner("Генерация суммаризации..."):
                summary = run_async(
                    generate_summary(
                        product_id=selected_product.id,
                        method=selected_method,
                        params=params,
                    )
                )

            st.success("✅ Суммаризация успешно сгенерирована!")

            # Отображение результата
            st.markdown("---")
            st.subheader("Результат суммаризации")

            # Метаданные
            meta_cols = st.columns(4)
            with meta_cols[0]:
                st.metric("Отзывов обработано", summary.reviews_count)
            with meta_cols[1]:
                if summary.rating_avg:
                    st.metric("Средний рейтинг", f"{summary.rating_avg:.1f}")
            with meta_cols[2]:
                st.caption(f"Метод: {summary.method}")
            with meta_cols[3]:
                st.caption(f"ID: {str(summary.id)[:8]}...")

            st.markdown("---")

            # Общий текст (если есть)
            if summary.has_overall_summary():
                st.markdown("### 📝 Общее резюме")
                st.markdown(
                    f'<div class="summary-text">{summary.text_overall}</div>',
                    unsafe_allow_html=True,
                )

            # Структурированный результат (если есть)
            if summary.has_structured_summary():
                result_cols = st.columns(3)

                with result_cols[0]:
                    st.markdown("### 📋 Нейтральное резюме")
                    if summary.text_neutral:
                        st.markdown(
                            f'<div class="summary-text neutral">{summary.text_neutral}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.caption("Не заполнено")

                with result_cols[1]:
                    st.markdown("### ✅ Плюсы")
                    if summary.text_pros:
                        # Разбиваем текст на предложения и выделяем положительные моменты
                        pros_text = summary.text_pros.replace("\n", "<br>")
                        st.markdown(
                            f'<div class="summary-text" style="background-color: #e8f5e9; border-left: 4px solid #09ab3b;">'
                            f'<span class="positive">{pros_text}</span></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.caption("Не заполнено")

                with result_cols[2]:
                    st.markdown("### ❌ Минусы")
                    if summary.text_cons:
                        # Разбиваем текст на предложения и выделяем отрицательные моменты
                        cons_text = summary.text_cons.replace("\n", "<br>")
                        st.markdown(
                            f'<div class="summary-text" style="background-color: #ffebee; border-left: 4px solid #ff2b2b;">'
                            f'<span class="negative">{cons_text}</span></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.caption("Не заполнено")

            # Ключевые фразы (если есть)
            if summary.has_key_phrases():
                st.markdown("---")
                st.markdown("### 🔑 Ключевые фразы")

                positive_phrases, negative_phrases, neutral_phrases, other_phrases = (
                    bucket_key_phrases(summary.key_phrases)
                )

                if positive_phrases or negative_phrases or neutral_phrases:
                    phrase_cols = st.columns(3)

                    with phrase_cols[0]:
                        if positive_phrases:
                            st.markdown("#### ✅ Положительные")
                            for kp in sorted(positive_phrases, key=lambda x: x.count, reverse=True)[
                                :10
                            ]:
                                share_text = f" ({kp.share * 100:.1f}%)" if kp.share else ""
                                st.markdown(
                                    f'<span class="positive">• {kp.phrase}</span> '
                                    f"<small>({kp.count}{share_text})</small>",
                                    unsafe_allow_html=True,
                                )

                    with phrase_cols[1]:
                        if negative_phrases:
                            st.markdown("#### ❌ Отрицательные")
                            for kp in sorted(negative_phrases, key=lambda x: x.count, reverse=True)[
                                :10
                            ]:
                                share_text = f" ({kp.share * 100:.1f}%)" if kp.share else ""
                                st.markdown(
                                    f'<span class="negative">• {kp.phrase}</span> '
                                    f"<small>({kp.count}{share_text})</small>",
                                    unsafe_allow_html=True,
                                )

                    with phrase_cols[2]:
                        if neutral_phrases:
                            st.markdown("#### ⚪ Нейтральные")
                            for kp in sorted(neutral_phrases, key=lambda x: x.count, reverse=True)[
                                :10
                            ]:
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
                                f"• **{kp.phrase}** — `{kp.sentiment}` ({kp.count}{share_text})"
                            )

                with st.expander("📊 Полная таблица ключевых фраз"):
                    phrases_data = []
                    for kp in summary.key_phrases:
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

        except ValueError as e:
            st.error(f"Ошибка: {e}")
        except Exception as e:
            st.error(f"Ошибка при генерации: {e}")

except Exception as e:
    st.error(f"Ошибка при загрузке данных: {e}")
    st.info("Убедитесь, что база данных доступна и миграции выполнены")
