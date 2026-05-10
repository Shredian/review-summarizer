"""Лёгкая проверка evaluation-метрик: мало строк из БД, тяжёлые расчёты по желанию."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import UUID

import pandas as pd
import streamlit as st

root_path = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.container import Container
from src.domain.evaluation.config import EvaluationRunConfig
from src.presentation.streamlit.utils.async_utils import run_async

st.set_page_config(page_title="Evaluation метрики", page_icon="📊", layout="wide")


async def _sets_overview():
    app = Container.evaluation_application()
    return await app.list_benchmark_sets_overview()


async def _ingest_text(raw: str) -> list[UUID]:
    app = Container.evaluation_application()
    return await app.ingest_json_catalog_text(raw)


async def _run_eval(
    set_name: str,
    *,
    product_limit: int | None,
    force_ledger_rebuild: bool,
    run_auxiliary_metrics: bool,
    run_llm_judge: bool,
    run_glass_box: bool,
):
    app = Container.evaluation_application()
    cfg = EvaluationRunConfig(
        benchmark_set_name=set_name,
        run_auxiliary_metrics=run_auxiliary_metrics,
        run_llm_judge=run_llm_judge,
        run_pairwise_judge=run_llm_judge,
        run_glass_box=run_glass_box,
    )
    return await app.run_evaluation_for_set(
        cfg,
        export_dir=None,
        force_ledger_rebuild=force_ledger_rebuild,
        product_limit=product_limit,
    )


async def _run_deep(run_id: UUID):
    repo = Container.evaluation_run_repository()
    return await repo.get_run_deep(run_id)


st.title("Проверка метрик evaluation")
st.caption(
    "По умолчанию — один товар за прогон и только основные метрики "
    "(без BERTScore/ROUGE и без LLM-судьи). Полный запрос отзывов — только под LIMIT."
)

if st.sidebar.button("Обновить страницу", type="secondary"):
    st.rerun()

try:
    overview = run_async(_sets_overview())
except Exception as exc:
    st.error(f"Не удалось прочитать benchmark-таблицы: {exc}")
    st.stop()

if overview:
    st.subheader("Наборы в БД (имя × число товаров)")
    st.dataframe(
        pd.DataFrame(overview, columns=["benchmark_set_name", "products"]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("В БД ещё нет benchmark-товаров. Загрузите небольшой JSON ниже.")

with st.expander("Загрузить каталог в БД из текста или файла"):
    pasted = st.text_area(
        "JSON каталога (как в examples/benchmark_config.sample.json или массив товаров)",
        height=140,
        placeholder='{"items": [ { "benchmark_set_name": "...", ... } ]}',
        key="bench_catalog_text",
    )
    upload = st.file_uploader(".json файл каталога", type=["json"])
    ingest_body = ""
    if upload is not None:
        ingest_body = upload.getvalue().decode("utf-8", errors="replace")
    else:
        ingest_body = (pasted or "").strip()

    if st.button("Записать в БД"):
        if not ingest_body.strip():
            st.warning("Нет содержимого для загрузки.")
        else:
            try:
                ids = run_async(_ingest_text(ingest_body))
                st.success(f"Записано товаров: {len(ids)}")
                st.rerun()
            except json.JSONDecodeError as exc:
                st.error(f"JSON: {exc}")
            except ValueError as exc:
                st.error(str(exc))

sets = [row[0] for row in overview]
if sets:
    picked = st.selectbox("Benchmark-набор", options=sets, index=0)
else:
    picked = st.text_input("Имя benchmark-набора")

col1, col2, col3 = st.columns(3)
with col1:
    lim = st.number_input(
        "Макс. число товаров за прогон (SQL LIMIT)",
        min_value=1,
        max_value=500,
        value=1,
    )
with col2:
    force_led = st.checkbox("Пересобрать reference ledger", value=False)
with col3:
    glass = st.checkbox("Glass-box метрики (план суммаризации)", value=False)

aux = st.checkbox("Вспомогательные метрики (BERTScore, ROUGE …)", value=False)
judge = st.checkbox("LLM-судья и pairwise-сравнение", value=False)

run_clicked = st.button("Запустить проверку метрик", type="primary")

if not run_clicked:
    lr = st.session_state.get("last_eval_run")
    if lr:
        st.divider()
        st.subheader("Последний прогон (сессия)")
        st.code(str(lr["run_id"]), language="text")
    st.stop()

name = str(picked or "").strip()
if not name:
    st.error("Выберите или введите имя набора.")
    st.stop()

with st.spinner("Суммаризация и расчёт метрик…"):
    try:
        summary = run_async(
            _run_eval(
                name,
                product_limit=int(lim),
                force_ledger_rebuild=force_led,
                run_auxiliary_metrics=aux,
                run_llm_judge=judge,
                run_glass_box=glass,
            )
        )
    except Exception as exc:
        st.exception(exc)
        st.stop()

st.session_state["last_eval_run"] = {"run_id": summary.run_id, "picked": name}
st.success(f"run_id = {summary.run_id}")

with st.spinner("Загрузка результатов…"):
    run_row = run_async(_run_deep(summary.run_id))

rows_out: list[dict] = []
for res in run_row.results:
    mj = res.metrics_json
    flat = mj.get("flat", {}) if isinstance(mj, dict) else {}
    if not isinstance(flat, dict):
        flat = {}
    row = {
        "benchmark_product_id": str(res.benchmark_product_id),
        "system_name": res.system_name,
    }
    row.update(flat)
    rows_out.append(row)

if rows_out:
    df = pd.DataFrame(rows_out)
    st.subheader("Метрики по системам и товарам")
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.warning("Нет строк результатов (набор без товаров?).")
