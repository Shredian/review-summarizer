"""Страница истории суммаризаций (UC-04)."""

import sys
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


async def load_summaries_by_product(product_id: UUID, limit: int = 50):
    app = Container.summary_application()
    return await app.list_by_product(product_id=product_id, limit=limit)


async def load_summary(summary_id: UUID):
    app = Container.summary_application()
    return await app.get(summary_id)


st.set_page_config(page_title="History", page_icon="📜", layout="wide")

# Добавляем CSS стили для красивого отображения
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
    # Загружаем список продуктов
    products = run_async(load_products())
    
    if not products:
        st.warning("Нет продуктов в базе данных")
        st.stop()
    
    # Выбор продукта
    product_options = {"Все продукты": None}
    product_options.update({p.name: p for p in products})
    
    selected_name = st.selectbox("Фильтр по продукту", list(product_options.keys()))
    selected_product = product_options[selected_name]
    
    st.markdown("---")
    
    # Загружаем суммаризации
    if selected_product:
        summaries = run_async(load_summaries_by_product(selected_product.id))
    else:
        # Загружаем все суммаризации (для всех продуктов)
        app = Container.summary_application()
        summaries = run_async(app.list(limit=100))
    
    if not summaries:
        st.info("История суммаризаций пуста")
        st.stop()
    
    st.subheader(f"Найдено суммаризаций: {len(summaries)}")
    
    # Таблица суммаризаций
    table_data = []
    for s in summaries:
        # Получаем название продукта
        product_name = "-"
        if selected_product:
            product_name = selected_product.name
        else:
            # Ищем продукт в списке
            for p in products:
                if p.id == s.product_id:
                    product_name = p.name
                    break
        
        table_data.append({
            "ID": str(s.id)[:8] + "...",
            "Продукт": product_name[:30] + ("..." if len(product_name) > 30 else ""),
            "Метод": s.method,
            "Версия": s.method_version or "-",
            "Отзывов": s.reviews_count,
            "Рейтинг": f"{s.rating_avg:.1f}" if s.rating_avg else "-",
            "Дата": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "-",
        })
    
    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
    )
    
    st.markdown("---")
    
    # Детальный просмотр суммаризации
    st.subheader("Детали суммаризации")
    
    summary_options = {
        f"{str(s.id)[:8]}... | {s.method} | {s.created_at.strftime('%Y-%m-%d %H:%M')}": s
        for s in summaries
    }
    
    selected_summary_key = st.selectbox("Выберите суммаризацию", list(summary_options.keys()))
    selected_summary = summary_options[selected_summary_key]
    
    if selected_summary:
        st.markdown("---")
        
        # Метаданные
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"**ID:** `{selected_summary.id}`")
        with col2:
            st.markdown(f"**Метод:** {selected_summary.method} ({selected_summary.method_version or 'N/A'})")
        with col3:
            st.markdown(f"**Отзывов:** {selected_summary.reviews_count}")
        with col4:
            st.markdown(f"**Дата:** {selected_summary.created_at}")
        
        # Параметры
        if selected_summary.params:
            with st.expander("📋 Параметры генерации"):
                st.json(selected_summary.params)
        
        # Входная статистика
        with st.expander("📊 Статистика отзывов"):
            stat_cols = st.columns(4)
            with stat_cols[0]:
                st.metric("Количество", selected_summary.reviews_count)
            with stat_cols[1]:
                st.metric("Средний рейтинг", f"{selected_summary.rating_avg:.1f}" if selected_summary.rating_avg else "-")
            with stat_cols[2]:
                st.metric("Дата (мин)", selected_summary.date_min.strftime("%Y-%m-%d") if selected_summary.date_min else "-")
            with stat_cols[3]:
                st.metric("Дата (макс)", selected_summary.date_max.strftime("%Y-%m-%d") if selected_summary.date_max else "-")
        
        st.markdown("---")
        
        # Результат суммаризации
        st.subheader("Результат")
        
        # Общий текст
        if selected_summary.has_overall_summary():
            st.markdown("### 📝 Общее резюме")
            st.markdown(
                f'<div class="summary-text">{selected_summary.text_overall}</div>',
                unsafe_allow_html=True
            )
        
        # Структурированный результат
        if selected_summary.has_structured_summary():
            result_cols = st.columns(3)
            
            with result_cols[0]:
                st.markdown("### 📋 Нейтральное")
                if selected_summary.text_neutral:
                    st.markdown(
                        f'<div class="summary-text neutral">{selected_summary.text_neutral}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.caption("Не заполнено")
            
            with result_cols[1]:
                st.markdown("### ✅ Плюсы")
                if selected_summary.text_pros:
                    # Разбиваем текст на предложения и выделяем положительные моменты
                    pros_text = selected_summary.text_pros.replace('\n', '<br>')
                    st.markdown(
                        f'<div class="summary-text" style="background-color: #e8f5e9; border-left: 4px solid #09ab3b;">'
                        f'<span class="positive">{pros_text}</span></div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.caption("Не заполнено")
            
            with result_cols[2]:
                st.markdown("### ❌ Минусы")
                if selected_summary.text_cons:
                    # Разбиваем текст на предложения и выделяем отрицательные моменты
                    cons_text = selected_summary.text_cons.replace('\n', '<br>')
                    st.markdown(
                        f'<div class="summary-text" style="background-color: #ffebee; border-left: 4px solid #ff2b2b;">'
                        f'<span class="negative">{cons_text}</span></div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.caption("Не заполнено")
        
        # Ключевые фразы
        if selected_summary.has_key_phrases():
            st.markdown("---")
            st.markdown("### 🔑 Ключевые фразы")
            
            # Разделяем фразы по тональности
            positive_phrases = [kp for kp in selected_summary.key_phrases if kp.sentiment == "positive"]
            negative_phrases = [kp for kp in selected_summary.key_phrases if kp.sentiment == "negative"]
            neutral_phrases = [kp for kp in selected_summary.key_phrases if kp.sentiment == "neutral"]
            
            if positive_phrases or negative_phrases or neutral_phrases:
                phrase_cols = st.columns(3)
                
                with phrase_cols[0]:
                    if positive_phrases:
                        st.markdown("#### ✅ Положительные")
                        for kp in sorted(positive_phrases, key=lambda x: x.count, reverse=True)[:10]:
                            share_text = f" ({kp.share * 100:.1f}%)" if kp.share else ""
                            st.markdown(
                                f'<span class="positive">• {kp.phrase}</span> '
                                f'<small>({kp.count}{share_text})</small>',
                                unsafe_allow_html=True
                            )
                
                with phrase_cols[1]:
                    if negative_phrases:
                        st.markdown("#### ❌ Отрицательные")
                        for kp in sorted(negative_phrases, key=lambda x: x.count, reverse=True)[:10]:
                            share_text = f" ({kp.share * 100:.1f}%)" if kp.share else ""
                            st.markdown(
                                f'<span class="negative">• {kp.phrase}</span> '
                                f'<small>({kp.count}{share_text})</small>',
                                unsafe_allow_html=True
                            )
                
                with phrase_cols[2]:
                    if neutral_phrases:
                        st.markdown("#### ⚪ Нейтральные")
                        for kp in sorted(neutral_phrases, key=lambda x: x.count, reverse=True)[:10]:
                            share_text = f" ({kp.share * 100:.1f}%)" if kp.share else ""
                            st.markdown(
                                f'<span class="neutral">• {kp.phrase}</span> '
                                f'<small>({kp.count}{share_text})</small>',
                                unsafe_allow_html=True
                            )
                
                # Полная таблица в expander
                with st.expander("📊 Полная таблица ключевых фраз"):
                    phrases_data = []
                    for kp in selected_summary.key_phrases:
                        sentiment_emoji = {
                            "positive": "🟢",
                            "negative": "🔴",
                            "neutral": "⚪",
                        }.get(kp.sentiment, "⚪")
                        
                        phrases_data.append({
                            "Фраза": kp.phrase,
                            "Тональность": f"{sentiment_emoji} {kp.sentiment}",
                            "Упоминаний": kp.count,
                            "Доля": f"{kp.share * 100:.1f}%" if kp.share else "-",
                        })
                    
                    st.dataframe(phrases_data, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Ошибка при загрузке данных: {e}")
    st.info("Убедитесь, что база данных доступна и миграции выполнены")
