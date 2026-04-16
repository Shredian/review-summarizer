"""Подготовка таблиц и графиков для дашборда Aspect Evidence Guided (Streamlit)."""

from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import UUID

import pandas as pd
import plotly.graph_objects as go


def cluster_rows_to_dataframe(clusters: list[Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for cluster in clusters:
        aliases = cluster.aliases_json.get("aliases", []) if isinstance(cluster.aliases_json, dict) else []
        rows.append(
            {
                "Аспект": cluster.aspect_name,
                "cluster_id": str(cluster.id),
                "Синонимов": len(aliases),
                "Упоминаний": cluster.total_mentions,
                "Positive": cluster.positive_mentions,
                "Negative": cluster.negative_mentions,
                "Neutral": cluster.neutral_mentions,
                "Mixed": cluster.mixed_mentions,
                "Importance": float(cluster.importance_score),
                "Prevalence": float(cluster.prevalence_score),
                "Polarity balance": float(cluster.polarity_balance_score),
                "Редкий": cluster.rarity_flag,
            }
        )
    return pd.DataFrame(rows)


def mention_rows_to_dataframe(mentions: list[Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for mention in mentions:
        rows.append(
            {
                "review_id": str(mention.review_id),
                "Секция": mention.section_type,
                "Кандидат": mention.aspect_candidate,
                "Сырой аспект": mention.aspect_raw,
                "Сентимент": mention.sentiment_label,
                "score": mention.sentiment_score,
                "Уверенность": mention.extractor_confidence,
                "Фрагмент": mention.span_text,
            }
        )
    return pd.DataFrame(rows)


def filter_mentions_df(
    df: pd.DataFrame,
    sections: list[str] | None,
    sentiments: list[str] | None,
    search: str,
) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if sections:
        out = out[out["Секция"].isin(sections)]
    if sentiments:
        out = out[out["Сентимент"].isin(sentiments)]
    q = search.strip().lower()
    if q:
        mask = (
            out["Кандидат"].str.lower().str.contains(q, na=False)
            | out["Фрагмент"].str.lower().str.contains(q, na=False)
            | out["Сырой аспект"].str.lower().str.contains(q, na=False)
        )
        out = out[mask]
    return out


def evidence_to_dataframe(evidence: list[Any], cluster_id_to_name: dict[UUID, str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in evidence:
        cid = item.aspect_cluster_id
        rows.append(
            {
                "Аспект": cluster_id_to_name.get(cid, str(cid)),
                "cluster_id": str(cid),
                "review_id": str(item.review_id),
                "Ранг": item.evidence_rank,
                "Полярность": item.supports_polarity,
                "В финале": item.used_in_final_summary,
                "Текст": item.evidence_text,
            }
        )
    return pd.DataFrame(rows)


def build_cluster_name_map(clusters: list[Any]) -> dict[UUID, str]:
    return {c.id: c.aspect_name for c in clusters}


def sentiment_section_counts(mentions: list[Any]) -> pd.DataFrame:
    grouped = Counter((m.section_type, m.sentiment_label) for m in mentions)
    rows = [
        {"Секция": s, "Сентимент": sent, "Упоминаний": c}
        for (s, sent), c in sorted(grouped.items())
    ]
    return pd.DataFrame(rows)


def sentiment_section_pivot_for_chart(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    pivot = df.pivot_table(index="Секция", columns="Сентимент", values="Упоминаний", fill_value=0)
    return pivot


def make_importance_prevalence_scatter(df: pd.DataFrame) -> go.Figure | None:
    if df.empty or "Importance" not in df.columns:
        return None
    fig = go.Figure()
    common = df[df["Редкий"].eq(False)]
    rare = df[df["Редкий"].eq(True)]
    if not common.empty:
        fig.add_trace(
            go.Scatter(
                x=common["Prevalence"],
                y=common["Importance"],
                mode="markers",
                name="Обычный",
                marker=dict(size=11, color="#2980b9", line=dict(width=0.5, color="white")),
                text=common["Аспект"],
                hovertemplate=(
                    "<b>%{text}</b><br>Prevalence: %{x:.4f}<br>Importance: %{y:.4f}<extra></extra>"
                ),
            )
        )
    if not rare.empty:
        fig.add_trace(
            go.Scatter(
                x=rare["Prevalence"],
                y=rare["Importance"],
                mode="markers",
                name="Редкий (rarity)",
                marker=dict(size=12, color="#c0392b", symbol="diamond", line=dict(width=0.5, color="white")),
                text=rare["Аспект"],
                hovertemplate=(
                    "<b>%{text}</b><br>Prevalence: %{x:.4f}<br>Importance: %{y:.4f}<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        title="Важность vs распространённость кластеров",
        xaxis_title="Prevalence",
        yaxis_title="Importance",
        height=420,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def make_cluster_polarity_bars(df: pd.DataFrame, top_n: int = 15) -> go.Figure | None:
    if df.empty:
        return None
    sub = df.nlargest(top_n, "Упоминаний") if len(df) > top_n else df
    names = sub["Аспект"].tolist()
    fig = go.Figure(
        data=[
            go.Bar(name="Positive", x=names, y=sub["Positive"].tolist(), marker_color="#27ae60"),
            go.Bar(name="Negative", x=names, y=sub["Negative"].tolist(), marker_color="#c0392b"),
            go.Bar(name="Neutral", x=names, y=sub["Neutral"].tolist(), marker_color="#7f8c8d"),
            go.Bar(name="Mixed", x=names, y=sub["Mixed"].tolist(), marker_color="#8e44ad"),
        ]
    )
    fig.update_layout(
        barmode="stack",
        title=f"Полярности по топ-{len(names)} кластерам (по числу упоминаний)",
        height=max(400, 28 * len(names)),
        xaxis=dict(tickangle=-35),
        margin=dict(b=120, t=50),
    )
    return fig


def make_sentiment_section_grouped_bar(pivot: pd.DataFrame) -> go.Figure | None:
    if pivot.empty:
        return None
    fig = go.Figure()
    for col in pivot.columns:
        fig.add_trace(
            go.Bar(name=str(col), x=pivot.index.astype(str).tolist(), y=pivot[col].tolist())
        )
    fig.update_layout(
        barmode="group",
        title="Упоминания: секция × сентимент",
        height=400,
        xaxis_title="Секция",
        yaxis_title="Количество",
        legend_title="Сентимент",
        margin=dict(t=50),
    )
    return fig


def paginate_dataframe(df: pd.DataFrame, page: int, page_size: int) -> tuple[pd.DataFrame, int]:
    """page — с 1. Возвращает срез и общее число страниц."""
    if df.empty:
        return df, 1
    total_pages = max(1, (len(df) + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    return df.iloc[start : start + page_size], total_pages


def plan_items_to_dataframe(plan_obj: Any | None) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Возвращает (selected_df, dropped_series_as_df, diagnostics_dict)."""
    if plan_obj is None:
        return pd.DataFrame(), pd.DataFrame(), {}
    raw_sel = plan_obj.selected_aspects_json or {}
    items = raw_sel.get("items", []) if isinstance(raw_sel, dict) else []
    selected_df = pd.DataFrame(items) if items else pd.DataFrame()

    raw_drop = plan_obj.dropped_aspects_json or {}
    dropped_list = raw_drop.get("items", []) if isinstance(raw_drop, dict) else []
    dropped_df = pd.DataFrame({"Отброшенный аспект": dropped_list}) if dropped_list else pd.DataFrame()

    diag = plan_obj.diagnostics_json if isinstance(plan_obj.diagnostics_json, dict) else {}
    return selected_df, dropped_df, diag


def params_versions_block(params: dict[str, Any]) -> dict[str, Any]:
    return {
        "method_version": params.get("method_version"),
        "pipeline_version": params.get("pipeline_version"),
        "planner_version": params.get("planner_version"),
    }


def run_diagnostics_block(params: dict[str, Any]) -> dict[str, Any]:
    d = params.get("diagnostics") or {}
    return dict(d) if isinstance(d, dict) else {}


def reproducible_params_for_display(params: dict[str, Any]) -> dict[str, Any]:
    """Убираем вложенный diagnostics из копии для таблицы «параметры метода»."""
    skip = {"diagnostics", "method_version", "pipeline_version", "planner_version"}
    return {k: v for k, v in params.items() if k not in skip}
