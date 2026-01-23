import asyncio
import threading
import streamlit as st


@st.cache_resource
def get_event_loop():
    """
    Создает и возвращает глобальный event loop для работы с асинхронными вызовами в Streamlit.
    Использует отдельный поток для loop, чтобы не блокировать Streamlit.
    """
    loop = asyncio.new_event_loop()
    
    def run_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()
        
    thread = threading.Thread(target=run_loop, args=(loop,), daemon=True)
    thread.start()
    
    return loop


def run_async(coro):
    """Выполняет корутину в глобальном event loop."""
    loop = get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()
