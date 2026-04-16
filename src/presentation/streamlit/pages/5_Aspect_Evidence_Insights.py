"""Страница детальной аналитики артефактов aspect_evidence_guided_v1."""

import sys
from pathlib import Path
from uuid import UUID

import pandas as pd
import streamlit as st

root_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(root_path))

from src.container import Container
from src.presentation.streamlit.aspect_evidence_insights_data import (
    build_cluster_name_map,
    evidence_to_dataframe,
    filter_mentions_df,
    make_cluster_polarity_bars,
    make_importance_prevalence_scatter,
    make_sentiment_section_grouped_bar,
    mention_rows_to_dataframe,
    paginate_dataframe,
    plan_items_to_dataframe,
    cluster_rows_to_dataframe,
    params_versions_block,
    reproducible_params_for_display,
    run_diagnostics_block,
    sentiment_section_counts,
    sentiment_section_pivot_for_chart,
)
from src.presentation.streamlit.utils.async_utils import run_async


TARGET_METHOD = "aspect_evidence_guided_v1"


async def load_products():
    app = Container.product_application()
    return await app.list(limit=1000)


async def load_method_summaries(product_id: UUID):
    app = Container.summary_application()
    return await app.list_by_product(product_id=product_id, limit=100, method=TARGET_METHOD)


async def load_artifacts(summary_id: UUID):
    mention_repo = Container.aspect_mention_repository()
    cluster_repo = Container.aspect_cluster_repository()
    evidence_repo = Container.summary_evidence_repository()
    plan_repo = Container.summary_plan_repository()
    mentions = await mention_repo.list_by_summary(summary_id)
    clusters = await cluster_repo.list_by_summary(summary_id)
    evidence = await evidence_repo.list_by_summary(summary_id)
    plan = await plan_repo.get_by_summary(summary_id)
    return mentions, clusters, evidence, plan


st.set_page_config(page_title="Aspect Insights", page_icon="🧭", layout="wide")
st.title("🧭 Aspect Evidence Guided")
st.caption("Интерактивный дашборд артефактов и метрик для метода aspect_evidence_guided_v1")

