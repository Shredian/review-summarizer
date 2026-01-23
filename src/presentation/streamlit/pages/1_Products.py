"""Страница просмотра списка продуктов (UC-01)."""

import sys
from pathlib import Path

import streamlit as st

root_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(root_path))

from src.container import Container
from src.presentation.streamlit.utils.async_utils import run_async


async def load_products(limit: int = 100, offset: int = 0):
    app = Container.product_application()
    return await app.list_with_reviews_count(limit=limit, offset=offset)


async def get_products_count():
    app = Container.product_application()
    return await app.count()


st.set_page_config(page_title="Products", page_icon="📦", layout="wide")

st.title("📦 Продукты")
st.markdown("Список всех продуктов с количеством отзывов")

# Фильтры и пагинация
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input("🔍 Поиск по названию", placeholder="Введите название продукта...")

with col2:
    page_size = st.selectbox("Записей на странице", [10, 25, 50, 100], index=1)

# Получаем данные
try:
    total_count = run_async(get_products_count())
    products_with_counts = run_async(load_products(limit=page_size))
    
    # Фильтрация по поисковому запросу (клиентская)
    if search_query:
        products_with_counts = [
            (p, c) for p, c in products_with_counts
            if search_query.lower() in p.name.lower()
        ]
    
    st.markdown(f"**Всего продуктов:** {total_count}")
    
    if products_with_counts:
        # Формируем данные для таблицы
        table_data = []
        for product, reviews_count in products_with_counts:
            table_data.append({
                "ID": str(product.id)[:8] + "...",
                "Название": product.name,
                "Описание": (product.description or "")[:100] + ("..." if product.description and len(product.description) > 100 else ""),
                "Отзывов": reviews_count,
                "Создан": product.created_at.strftime("%Y-%m-%d %H:%M") if product.created_at else "-",
            })
        
        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.TextColumn("ID", width="small"),
                "Название": st.column_config.TextColumn("Название", width="medium"),
                "Описание": st.column_config.TextColumn("Описание", width="large"),
                "Отзывов": st.column_config.NumberColumn("Отзывов", width="small"),
                "Создан": st.column_config.TextColumn("Создан", width="small"),
            },
        )
        
        # Детальный просмотр продукта
        st.markdown("---")
        st.subheader("Детали продукта")
        
        product_names = [p.name for p, _ in products_with_counts]
        selected_name = st.selectbox("Выберите продукт для просмотра", product_names)
        
        if selected_name:
            selected_product = next(
                (p for p, _ in products_with_counts if p.name == selected_name),
                None
            )
            if selected_product:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**ID:** `{selected_product.id}`")
                    st.markdown(f"**Название:** {selected_product.name}")
                with col2:
                    st.markdown(f"**Создан:** {selected_product.created_at}")
                    st.markdown(f"**Обновлён:** {selected_product.updated_at}")
                
                if selected_product.description:
                    st.markdown("**Описание:**")
                    st.text(selected_product.description)
                
                st.info(f"💡 Перейдите на страницу **Product Reviews**, чтобы посмотреть отзывы этого продукта")
    else:
        st.info("Продукты не найдены")

except Exception as e:
    st.error(f"Ошибка при загрузке данных: {e}")
    st.info("Убедитесь, что база данных доступна и миграции выполнены")
