"""
Dashboard · Adidas vs Nike
─────────────────────────────────────────────────────────────
Análisis comparativo del catálogo Adidas vs Nike (3,268 sneakers
scrapeados, 4 brands, snapshot 2020-04-13).

Fuente de datos: Supabase
  · brands   (5 marcas — Adidas Core/Neo, Originals, Sport Perf, Nike)
  · products (3,268 productos del catálogo)

Identidad visual: estilo Claude (beige cálido + coral + serif).
"""
from __future__ import annotations

import concurrent.futures
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv(Path(__file__).parent / ".env")


# ─────────────────────────────────────────────────────────────
# Flag de estado del dataset
# ─────────────────────────────────────────────────────────────
DATASET_READY: bool = True  # cuando los datos están en Supabase


# ─────────────────────────────────────────────────────────────
# Configuración de página
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Adidas vs Nike · Analaitica",
    page_icon="✲",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────
# Paleta Claude
# ─────────────────────────────────────────────────────────────
CLAUDE_PALETTE = {
    "bg":         "#F5F0E8",
    "surface":    "#FAF7F0",
    "ink":        "#3D3929",
    "ink_muted":  "#6B6356",
    "primary":    "#D97757",  # coral — usar para Adidas
    "primary_dk": "#BC5215",
    "accent":     "#629D6E",  # sage
    "warning":    "#C19250",
    "danger":     "#A33E2E",
    "muted":      "#B49B7C",
    "border":     "#E5DDD0",
    "ink_alt":    "#1F1E1B",  # negro Nike-ish
}

# ─────────────────────────────────────────────────────────────
# Sistema de color de DATOS — independiente del tema del dashboard
# ─────────────────────────────────────────────────────────────
# El branding beige (CLAUDE_PALETTE) se usa SOLO para el chrome (hero, KPIs,
# tabs, sidebar). Las gráficas usan su propia paleta para que el color tenga
# significado estable y no dependa de la estética de la página.
#   · Categórica  : Okabe-Ito (colorblind-safe)
#   · Secuencial  : Viridis (perceptualmente uniforme)
#   · Semánticos  : rojo = riesgo, verde = bueno, gris = contexto (estables)
VIZ = {
    "chart_bg":   "#FFFFFF",   # fondo de gráfica (la página sigue beige)
    "grid":       "#E6E6E6",   # rejilla/ejes neutros (no el border beige)
    "axis_text":  "#333333",   # texto de ejes neutro (no el ink beige)
    "reference":  "#9AA0A6",   # líneas de referencia / medianas (contexto)
    "alert":      "#D62728",   # rojo — SIEMPRE = riesgo/negativo
    "positive":   "#2CA02C",   # verde — SIEMPRE = bueno
    "structural": "#8C8C8C",   # barras no categóricas (Pareto)
    "emphasis":   "#333333",   # trendline OLS global / protagonistas neutros
}

# Mapping para parent brand (Okabe-Ito): Adidas → azul, Nike → naranja.
# Significado estable de color en TODAS las gráficas categóricas.
PARENT_BRAND_COLORS = {
    "Adidas": "#0072B2",  # azul
    "Nike":   "#E69F00",  # naranja
}

# Secuencia categórica de respaldo (Okabe-Ito completa)
PLOTLY_SEQUENCE = [
    "#0072B2",  # azul
    "#E69F00",  # naranja
    "#009E73",  # verde
    "#CC79A7",  # rosa
    "#56B4E9",  # celeste
    "#D55E00",  # bermellón
    "#F0E442",  # amarillo
]

SEQUENTIAL_SCALE = "Viridis"  # heatmap: perceptualmente uniforme, colorblind-safe


