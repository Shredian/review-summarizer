import streamlit as st

st.set_page_config(
    page_title="Review Summarizer",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Review Summarizer")
st.markdown(
    """
**Разделы:** Products · Product Reviews · Summarization · History · Aspect Evidence Insights · Review suggestions · Evaluation metrics.

Выберите страницу в боковом меню.
"""
)
