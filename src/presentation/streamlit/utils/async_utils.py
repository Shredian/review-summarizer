import asyncio
import threading

import streamlit as st


@st.cache_resource
def get_event_loop():
    """Отдельный поток с event loop для await из синхронного Streamlit."""
    loop = asyncio.new_event_loop()

    def run_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    thread = threading.Thread(target=run_loop, args=(loop,), daemon=True)
    thread.start()

    return loop


def run_async(coro):
    """Блокирующий вызов корутины через общий loop."""
    loop = get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()
