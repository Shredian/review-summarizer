"""Страница просмотра списка продуктов (UC-01)."""

import sys
from pathlib import Path

import streamlit as st

root_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(root_path))

from src.container import Container
from src.presentation.streamlit.utils.async_utils import run_async
from src.presentation.streamlit.utils.product_choices import build_product_choice_map


async def load_products_page(limit: int, offset: int):
    app = Container.product_application()
    return await app.list_with_reviews_count(limit=limit, offset=offset)


async def get_products_count():
    app = Container.product_application()
    return await app.count()


st.set_page_config(page_title="Products", page_icon="📦", layout="wide")

st.title("📦 Продукты")

col_f1, col_f2, col_f3, col_f4 = st.columns([2, 1, 1, 1])
with col_f1:
    search_query = st.text_input("Поиск по названию", placeholder="Часть названия…")
with col_f2:
    page_size = st.selectbox("На странице", [10, 25, 50, 100], index=1)
with col_f3:
    sort_by = st.selectbox(
        "Сортировка",
        ["По названию", "По отзывам ↓", "По отзывам ↑", "По дате создания ↓"],
    )
with col_f4:
    min_reviews = st.number_input("Мин. отзывов", min_value=0, value=0, step=1)

try:
    total_count = run_async(get_products_count())
    page_count = max(1, (total_count + page_size - 1) // page_size)
    page_nr = st.number_input(
        "Страница",
        min_value=1,
        max_value=max(1, page_count),
        value=1,
        step=1,
    )
    offset = (int(page_nr) - 1) * page_size

    products_with_counts = run_async(load_products_page(limit=page_size, offset=offset))

    filtered = [(p, c) for p, c in products_with_counts if c >= min_reviews]
    if search_query:
        q = search_query.lower()
        filtered = [(p, c) for p, c in filtered if q in p.name.lower()]

    if sort_by == "По названию":
        filtered.sort(key=lambda x: x[0].name.lower())
    elif sort_by == "По отзывам ↓":
        filtered.sort(key=lambda x: x[1], reverse=True)
    elif sort_by == "По отзывам ↑":
        filtered.sort(key=lambda x: x[1])
    elif sort_by == "По дате создания ↓":
        filtered.sort(key=lambda x: x[0].created_at or x[0].updated_at, reverse=True)

    st.caption(
        f"Всего продуктов в базе: **{total_count}**. Поиск и фильтры ниже действуют в пределах загруженной страницы ({page_size} записей)."
    )

    main_col, side_col = st.columns([1.6, 1], gap="large")

    with main_col:
        if filtered:
            table_data = []
            for product, reviews_count in filtered:
                desc = product.description or ""
                short = (desc[:120] + "…") if len(desc) > 120 else desc
                table_data.append(
                    {
                        "Название": product.name,
                        "Отзывов": reviews_count,
                        "Описание": short or "—",
                    }
                )
            st.dataframe(
                table_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Название": st.column_config.TextColumn("Название", width="medium"),
                    "Отзывов": st.column_config.NumberColumn("Отзывов", width="small"),
                    "Описание": st.column_config.TextColumn("Описание", width="large"),
                },
            )
        else:
            st.info("На этой странице нет записей по фильтрам.")

    with side_col:
        st.subheader("Подробнее")
        if filtered:
            detail_map = build_product_choice_map(filtered)
            detail_labels = list(detail_map.keys())
            selected_label = st.selectbox("Продукт", detail_labels)
            sel = detail_map[selected_label]
            st.markdown(f"**{sel.name}**")
            st.caption(f"ID: `{sel.id}`")
            st.caption(f"Создан: {sel.created_at}")
            st.caption(f"Обновлён: {sel.updated_at}")
            if sel.description:
                st.markdown(sel.description)
            st.page_link("pages/2_Product_Reviews.py", label="Открыть отзывы →")
        else:
            st.caption("Выберите страницу с данными.")

except Exception as e:
    st.error(f"Ошибка при загрузке данных: {e}")
    st.info("Убедитесь, что база данных доступна и миграции выполнены")
