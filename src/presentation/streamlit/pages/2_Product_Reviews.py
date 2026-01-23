"""Страница просмотра отзывов продукта (UC-02)."""

import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

import streamlit as st

root_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(root_path))

from src.container import Container
from src.presentation.streamlit.utils.async_utils import run_async


async def load_products():
    app = Container.product_application()
    return await app.list(limit=1000)


async def load_reviews(
    product_id: UUID,
    source: str | None = None,
    rating_min: float | None = None,
    rating_max: float | None = None,
    limit: int = 100,
):
    app = Container.review_application()
    return await app.list_by_product(
        product_id=product_id,
        source=source if source != "Все" else None,
        rating_min=rating_min,
        rating_max=rating_max,
        limit=limit,
    )


async def load_sources(product_id: UUID):
    app = Container.review_application()
    return await app.get_sources_by_product(product_id)


async def load_stats(product_id: UUID):
    app = Container.review_application()
    return await app.get_stats_by_product(product_id)


st.set_page_config(page_title="Product Reviews", page_icon="💬", layout="wide")

st.title("💬 Отзывы продукта")

try:
    products = run_async(load_products())
    
    if not products:
        st.warning("Нет продуктов в базе данных")
        st.stop()
    
    # Выбор продукта
    product_options = {p.name: p for p in products}
    selected_name = st.selectbox("Выберите продукт", list(product_options.keys()))
    selected_product = product_options[selected_name]
    
    # Карточка продукта
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(selected_product.name)
        if selected_product.description:
            st.markdown(selected_product.description)
    
    # Статистика и фильтры
    stats = run_async(load_stats(selected_product.id))
    sources = run_async(load_sources(selected_product.id))
    
    with col2:
        st.metric("Всего отзывов", stats["count"])
        if stats["rating_avg"]:
            st.metric("Средний рейтинг", f"{stats['rating_avg']:.1f} ⭐")
    
    st.markdown("---")
    
    # Фильтры
    st.subheader("Фильтры")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        source_filter = st.selectbox("Источник", ["Все"] + sources)
    
    with col2:
        rating_min = st.number_input("Мин. рейтинг", min_value=0.0, max_value=5.0, value=0.0, step=0.5)
    
    with col3:
        rating_max = st.number_input("Макс. рейтинг", min_value=0.0, max_value=5.0, value=5.0, step=0.5)
    
    with col4:
        limit = st.selectbox("Показать", [25, 50, 100, 200], index=1)
    
    # Загружаем отзывы с фильтрами
    reviews = run_async(load_reviews(
        product_id=selected_product.id,
        source=source_filter if source_filter != "Все" else None,
        rating_min=rating_min if rating_min > 0 else None,
        rating_max=rating_max if rating_max < 5 else None,
        limit=limit,
    ))
    
    st.markdown("---")
    st.subheader(f"Отзывы ({len(reviews)})")
    
    if reviews:
        for review in reviews:
            with st.container():
                # Заголовок отзыва
                header_cols = st.columns([1, 2, 1, 1])
                with header_cols[0]:
                    if review.rating:
                        stars = "⭐" * int(review.rating)
                        st.markdown(f"**{review.rating}** {stars}")
                with header_cols[1]:
                    if review.title:
                        st.markdown(f"**{review.title}**")
                with header_cols[2]:
                    st.caption(f"📍 {review.source}")
                with header_cols[3]:
                    if review.review_date:
                        st.caption(review.review_date.strftime("%Y-%m-%d"))
                
                # Текст отзыва
                if review.comment:
                    st.markdown(review.comment)
                
                # Плюсы и минусы
                if review.plus or review.minus:
                    plus_minus_cols = st.columns(2)
                    with plus_minus_cols[0]:
                        if review.plus:
                            st.success(f"✅ **Плюсы:** {review.plus}")
                    with plus_minus_cols[1]:
                        if review.minus:
                            st.error(f"❌ **Минусы:** {review.minus}")
                
                # Ссылка на источник
                if review.url:
                    st.markdown(f"[🔗 Источник]({review.url})")
                
                st.markdown("---")
    else:
        st.info("Отзывы не найдены по заданным фильтрам")

except Exception as e:
    st.error(f"Ошибка при загрузке данных: {e}")
    st.info("Убедитесь, что база данных доступна и миграции выполнены")
