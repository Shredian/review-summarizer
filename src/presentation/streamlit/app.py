import streamlit as st

st.set_page_config(
    page_title="Review Summarizer",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📝 Review Summarizer")
st.markdown("""
Добро пожаловать в сервис суммаризации отзывов!

### Возможности:

- **Products** — просмотр списка продуктов и количества отзывов
- **Product Reviews** — просмотр отзывов конкретного продукта
- **Summarization** — генерация суммаризации отзывов
- **History** — история суммаризаций
- **Review suggestions** — проверка контекстных подсказок при написании отзыва (prepare / suggest / feedback)
- **Evaluation metrics** — быстрый прогон метрик benchmark (без CLI)

---

Выберите страницу в боковом меню слева.
""")

st.sidebar.success("Выберите страницу выше")