try:
    products = run_async(load_products())
    if not products:
        st.warning("Нет продуктов в базе данных")
        st.stop()

    product_options = {product.name: product for product in products}
    selected_name = st.selectbox("Продукт", list(product_options.keys()))
    selected_product = product_options[selected_name]

    summaries = run_async(load_method_summaries(selected_product.id))
    if not summaries:
        st.info("Для выбранного продукта пока нет суммаризаций методом aspect_evidence_guided_v1")
        st.stop()

    summary_options = {
        f"{str(summary.id)[:8]}… | {summary.created_at.strftime('%Y-%m-%d %H:%M')} | reviews={summary.reviews_count}": summary
        for summary in summaries
    }
    selected_key = st.selectbox("Запуск (summary)", list(summary_options.keys()))
    selected_summary = summary_options[selected_key]

    mentions, clusters, evidence, plan = run_async(load_artifacts(selected_summary.id))
    params = selected_summary.params or {}
    diag_run = run_diagnostics_block(params)
    versions = params_versions_block(params)

    cluster_df = cluster_rows_to_dataframe(clusters)
    mention_df = mention_rows_to_dataframe(mentions)
    cluster_name_by_id = build_cluster_name_map(clusters)
    evidence_df = evidence_to_dataframe(evidence, cluster_name_by_id)
    sentiment_df = sentiment_section_counts(mentions)
    sentiment_pivot = sentiment_section_pivot_for_chart(sentiment_df)
    selected_plan_df, dropped_plan_df, plan_diag = plan_items_to_dataframe(plan)

    tab_overview, tab_params, tab_clusters, tab_mentions, tab_evidence, tab_planner, tab_texts = st.tabs(
        [
            "Обзор",
            "Параметры",
            "Кластеры",
            "Упоминания",
            "Evidence",
            "Планировщик",
            "Тексты",
        ]
    )

    with tab_overview:
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Mentions", len(mentions))
        m2.metric("Кластеры", len(clusters))
        m3.metric("Evidence", len(evidence))
        m4.metric("Уник. кандидаты", len({m.aspect_candidate for m in mentions}))
        m5.metric("Уник. отзывы", len({m.review_id for m in mentions}))
        m6.metric("Редких кластеров", len([c for c in clusters if c.rarity_flag]))

        st.subheader("Метаданные запуска")
        meta_c1, meta_c2, meta_c3 = st.columns(3)
        meta_c1.metric("Отзывов на входе", selected_summary.reviews_count)
        ra = selected_summary.rating_avg
        meta_c2.metric("Средний рейтинг", f"{ra:.2f}" if ra is not None else "—")
        meta_c3.metric("Summary ID", str(selected_summary.id)[:13] + "…")

        st.subheader("Версии")
        vc1, vc2, vc3 = st.columns(3)
        vc1.metric("Метод (method_version)", versions.get("method_version") or "—")
        vc2.metric("Pipeline", versions.get("pipeline_version") or "—")
        vc3.metric("Planner", versions.get("planner_version") or "—")

        st.subheader("Верификация (из params.diagnostics)")
        if diag_run:
            passed = diag_run.get("verification_passed")
            if passed is True:
                st.success("Верификация пройдена")
            elif passed is False:
                st.error("Верификация не пройдена")
            else:
                st.info("Поле verification_passed отсутствует в сохранённых params")

            err = diag_run.get("verification_errors") or []
            warn = diag_run.get("verification_warnings") or []
            if err:
                st.markdown("**Ошибки:**")
                for e in err:
                    st.write(f"- {e}")
            if warn:
                st.markdown("**Предупреждения:**")
                for w in warn:
                    st.write(f"- {w}")

            mc = diag_run.get("mentions_count")
            cc = diag_run.get("candidates_count")
            if mc is not None or cc is not None:
                d1, d2 = st.columns(2)
                if mc is not None:
                    d1.metric("Mentions (pipeline)", mc)
                if cc is not None:
                    d2.metric("Кандидаты аспектов", cc)
        else:
            st.warning("Нет блока diagnostics в params (старый запуск или пустой объект)")

    with tab_params:
        st.subheader("Параметры воспроизводимости")
        repro = reproducible_params_for_display(params)
        if repro:
            items = list(repro.items())
            half = (len(items) + 1) // 2
            col_a, col_b = st.columns(2)
            for i, (k, v) in enumerate(items):
                target = col_a if i < half else col_b
                with target:
                    st.text(f"{k}")
                    st.code(str(v), language=None)
        else:
            st.info("Нет дополнительных параметров для отображения")

        with st.expander("Полный JSON params (экспорт)"):
            st.json(params)

    with tab_clusters:
        st.subheader("Графики")
        g1, g2 = st.columns(2)
        with g1:
            fig_scatter = make_importance_prevalence_scatter(cluster_df)
            if fig_scatter:
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("Нет данных для scatter")
        with g2:
            top_n = st.slider("Топ кластеров (по упоминаниям)", 5, 40, 15, key="cluster_top_n")
            fig_bar = make_cluster_polarity_bars(cluster_df, top_n=top_n)
            if fig_bar:
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Нет данных для столбчатой диаграммы")

        st.subheader("Сентимент × секция (упоминания)")
        fig_sent = make_sentiment_section_grouped_bar(sentiment_pivot)
        if fig_sent:
            st.plotly_chart(fig_sent, use_container_width=True)
        else:
            st.info("Нет данных для групповой диаграммы (нет упоминаний)")

        st.subheader("Таблица кластеров")
        if not cluster_df.empty:
            st.dataframe(
                cluster_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Аспект": st.column_config.TextColumn("Аспект", width="medium"),
                    "cluster_id": st.column_config.TextColumn("cluster_id", width="small"),
                    "Importance": st.column_config.NumberColumn("Importance", format="%.4f"),
                    "Prevalence": st.column_config.NumberColumn("Prevalence", format="%.4f"),
                    "Polarity balance": st.column_config.NumberColumn("Polarity bal.", format="%.4f"),
                    "Редкий": st.column_config.CheckboxColumn("Редкий"),
                },
            )
        else:
            st.info("Нет кластеров")

    with tab_mentions:
        fc1, fc2, fc3 = st.columns([1, 1, 2])
        all_sections = sorted(mention_df["Секция"].dropna().unique().tolist()) if not mention_df.empty else []
        all_sentiments = sorted(mention_df["Сентимент"].dropna().unique().tolist()) if not mention_df.empty else []
        with fc1:
            sel_sec = st.multiselect("Секция", all_sections, default=[], key="m_sec")
        with fc2:
            sel_sent = st.multiselect("Сентимент", all_sentiments, default=[], key="m_sent")
        with fc3:
            search = st.text_input("Поиск по кандидату / фрагменту", "", key="m_q")

        filtered = filter_mentions_df(
            mention_df,
            sections=sel_sec if sel_sec else None,
            sentiments=sel_sent if sel_sent else None,
            search=search,
        )
        st.caption(f"Строк после фильтра: **{len(filtered)}** из {len(mention_df)}")

        page_size_m = st.select_slider("Строк на страницу", options=[25, 50, 100, 200], value=50, key="m_ps")
        total_pages_m = max(1, (len(filtered) + page_size_m - 1) // page_size_m) if len(filtered) else 1
        page_m = st.number_input("Страница", min_value=1, max_value=total_pages_m, value=1, key="m_pg")
        slice_m, _ = paginate_dataframe(filtered, int(page_m), page_size_m)

        if not slice_m.empty:
            st.dataframe(
                slice_m,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Фрагмент": st.column_config.TextColumn("Фрагмент", width="large"),
                    "Кандидат": st.column_config.TextColumn("Кандидат", width="medium"),
                    "Уверенность": st.column_config.NumberColumn("Уверенность", format="%.3f"),
                    "score": st.column_config.NumberColumn("sent. score", format="%.3f"),
                },
            )
        else:
            st.info("Нет упоминаний по фильтрам")

    with tab_evidence:
        if evidence_df.empty:
            st.info("Нет evidence spans")
        else:
            aspects_all = sorted(evidence_df["Аспект"].dropna().unique().tolist())
            pol_all = sorted(evidence_df["Полярность"].dropna().unique().tolist())
            e1, e2 = st.columns(2)
            with e1:
                asp_pick = st.multiselect("Аспект", aspects_all, default=[], key="e_asp")
            with e2:
                pol_pick = st.multiselect("Полярность", pol_all, default=[], key="e_pol")

            ev_f = evidence_df
            if asp_pick:
                ev_f = ev_f[ev_f["Аспект"].isin(asp_pick)]
            if pol_pick:
                ev_f = ev_f[ev_f["Полярность"].isin(pol_pick)]

            st.caption(f"Строк: **{len(ev_f)}**")

            page_size_e = st.select_slider("Строк на страницу", options=[25, 50, 100, 200], value=50, key="e_ps")
            total_pages_e = max(1, (len(ev_f) + page_size_e - 1) // page_size_e) if len(ev_f) else 1
            page_e = st.number_input("Страница", min_value=1, max_value=total_pages_e, value=1, key="e_pg")
            slice_e, _ = paginate_dataframe(ev_f, int(page_e), page_size_e)

            st.dataframe(
                slice_e,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Текст": st.column_config.TextColumn("Текст", width="large"),
                    "Аспект": st.column_config.TextColumn("Аспект", width="medium"),
                    "В финале": st.column_config.CheckboxColumn("В финале"),
                },
            )

    with tab_planner:
        if plan is None:
            st.warning("SummaryPlan не найден для этой суммаризации")
        else:
            st.caption(f"planner_version: **{plan.planner_version}**")
            st.subheader("Выбранные аспекты")
            if not selected_plan_df.empty:
                st.dataframe(selected_plan_df, use_container_width=True, hide_index=True)
            else:
                st.info("Пустой selected_aspects_json")
            st.subheader("Отброшенные аспекты")
            if not dropped_plan_df.empty:
                st.dataframe(dropped_plan_df, use_container_width=True, hide_index=True)
            else:
                st.info("Нет отброшенных")
            st.subheader("Диагностика планировщика")
            if plan_diag:
                c1, c2, c3, c4 = st.columns(4)
                keys = ["selected_count", "dropped_count", "rare_selected", "mean_importance"]
                labels = ["Выбрано", "Отброшено", "Редких в плане", "Средн. importance"]
                cols = [c1, c2, c3, c4]
                for col, key, lab in zip(cols, keys, labels):
                    if key in plan_diag:
                        col.metric(lab, plan_diag[key])
                with st.expander("Полный diagnostics_json"):
                    st.json(plan_diag)
            else:
                st.info("diagnostics_json пуст")

            with st.expander("Сырой selected_aspects_json"):
                st.json(plan.selected_aspects_json)
            with st.expander("Сырой dropped_aspects_json"):
                st.json(plan.dropped_aspects_json)

    with tab_texts:
        st.subheader("Итоговые тексты")
        t1, t2 = st.columns(2)
        with t1:
            st.markdown("**Overall**")
            st.write(selected_summary.text_overall or "—")
            st.markdown("**Плюсы**")
            st.write(selected_summary.text_pros or "—")
        with t2:
            st.markdown("**Минусы**")
            st.write(selected_summary.text_cons or "—")
            st.markdown("**Нейтрально**")
            st.write(selected_summary.text_neutral or "—")

        st.subheader("Ключевые фразы (из summary)")
        if selected_summary.key_phrases:
            kdf = pd.DataFrame([kp.model_dump() for kp in selected_summary.key_phrases])
            st.dataframe(kdf, use_container_width=True, hide_index=True)
        else:
            st.info("Нет key_phrases")

except Exception as exc:
    st.error(f"Ошибка при загрузке аналитики: {exc}")
    st.info("Убедитесь, что контейнеры запущены и миграции применены")