# ─────────────────────────────────────────────────────────────
# CSS · identidad Claude
# ─────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', system-ui, sans-serif !important;
        color: {CLAUDE_PALETTE["ink"]};
    }}

    .stApp {{ background: {CLAUDE_PALETTE["bg"]}; }}

    h1, h2, h3, .serif {{
        font-family: 'Source Serif 4', 'Charter', 'Cambria', Georgia, serif !important;
        color: {CLAUDE_PALETTE["ink"]};
        font-weight: 600;
        letter-spacing: -0.01em;
    }}

    .hero {{
        background: {CLAUDE_PALETTE["surface"]};
        border: 1px solid {CLAUDE_PALETTE["border"]};
        border-radius: 18px;
        padding: 36px 40px;
        margin-bottom: 28px;
        box-shadow: 0 1px 2px rgba(61,57,41,0.04), 0 8px 24px rgba(61,57,41,0.06);
    }}
    .hero h1 {{ font-size: 2.2rem; margin: 0 0 6px 0; }}
    .hero p  {{
        font-family: 'Inter', sans-serif;
        color: {CLAUDE_PALETTE["ink_muted"]};
        font-size: 1rem;
        margin: 0;
        line-height: 1.55;
    }}
    .hero-asterisk {{
        font-size: 2rem;
        color: {CLAUDE_PALETTE["primary"]};
        margin-bottom: 12px;
        line-height: 1;
    }}

    .kpi-card {{
        background: {CLAUDE_PALETTE["surface"]};
        border: 1px solid {CLAUDE_PALETTE["border"]};
        border-left: 3px solid {CLAUDE_PALETTE["primary"]};
        border-radius: 14px;
        padding: 20px 22px;
        height: 100%;
        transition: transform .2s ease, box-shadow .2s ease;
    }}
    .kpi-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(61,57,41,.08);
    }}
    .kpi-label {{
        font-size: .74rem;
        text-transform: uppercase;
        letter-spacing: .14em;
        color: {CLAUDE_PALETTE["ink_muted"]};
        font-weight: 600;
        margin-bottom: 8px;
    }}
    .kpi-value {{
        font-family: 'Source Serif 4', serif;
        font-size: 1.85rem;
        font-weight: 600;
        color: {CLAUDE_PALETTE["ink"]};
        line-height: 1.15;
    }}
    .kpi-sub {{
        font-size: .82rem;
        margin-top: 8px;
        color: {CLAUDE_PALETTE["ink_muted"]};
    }}

    .section-title {{
        font-family: 'Source Serif 4', serif;
        font-size: 1.15rem;
        font-weight: 600;
        color: {CLAUDE_PALETTE["ink"]};
        margin: 28px 0 14px 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .section-title::before {{
        content: "";
        width: 3px;
        height: 18px;
        background: {CLAUDE_PALETTE["primary"]};
        border-radius: 2px;
    }}

    .insight-box {{
        background: {CLAUDE_PALETTE["surface"]};
        border: 1px solid {CLAUDE_PALETTE["border"]};
        border-left: 3px solid {CLAUDE_PALETTE["primary"]};
        border-radius: 12px;
        padding: 20px 24px;
        margin-top: 8px;
        color: {CLAUDE_PALETTE["ink"]};
        line-height: 1.7;
    }}

    section[data-testid="stSidebar"] {{
        background: {CLAUDE_PALETTE["surface"]};
        border-right: 1px solid {CLAUDE_PALETTE["border"]};
    }}
    section[data-testid="stSidebar"] * {{ color: {CLAUDE_PALETTE["ink"]}; }}

    div[data-testid="stDataFrame"] {{
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid {CLAUDE_PALETTE["border"]};
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px;
        background: {CLAUDE_PALETTE["surface"]};
        padding: 6px;
        border-radius: 12px;
        border: 1px solid {CLAUDE_PALETTE["border"]};
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        border-radius: 8px;
        padding: 8px 18px;
        color: {CLAUDE_PALETTE["ink_muted"]};
        font-weight: 500;
    }}
    .stTabs [aria-selected="true"] {{
        background: {CLAUDE_PALETTE["primary"]} !important;
        color: white !important;
    }}

    .stButton > button {{
        background: {CLAUDE_PALETTE["primary"]};
        color: white;
        border: none;
        border-radius: 10px;
        padding: 8px 18px;
        font-weight: 500;
        transition: background .2s ease;
    }}
    .stButton > button:hover {{
        background: {CLAUDE_PALETTE["primary_dk"]};
        color: white;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# Layout compartido de Plotly
# ─────────────────────────────────────────────────────────────
plotly_layout = dict(
    paper_bgcolor=VIZ["chart_bg"],
    plot_bgcolor=VIZ["chart_bg"],
    font=dict(color=VIZ["axis_text"], family="Inter"),
    xaxis=dict(gridcolor=VIZ["grid"], linecolor=VIZ["grid"]),
    yaxis=dict(gridcolor=VIZ["grid"], linecolor=VIZ["grid"]),
    colorway=PLOTLY_SEQUENCE,
    legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
    margin=dict(l=10, r=10, t=30, b=10),
)


# ─────────────────────────────────────────────────────────────
# Supabase: cliente + fetch paginado
# ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        try:
            url = url or st.secrets["SUPABASE_URL"]
            key = key or st.secrets["SUPABASE_ANON_KEY"]
        except (KeyError, FileNotFoundError):
            pass
    if not url or not key:
        st.error("❌ Faltan `SUPABASE_URL` y/o `SUPABASE_ANON_KEY` en `.env` o `st.secrets`.")
        st.stop()
    return create_client(url, key)


def fetch_all(client: Client, table: str, page_size: int = 1000) -> pd.DataFrame:
    rows: list[dict] = []
    start = 0
    while True:
        resp = client.table(table).select("*").range(start, start + page_size - 1).execute()
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────
# Carga + ETL (cacheado)
# ─────────────────────────────────────────────────────────────
LOADER_VERSION = "v1-adidas-nike"


@st.cache_data(ttl=3600, persist="disk",
               show_spinner="Cargando catálogo Adidas vs Nike desde Supabase…")
def load_catalog(_v: str = LOADER_VERSION) -> pd.DataFrame:
    """Lee brands + products en paralelo y los une. Datos derivados:
    actual_discount_pct, price_bucket, rating_bucket."""
    client = get_supabase_client()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            f_brands = ex.submit(fetch_all, client, "brands")
            f_products = ex.submit(fetch_all, client, "products")
            brands = f_brands.result()
            products = f_products.result()
    except Exception as e:
        st.error(
            "❌ No se pudieron leer las tablas de Supabase. "
            "¿Ejecutaste `supabase_schema.sql` y `load_to_supabase.py`?"
        )
        st.exception(e)
        st.stop()

    if brands.empty or products.empty:
        st.warning("Las tablas de Supabase están vacías. Corre `python load_to_supabase.py`.")
        st.stop()

    df = products.merge(brands, on="brand_id", how="left")

    # Tipados
    df["last_visited"] = pd.to_datetime(df["last_visited"], errors="coerce", utc=True).dt.tz_localize(None)
    for c in ["listing_price_inr", "sale_price_inr", "discount_pct", "reviews_count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    # Derivados
    df["actual_discount_pct"] = np.where(
        df["listing_price_inr"].notna() & (df["listing_price_inr"] > 0),
        (1 - df["sale_price_inr"] / df["listing_price_inr"]) * 100,
        np.nan,
    )
    df["price_bucket"] = pd.cut(
        df["sale_price_inr"],
        bins=[0, 2000, 5000, 10000, 20000, 100000],
        labels=["<2K", "2-5K", "5-10K", "10-20K", "20K+"],
    )
    df["rating_bucket"] = pd.cut(
        df["rating"],
        bins=[-0.01, 2.5, 3.5, 4.5, 5.01],
        labels=["≤2.5", "2.5-3.5", "3.5-4.5", "4.5-5"],
    )
    return df


# ─────────────────────────────────────────────────────────────
# Helpers de formato
# ─────────────────────────────────────────────────────────────
INR_TO_USD = 0.012  # aprox 2020 — solo referencia secundaria en KPIs


def fmt_inr(v: float) -> str:
    if pd.isna(v):
        return "—"
    if abs(v) >= 1e7:
        return f"₹ {v/1e7:,.1f} Cr"   # crore
    if abs(v) >= 1e5:
        return f"₹ {v/1e5:,.1f} L"    # lakh
    if abs(v) >= 1e3:
        return f"₹ {v/1e3:,.1f}K"
    return f"₹ {v:,.0f}"


def fmt_int(v: float) -> str:
    if pd.isna(v):
        return "—"
    return f"{int(v):,}".replace(",", ".")


def kpi_card(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """


# ─────────────────────────────────────────────────────────────
# Carga del dataset
# ─────────────────────────────────────────────────────────────
df_all = load_catalog()


# ─────────────────────────────────────────────────────────────
# Sidebar · marca + filtros
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"""
        <div style='padding:8px 4px 22px 4px;'>
            <div style='font-size:.7rem; letter-spacing:.18em;
                        color:{CLAUDE_PALETTE["primary"]}; font-weight:600;'>
                ANALAITICA
            </div>
            <div style="font-family:'Source Serif 4', serif;
                        font-size:1.4rem; font-weight:600;
                        color:{CLAUDE_PALETTE["ink"]}; margin-top:4px;">
                Adidas vs Nike
            </div>
            <div style='font-size:.74rem; color:{CLAUDE_PALETTE["ink_muted"]};
                        margin-top:6px;'>
                Catálogo scrapeado · snapshot Abr 2020
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🔄 Refrescar desde Supabase", use_container_width=True,
                 help="Vacía la caché y vuelve a leer brands + products."):
        load_catalog.clear()
        st.rerun()

    st.markdown("---")

    parents_all = sorted(df_all["parent_brand"].dropna().unique())
    parent_sel = st.multiselect(
        "Casa matriz", parents_all, default=parents_all,
        help="Filtra por compañía. Adidas agrupa CORE/NEO + ORIGINALS + SPORT PERFORMANCE.",
    )

    brands_pool = df_all[df_all["parent_brand"].isin(parent_sel)] if parent_sel else df_all
    brands_all = sorted(brands_pool["brand_name"].dropna().unique())
    brand_sel = st.multiselect(
        "Sub-marca", brands_all, default=brands_all,
        help="Marca específica dentro de la casa matriz.",
    )

    price_min_raw, price_max_raw = int(df_all["sale_price_inr"].min()), int(df_all["sale_price_inr"].max())
    price_range = st.slider(
        "Rango de precio (₹)", price_min_raw, price_max_raw,
        (price_min_raw, price_max_raw), step=100,
        help="Filtra por sale_price en rupias indias.",
    )

    discount_range = st.slider(
        "Descuento %", 0, 100, (0, 100),
        help="Rango de descuento marcado en el catálogo.",
    )

    rating_min = st.slider(
        "Rating mínimo", 0.0, 5.0, 0.0, step=0.1,
        help="Solo productos con rating ≥ este valor. 0 incluye productos sin rating.",
    )

    only_with_reviews = st.checkbox(
        "Solo productos con ≥1 review",
        value=False,
        help="Excluye productos con 0 reviews (suelen ser recién listados).",
    )

    st.markdown("---")
    st.caption(f"Productos totales en BD: **{fmt_int(len(df_all))}**")


# ─────────────────────────────────────────────────────────────
# Aplicar filtros
# ─────────────────────────────────────────────────────────────
def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if parent_sel:
        mask &= df["parent_brand"].isin(parent_sel)
    if brand_sel:
        mask &= df["brand_name"].isin(brand_sel)
    mask &= df["sale_price_inr"].between(price_range[0], price_range[1])
    mask &= df["discount_pct"].between(discount_range[0], discount_range[1])
    if rating_min > 0:
        mask &= (df["rating"] >= rating_min) & df["rating"].notna()
    if only_with_reviews:
        mask &= df["reviews_count"] > 0
    return df[mask].copy()


df = apply_filters(df_all)


# ─────────────────────────────────────────────────────────────
# Análisis del slice (sidebar dinámico, debajo de los filtros)
# ─────────────────────────────────────────────────────────────
def render_slice_analysis() -> None:
    """Compara el slice filtrado vs el catálogo completo."""
    with st.sidebar:
        st.markdown("---")
        st.markdown(
            f"<div style='font-size:.72rem; text-transform:uppercase; "
            f"letter-spacing:.18em; color:{CLAUDE_PALETTE['primary']}; "
            f"font-weight:600; margin-bottom:6px;'>"
            f"🔍 Análisis del slice</div>",
            unsafe_allow_html=True,
        )

        n_view = len(df)
        pct_view = n_view / max(len(df_all), 1)
        st.caption(f"**{fmt_int(n_view)}** productos · {pct_view:.1%} del catálogo")

        if n_view == 0:
            st.caption("⚠️ Sin productos para los filtros actuales.")
            return

        # Precio promedio
        price_local = df["sale_price_inr"].mean()
        price_global = df_all["sale_price_inr"].mean()
        delta_p = (price_local - price_global) / price_global if price_global else 0
        arrow_p = "↑" if delta_p > 0.02 else ("↓" if delta_p < -0.02 else "≈")
        st.caption(
            f"💰 Precio medio **{fmt_inr(price_local)}** "
            f"({arrow_p} {abs(delta_p):.0%} vs global)"
        )

        # Descuento promedio
        disc_local = df["discount_pct"].mean()
        disc_global = df_all["discount_pct"].mean()
        delta_d = disc_local - disc_global
        arrow_d = "↑" if delta_d > 1 else ("↓" if delta_d < -1 else "≈")
        st.caption(
            f"💸 Descuento **{disc_local:.1f}%** "
            f"({arrow_d} {abs(delta_d):.1f}pp vs global)"
        )

        # Rating
        rating_local = df.loc[df["rating"].notna() & (df["rating"] > 0), "rating"].mean()
        rating_global = df_all.loc[df_all["rating"].notna() & (df_all["rating"] > 0), "rating"].mean()
        if pd.notna(rating_local) and pd.notna(rating_global):
            delta_r = rating_local - rating_global
            arrow_r = "↑" if delta_r > 0.05 else ("↓" if delta_r < -0.05 else "≈")
            st.caption(
                f"⭐ Rating **{rating_local:.2f}** "
                f"({arrow_r} {abs(delta_r):.2f} vs {rating_global:.2f} global)"
            )

        # Mix de parent_brand
        parent_mix = df["parent_brand"].value_counts(normalize=True)
        if not parent_mix.empty:
            top_p = parent_mix.idxmax()
            share = parent_mix.iloc[0]
            global_share = (df_all["parent_brand"] == top_p).sum() / max(len(df_all), 1)
            delta_share = (share - global_share) * 100
            arrow_s = "↑" if delta_share > 0.5 else ("↓" if delta_share < -0.5 else "≈")
            st.caption(
                f"👟 **{top_p}** {share:.0%} "
                f"({arrow_s} {abs(delta_share):.0f}pp vs global)"
            )

        # Marca líder por # productos
        brand_mix = df["brand_name"].value_counts()
        if not brand_mix.empty:
            top_b = brand_mix.index[0]
            st.caption(f"🏷 Top marca: **{top_b}** ({brand_mix.iloc[0]:,})")


render_slice_analysis()


# ─────────────────────────────────────────────────────────────
# Hero
# ─────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-asterisk">✲</div>
        <h1>Adidas vs Nike</h1>
        <p>Análisis comparativo del catálogo · {fmt_int(len(df))} productos en vista
        de {fmt_int(len(df_all))} totales · snapshot Abril 2020 ·
        precios en rupias indias (₹).</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# Empty state
# ─────────────────────────────────────────────────────────────
if df.empty:
    st.warning("Los filtros actuales dejan el catálogo vacío. Suaviza los filtros del sidebar.")
    st.stop()


# ─────────────────────────────────────────────────────────────
# KPIs (5 cards)
# ─────────────────────────────────────────────────────────────
n_products = len(df)
avg_sale = df["sale_price_inr"].mean()
avg_discount = df["discount_pct"].mean()
rated_mask = df["rating"].notna() & (df["rating"] > 0)
avg_rating = df.loc[rated_mask, "rating"].mean()
n_rated = rated_mask.sum()

parent_counts = df["parent_brand"].value_counts()
top_parent = parent_counts.idxmax() if not parent_counts.empty else "—"
top_parent_share = parent_counts.iloc[0] / parent_counts.sum() if not parent_counts.empty else 0

cols = st.columns(5)
cards = [
    ("Productos",         fmt_int(n_products),         f"de {fmt_int(len(df_all))} en catálogo"),
    ("Sale price medio",  fmt_inr(avg_sale),           f"≈ ${avg_sale * INR_TO_USD:,.0f} USD"),
    ("Descuento medio",   f"{avg_discount:.1f}%",      f"max {df['discount_pct'].max():.0f}%"),
    ("Rating medio",      f"{avg_rating:.2f} ★" if pd.notna(avg_rating) else "—",
                          f"{fmt_int(n_rated)} productos rateados"),
    ("Casa líder",        top_parent,                  f"{top_parent_share:.0%} del catálogo"),
]
for col, (label, value, sub) in zip(cols, cards):
    col.markdown(kpi_card(label, value, sub), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📦 Catálogo", "💸 Pricing & Descuentos", "⭐ Calidad percibida"])


# ───────── TAB 1 — CATÁLOGO ─────────
with tab1:
    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.markdown('<div class="section-title">Composición del catálogo</div>',
                    unsafe_allow_html=True)
        brand_summary = (
            df.groupby(["parent_brand", "brand_name"], observed=True)
            .agg(n=("product_id", "count"))
            .reset_index()
            .sort_values("n", ascending=True)
        )
        fig_brand = px.bar(
            brand_summary, x="n", y="brand_name", orientation="h",
            color="parent_brand", color_discrete_map=PARENT_BRAND_COLORS,
            hover_data={"n": True, "brand_name": False, "parent_brand": True},
            labels={"n": "Productos", "brand_name": ""},
        )
        fig_brand.update_layout(**plotly_layout, height=380, legend_title_text="Casa")
        st.plotly_chart(fig_brand, use_container_width=True)

    with col_b:
        st.markdown('<div class="section-title">Adidas vs Nike — porcentaje</div>',
                    unsafe_allow_html=True)
        parent_summary = (
            df.groupby("parent_brand", observed=True)
            .agg(n=("product_id", "count"),
                 sale=("sale_price_inr", "mean"))
            .reset_index()
        )
        fig_donut = go.Figure(go.Pie(
            labels=parent_summary["parent_brand"],
            values=parent_summary["n"],
            hole=0.55,
            marker=dict(colors=[PARENT_BRAND_COLORS.get(p, VIZ["structural"])
                                for p in parent_summary["parent_brand"]]),
            textposition="outside",
            textinfo="label+percent",
            textfont=dict(color=VIZ["axis_text"], size=14, family="Inter"),
            hovertemplate="<b>%{label}</b><br>%{value:,} productos<br>%{percent}<extra></extra>",
        ))
        fig_donut.update_layout(**plotly_layout, height=380)
        st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown('<div class="section-title">Distribución por rango de precio (₹)</div>',
                unsafe_allow_html=True)
    price_dist = (
        df.dropna(subset=["price_bucket"])
        .groupby(["price_bucket", "parent_brand"], observed=True)
        .size().reset_index(name="n")
    )
    fig_price_dist = px.bar(
        price_dist, x="price_bucket", y="n", color="parent_brand",
        color_discrete_map=PARENT_BRAND_COLORS, barmode="group",
        labels={"price_bucket": "Rango de sale price (₹)", "n": "Productos"},
    )
    fig_price_dist.update_layout(**plotly_layout, height=320, legend_title_text="Casa")
    st.plotly_chart(fig_price_dist, use_container_width=True)

    # ── Brand quadrant — el "estrellas / problemas / nicho / deadweight" ──
    st.markdown('<div class="section-title">Cuadrante de marcas — precio vs rating</div>',
                unsafe_allow_html=True)
    brand_quad = (
        df[rated_mask]
        .groupby(["brand_name", "parent_brand"], observed=True)
        .agg(price=("sale_price_inr", "mean"),
             rating=("rating", "mean"),
             n=("product_id", "count"),
             reviews=("reviews_count", "sum"),
             disc=("discount_pct", "mean"))
        .reset_index()
        .dropna(subset=["price", "rating"])
        .query("n >= 5")
    )
    if not brand_quad.empty:
        median_price = brand_quad["price"].median()
        median_rating = brand_quad["rating"].median()
        fig_quad = px.scatter(
            brand_quad, x="price", y="rating", size="n",
            color="parent_brand", color_discrete_map=PARENT_BRAND_COLORS,
            text="brand_name", size_max=72,
            hover_data={
                "n": True, "reviews": True, "disc": ":.0f",
                "price": ":,.0f", "rating": ":.2f",
                "brand_name": False, "parent_brand": False,
            },
            labels={"price": "Sale price promedio (₹)", "rating": "Rating promedio"},
        )
        fig_quad.update_traces(
            textposition="top center",
            textfont=dict(size=11, color=VIZ["axis_text"], family="Inter"),
        )
        fig_quad.add_vline(x=median_price, line_color=VIZ["reference"],
                           line_dash="dot")
        fig_quad.add_hline(y=median_rating, line_color=VIZ["reference"],
                           line_dash="dot")
        # Etiquetas de cuadrante — semántica estable (verde=bueno, rojo=malo, gris=neutro)
        x_hi, x_lo = brand_quad["price"].max(), brand_quad["price"].min()
        y_hi, y_lo = brand_quad["rating"].max(), brand_quad["rating"].min()
        for x, y, txt, color in [
            (x_hi, y_hi, "⭐ Premium adoradas", VIZ["positive"]),
            (x_hi, y_lo, "🔥 Caras + flojas",   VIZ["alert"]),
            (x_lo, y_hi, "🌱 Asequibles top",   VIZ["positive"]),
            (x_lo, y_lo, "⚓ Asequibles flojas", VIZ["reference"]),
        ]:
            fig_quad.add_annotation(
                x=x, y=y, text=f"<b>{txt}</b>", showarrow=False,
                font=dict(size=10, color=color),
                bgcolor=VIZ["chart_bg"],
                bordercolor=color, borderwidth=1, borderpad=4,
                xanchor="right" if x == x_hi else "left",
                yanchor="top" if y == y_hi else "bottom",
            )
        fig_quad.update_layout(
            **plotly_layout, height=420,
            xaxis_title="Sale price promedio (₹) — líneas punteadas en medianas",
            yaxis_title="Rating promedio",
            legend_title_text="Casa",
        )
        st.plotly_chart(fig_quad, use_container_width=True)
    else:
        st.info("No hay suficientes marcas con ≥5 productos rateados en la vista.")


# ───────── TAB 2 — PRICING & DESCUENTOS ─────────
with tab2:
    col_a, col_b = st.columns([1.1, 1])

    with col_a:
        st.markdown('<div class="section-title">Histograma de descuentos</div>',
                    unsafe_allow_html=True)
        fig_disc_hist = px.histogram(
            df, x="discount_pct", nbins=20, color="parent_brand",
            color_discrete_map=PARENT_BRAND_COLORS, barmode="overlay", opacity=0.75,
            labels={"discount_pct": "Descuento %", "count": "Productos"},
        )
        # Mean line para anclar la lectura
        mean_disc = df["discount_pct"].mean()
        fig_disc_hist.add_vline(
            x=mean_disc, line_color=VIZ["reference"], line_dash="dash",
            annotation_text=f"media {mean_disc:.1f}%",
            annotation_position="top right",
            annotation_font_color=VIZ["axis_text"],
        )
        fig_disc_hist.update_layout(**plotly_layout, height=360, legend_title_text="Casa")
        st.plotly_chart(fig_disc_hist, use_container_width=True)

    with col_b:
        st.markdown('<div class="section-title">Descuento medio por marca</div>',
                    unsafe_allow_html=True)
        disc_by_brand = (
            df.groupby(["brand_name", "parent_brand"], observed=True)
            .agg(disc=("discount_pct", "mean"), n=("product_id", "count"))
            .reset_index()
            .sort_values("disc", ascending=True)
        )
        fig_disc_brand = px.bar(
            disc_by_brand, x="disc", y="brand_name", orientation="h",
            color="parent_brand", color_discrete_map=PARENT_BRAND_COLORS,
            text=disc_by_brand["disc"].map(lambda v: f"{v:.0f}%"),
            hover_data={"n": True, "disc": ":.1f"},
            labels={"disc": "Descuento promedio %", "brand_name": ""},
        )
        fig_disc_brand.update_traces(textposition="outside")
        # Línea de la media global del slice
        fig_disc_brand.add_vline(
            x=mean_disc, line_color=VIZ["reference"], line_dash="dash",
            annotation_text=f"media {mean_disc:.0f}%",
            annotation_position="top",
            annotation_font_color=VIZ["axis_text"],
        )
        fig_disc_brand.update_layout(**plotly_layout, height=360, legend_title_text="Casa")
        st.plotly_chart(fig_disc_brand, use_container_width=True)

    st.markdown('<div class="section-title">Listing price vs Sale price (con regresión OLS)</div>',
                unsafe_allow_html=True)
    df_scatter = df.dropna(subset=["listing_price_inr"]).copy()
    if not df_scatter.empty:
        try:
            fig_scatter = px.scatter(
                df_scatter, x="listing_price_inr", y="sale_price_inr",
                color="parent_brand", color_discrete_map=PARENT_BRAND_COLORS,
                opacity=0.55, hover_name="product_name",
                hover_data={"brand_name": True, "discount_pct": ":.0f",
                            "listing_price_inr": ":,.0f", "sale_price_inr": ":,.0f",
                            "parent_brand": False},
                labels={"listing_price_inr": "Listing price (₹)",
                        "sale_price_inr": "Sale price (₹)"},
                trendline="ols", trendline_scope="overall",
                trendline_color_override=VIZ["emphasis"],
            )
        except Exception:
            fig_scatter = px.scatter(
                df_scatter, x="listing_price_inr", y="sale_price_inr",
                color="parent_brand", color_discrete_map=PARENT_BRAND_COLORS,
                opacity=0.55, hover_name="product_name",
                hover_data={"brand_name": True, "discount_pct": ":.0f",
                            "listing_price_inr": ":,.0f", "sale_price_inr": ":,.0f",
                            "parent_brand": False},
                labels={"listing_price_inr": "Listing price (₹)",
                        "sale_price_inr": "Sale price (₹)"},
            )
        # Línea de identidad y=x → sin descuento
        max_val = max(df_scatter["listing_price_inr"].max(), df_scatter["sale_price_inr"].max())
        fig_scatter.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                              line=dict(color=VIZ["reference"], dash="dot", width=1))
        fig_scatter.add_annotation(x=max_val * 0.92, y=max_val * 0.96, text="sin descuento",
                                   showarrow=False,
                                   font=dict(color=VIZ["reference"], size=10))
        fig_scatter.update_layout(**plotly_layout, height=420, legend_title_text="Casa")
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Todos los productos en vista tienen listing_price NULL (out of stock).")

    st.markdown('<div class="section-title">Top 10 descuentos absolutos (₹ ahorrados)</div>',
                unsafe_allow_html=True)
    top_savings = df.dropna(subset=["listing_price_inr"]).copy()
    if not top_savings.empty:
        top_savings["savings_inr"] = top_savings["listing_price_inr"] - top_savings["sale_price_inr"]
        top_savings = top_savings.nlargest(10, "savings_inr")[
            ["product_name", "brand_name", "listing_price_inr", "sale_price_inr",
             "savings_inr", "discount_pct", "rating"]
        ].rename(columns={
            "product_name": "Producto", "brand_name": "Marca",
            "listing_price_inr": "Listing ₹", "sale_price_inr": "Sale ₹",
            "savings_inr": "Ahorro ₹", "discount_pct": "% off",
            "rating": "★",
        })
        st.dataframe(top_savings, use_container_width=True, hide_index=True, height=380)


# ───────── TAB 3 — CALIDAD PERCIBIDA ─────────
with tab3:
    col_a, col_b = st.columns([1, 1.2])

    with col_a:
        st.markdown('<div class="section-title">Distribución de ratings</div>',
                    unsafe_allow_html=True)
        rated = df[rated_mask]
        if not rated.empty:
            rating_dist = (
                rated.dropna(subset=["rating_bucket"])
                .groupby(["rating_bucket", "parent_brand"], observed=True)
                .size().reset_index(name="n")
            )
            fig_rating = px.bar(
                rating_dist, x="rating_bucket", y="n",
                color="parent_brand", color_discrete_map=PARENT_BRAND_COLORS,
                barmode="group",
                labels={"rating_bucket": "Rango de rating", "n": "Productos"},
            )
            fig_rating.update_layout(**plotly_layout, height=360, legend_title_text="Casa")
            st.plotly_chart(fig_rating, use_container_width=True)
        else:
            st.info("No hay productos con rating en la vista.")

    with col_b:
        st.markdown('<div class="section-title">Rating vs popularidad (n reviews)</div>',
                    unsafe_allow_html=True)
        rated = df[rated_mask & (df["reviews_count"] > 0)]
        if not rated.empty:
            fig_pop = px.scatter(
                rated, x="reviews_count", y="rating",
                color="parent_brand", color_discrete_map=PARENT_BRAND_COLORS,
                size="sale_price_inr", size_max=24, opacity=0.6,
                hover_name="product_name",
                hover_data={"brand_name": True, "sale_price_inr": ":,.0f",
                            "reviews_count": True, "rating": ":.1f",
                            "parent_brand": False},
                labels={"reviews_count": "Número de reviews",
                        "rating": "Rating", "sale_price_inr": "Sale price"},
                log_x=True,
            )
            fig_pop.update_layout(**plotly_layout, height=360, legend_title_text="Casa")
            st.plotly_chart(fig_pop, use_container_width=True)
        else:
            st.info("Sin productos con reviews para graficar.")

    st.markdown('<div class="section-title">Heatmap precio × rating</div>',
                unsafe_allow_html=True)
    heat_df = df.dropna(subset=["price_bucket", "rating_bucket"]).copy()
    if not heat_df.empty:
        heat = (
            heat_df.groupby(["rating_bucket", "price_bucket"], observed=True)
            .size().reset_index(name="n")
        )
        heat_pivot = heat.pivot(index="rating_bucket", columns="price_bucket", values="n").fillna(0)
        fig_heat = go.Figure(go.Heatmap(
            z=heat_pivot.values,
            x=[str(c) for c in heat_pivot.columns],
            y=[str(r) for r in heat_pivot.index],
            colorscale=SEQUENTIAL_SCALE,
            hovertemplate="Rating %{y} · Precio %{x}<br>%{z:,} productos<extra></extra>",
        ))
        fig_heat.update_layout(**plotly_layout, height=320,
                               xaxis_title="Rango de precio (₹)",
                               yaxis_title="Rating")
        st.plotly_chart(fig_heat, use_container_width=True)

    # ── Pareto de concentración de reviews (¿qué % de productos acumula 80% reviews?)
    st.markdown('<div class="section-title">Pareto de reviews — concentración de la "voz del cliente"</div>',
                unsafe_allow_html=True)
    prod_rev = df[df["reviews_count"] > 0].sort_values("reviews_count", ascending=False).copy()
    if not prod_rev.empty:
        total_reviews = prod_rev["reviews_count"].sum()
        prod_rev["cum_share"] = prod_rev["reviews_count"].cumsum() / total_reviews
        prod_rev["rank"] = np.arange(1, len(prod_rev) + 1)

        # Productos para 50% y 80% acumulado
        rank_50 = int(prod_rev.loc[prod_rev["cum_share"] >= 0.5, "rank"].iloc[0]) \
            if (prod_rev["cum_share"] >= 0.5).any() else len(prod_rev)
        rank_80 = int(prod_rev.loc[prod_rev["cum_share"] >= 0.8, "rank"].iloc[0]) \
            if (prod_rev["cum_share"] >= 0.8).any() else len(prod_rev)
        share_top5pct = float(
            prod_rev.head(max(1, int(len(prod_rev) * 0.05)))["reviews_count"].sum() / total_reviews
        )

        top_show = prod_rev.head(min(200, len(prod_rev)))
        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(
            x=top_show["rank"], y=top_show["reviews_count"],
            marker_color=VIZ["structural"], name="Reviews del producto",
            hovertemplate="Producto #%{x}<br>Reviews: %{y:,}<extra></extra>",
        ))
        fig_pareto.add_trace(go.Scatter(
            x=prod_rev["rank"], y=prod_rev["cum_share"], yaxis="y2",
            mode="lines",
            line=dict(color=VIZ["alert"], width=2.5),
            name="Acumulado",
            hovertemplate="Top %{x} productos<br>Acumulado: %{y:.1%}<extra></extra>",
        ))
        fig_pareto.add_vline(
            x=rank_50, line_color=VIZ["reference"], line_dash="dot",
            annotation_text=f"50% en top {rank_50}",
            annotation_position="top",
            annotation_font_color=VIZ["axis_text"],
        )
        fig_pareto.add_vline(
            x=rank_80, line_color=VIZ["reference"], line_dash="dot",
            annotation_text=f"80% en top {rank_80}",
            annotation_position="top",
            annotation_font_color=VIZ["axis_text"],
        )
        layout_pareto = dict(plotly_layout)
        layout_pareto["yaxis"] = dict(
            gridcolor=VIZ["grid"], title="Reviews por producto",
        )
        layout_pareto["yaxis2"] = dict(
            overlaying="y", side="right", showgrid=False,
            tickformat=".0%", title="Acumulado", range=[0, 1.02],
        )
        fig_pareto.update_layout(**layout_pareto, height=420,
                                 xaxis_title="Ranking de productos por reviews",
                                 legend_title_text="")
        st.plotly_chart(fig_pareto, use_container_width=True)
        st.caption(
            f"📍 El **top 5% de productos** ({max(1, int(len(prod_rev)*0.05))} de "
            f"{len(prod_rev):,}) concentra el **{share_top5pct:.0%}** de todas las "
            f"reviews. Riesgo: el catálogo opera bajo el efecto de unos pocos "
            f"productos-estrella; el resto vive en la cola larga sin tracción social."
        )
    else:
        share_top5pct = float("nan")
        rank_50 = rank_80 = 0
        st.info("Ningún producto en la vista tiene reviews.")

    st.markdown('<div class="section-title">Top productos por rating (≥10 reviews)</div>',
                unsafe_allow_html=True)
    top_rated = df[rated_mask & (df["reviews_count"] >= 10)].copy()
    if not top_rated.empty:
        top_rated = top_rated.nlargest(15, ["rating", "reviews_count"])[
            ["product_name", "brand_name", "rating", "reviews_count",
             "sale_price_inr", "discount_pct"]
        ].rename(columns={
            "product_name": "Producto", "brand_name": "Marca",
            "rating": "★", "reviews_count": "Reviews",
            "sale_price_inr": "Precio ₹", "discount_pct": "% off",
        })
        st.dataframe(top_rated, use_container_width=True, hide_index=True, height=440)


# ─────────────────────────────────────────────────────────────
# Lectura analítica
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Lectura analítica</div>', unsafe_allow_html=True)

n_adidas = (df["parent_brand"] == "Adidas").sum()
n_nike = (df["parent_brand"] == "Nike").sum()
adidas_price = df[df["parent_brand"] == "Adidas"]["sale_price_inr"].mean()
nike_price = df[df["parent_brand"] == "Nike"]["sale_price_inr"].mean()
adidas_disc = df[df["parent_brand"] == "Adidas"]["discount_pct"].mean()
nike_disc = df[df["parent_brand"] == "Nike"]["discount_pct"].mean()

# Mejor relación precio/rating por brand
by_brand = (
    df[rated_mask]
    .groupby("brand_name", observed=True)
    .agg(rating=("rating", "mean"),
         price=("sale_price_inr", "mean"),
         n=("product_id", "count"))
    .query("n >= 10")
)
if not by_brand.empty:
    by_brand["score"] = by_brand["rating"] / (by_brand["price"] / 1000)  # rating por cada 1K INR
    best_value = by_brand["score"].idxmax()
    best_rating = by_brand["rating"].max()
    best_price = by_brand.loc[best_value, "price"]
    value_phrase = (
        f"La marca con mejor relación precio/rating es <b>{best_value}</b> "
        f"con <b>{best_rating:.2f}★</b> a un precio medio de <b>{fmt_inr(best_price)}</b>."
    )
else:
    value_phrase = ""

heavy_disc_pct = (df["discount_pct"] >= 50).sum() / len(df) if len(df) else 0

verdict_emoji = "🧡" if n_adidas > n_nike else "🖤"
who_leads = "Adidas" if n_adidas > n_nike else "Nike"
share_leader = max(n_adidas, n_nike) / max(n_adidas + n_nike, 1)

st.markdown(
    f"""
    <div class="insight-box">
    👟 <b>Adidas</b> aporta <b>{fmt_int(n_adidas)}</b> productos y
    <b>Nike</b> aporta <b>{fmt_int(n_nike)}</b> en la vista actual.
    Precio medio: Adidas <b>{fmt_inr(adidas_price)}</b> vs Nike <b>{fmt_inr(nike_price)}</b>.
    Descuento medio: Adidas <b>{adidas_disc:.1f}%</b> vs Nike <b>{nike_disc:.1f}%</b>.<br><br>

    {value_phrase}<br><br>

    💸 El <b>{heavy_disc_pct:.0%}</b> del catálogo en vista tiene un descuento
    de <b>50% o más</b>, una señal de estrategia agresiva de liquidación o de
    saldo de inventario hacia fin de temporada.<br><br>

    {verdict_emoji} <b>Veredicto:</b> <b>{who_leads}</b> domina este slice del
    catálogo con el <b>{share_leader:.0%}</b> de los productos. La comparación
    cabal Adidas-vs-Nike requiere ponderar también la profundidad de cada marca
    y la estrategia de precios.
    <br><br>
    <span style='color:{CLAUDE_PALETTE["ink_muted"]}; font-size:.85rem;'>
    Datos: scraping de catálogo, snapshot 2020-04-13 · precios en rupias indias.
    </span>
    </div>
    """,
    unsafe_allow_html=True,
)
