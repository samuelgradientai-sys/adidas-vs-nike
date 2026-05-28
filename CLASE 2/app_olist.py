"""
Olist Marketplace Insights · Analaitica
Dashboard ejecutivo del marketplace brasileño Olist (2017-2018).
Proyecto final — Herramientas de Visualización para la Inteligencia de Negocios.

Fuente de datos: Supabase (8 tablas). Las credenciales se leen de un
`.env` local (en desarrollo) o de `st.secrets` (en Streamlit Cloud).
"""
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
# Configuración base
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Olist Marketplace Insights · Analaitica",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

PALETTE = {
    "primary":   "#6366f1",  # violet — branding
    "secondary": "#a855f7",  # fuchsia
    "accent":    "#06b6d4",  # cyan — valor monetario
    "success":   "#22c55e",  # verde — on-time, promoters
    "warning":   "#eab308",  # amarillo — neutral
    "danger":    "#ef4444",  # rojo — retrasos, detractores
    "muted":     "#64748b",
}

# Mapeo oficial sigla → nombre de los 27 estados + DF de Brasil
BR_STATES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
    "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco",
    "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
    "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}


def state_label(sigla: str) -> str:
    """'RJ' -> 'RJ — Rio de Janeiro'. Si la sigla es desconocida, devuelve solo la sigla."""
    nombre = BR_STATES.get(sigla)
    return f"{sigla} — {nombre}" if nombre else sigla

# ─────────────────────────────────────────────────────────────
# Estilos (CSS — replicado verbatim de APP_7.py para consistencia visual)
# ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }

    .stApp {
        background: radial-gradient(circle at 20% 0%, #1a1d2e 0%, #0c0e1a 50%, #07080f 100%);
    }

    .hero {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(168, 85, 247, 0.15));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 24px;
        padding: 32px 40px;
        margin-bottom: 28px;
        backdrop-filter: blur(12px);
        box-shadow: 0 20px 60px rgba(0,0,0,0.35);
    }
    .hero h1 {
        font-size: 2.4rem;
        font-weight: 800;
        margin: 0;
        background: linear-gradient(90deg, #a5b4fc, #f0abfc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero p {
        color: #a3a8c3;
        margin-top: 6px;
        font-size: 1rem;
    }

    .kpi-card {
        background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 22px 24px;
        height: 100%;
        transition: transform 0.25s ease, border 0.25s ease, box-shadow 0.25s ease;
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, var(--accent-from), var(--accent-to));
        opacity: 0.85;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        border-color: rgba(255,255,255,0.18);
        box-shadow: 0 14px 40px rgba(99,102,241,0.18);
    }
    .kpi-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #9aa0c0;
        margin-bottom: 10px;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.1;
    }
    .kpi-delta {
        font-size: 0.82rem;
        margin-top: 8px;
        color: #7dd3fc;
    }
    .kpi-delta.down { color: #fda4af; }
    .kpi-delta.up   { color: #86efac; }

    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #e2e8f0;
        margin: 24px 0 12px 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .section-title::before {
        content: "";
        width: 4px; height: 18px;
        background: linear-gradient(180deg, #6366f1, #a855f7);
        border-radius: 2px;
    }

    .insight-box {
        background: rgba(30, 41, 59, 0.55);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-left: 3px solid #6366f1;
        border-radius: 12px;
        padding: 18px 22px;
        margin-top: 8px;
        color: #cbd5e1;
        line-height: 1.7;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1222 0%, #0a0c18 100%);
        border-right: 1px solid rgba(255,255,255,0.06);
    }

    div[data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.06);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255,255,255,0.03);
        padding: 6px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        padding: 8px 18px;
        color: #94a3b8;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1, #a855f7) !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# Conexión a Supabase
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
        st.error(
            "❌ Faltan `SUPABASE_URL` y/o `SUPABASE_ANON_KEY`. "
            "Configura tu archivo `.env` o `st.secrets`."
        )
        st.stop()
    return create_client(url, key)


def fetch_all(client: Client, table: str, page_size: int = 1000) -> pd.DataFrame:
    """Paginado: PostgREST devuelve máximo ~1000 filas por request."""
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
LOADER_VERSION = "v2-supabase"


@st.cache_data(ttl=300, show_spinner="Cargando dataset Olist desde Supabase…")
def load_orders(_v: str = LOADER_VERSION) -> pd.DataFrame:
    client = get_supabase_client()
    try:
        orders = fetch_all(client, "olist_orders")
        customers = fetch_all(client, "olist_customers")
        payments = fetch_all(client, "olist_order_payments")
        reviews = fetch_all(client, "olist_order_reviews")
        items = fetch_all(client, "olist_order_items")
        sellers = fetch_all(client, "olist_sellers")
        products = fetch_all(client, "olist_products")
        cat_tr = fetch_all(client, "product_category_name_translation")
    except Exception as e:
        st.error(
            "❌ No se pudieron leer las tablas de Supabase. "
            "¿Ejecutaste `supabase_schema.sql` en el SQL Editor y luego "
            "`python load_to_supabase.py` para cargar los CSVs?"
        )
        st.exception(e)
        st.stop()

    # Tipados (Supabase devuelve timestamps como ISO 8601 y numeric como string)
    for c in ["order_purchase_timestamp", "order_approved_at",
              "order_delivered_carrier_date", "order_delivered_customer_date",
              "order_estimated_delivery_date"]:
        orders[c] = pd.to_datetime(orders[c], errors="coerce", utc=True).dt.tz_localize(None)
    for c in ["review_creation_date", "review_answer_timestamp"]:
        reviews[c] = pd.to_datetime(reviews[c], errors="coerce", utc=True).dt.tz_localize(None)
    for c in ["price", "freight_value"]:
        items[c] = pd.to_numeric(items[c], errors="coerce")
    payments["payment_value"] = pd.to_numeric(payments["payment_value"], errors="coerce")

    # Pagos agregados por pedido
    pay_agg = (
        payments.sort_values("payment_value", ascending=False)
        .groupby("order_id")
        .agg(
            payment_value=("payment_value", "sum"),
            payment_installments=("payment_installments", "max"),
            payment_type=("payment_type", "first"),
        )
        .reset_index()
    )

    # Reviews dedup: 1 review por pedido (primera por fecha)
    rev_dedup = (
        reviews.sort_values("review_creation_date")
        .drop_duplicates("order_id", keep="first")
        [["order_id", "review_score", "review_creation_date"]]
    )

    # Items: agregar a nivel pedido + atribuir categoría/seller principal
    items_cat = items.merge(products[["product_id", "product_category_name"]], on="product_id", how="left")
    items_cat = items_cat.merge(cat_tr, on="product_category_name", how="left")
    items_cat["category_en"] = items_cat["product_category_name_english"].fillna(
        items_cat["product_category_name"]
    )
    items_cat = items_cat.merge(sellers[["seller_id", "seller_state"]], on="seller_id", how="left")

    items_agg = (
        items_cat.groupby("order_id")
        .agg(
            items_price_sum=("price", "sum"),
            items_freight_sum=("freight_value", "sum"),
            n_items=("order_item_id", "count"),
            primary_category_en=("category_en", lambda s: s.mode().iloc[0] if not s.mode().empty else np.nan),
            primary_seller_state=("seller_state", lambda s: s.mode().iloc[0] if not s.mode().empty else np.nan),
        )
        .reset_index()
    )

    df = (
        orders
        .merge(customers[["customer_id", "customer_unique_id", "customer_state", "customer_city"]],
               on="customer_id", how="left")
        .merge(pay_agg, on="order_id", how="left")
        .merge(rev_dedup, on="order_id", how="left")
        .merge(items_agg, on="order_id", how="left")
    )

    # Variables derivadas
    df["revenue"] = df["items_price_sum"].fillna(0) + df["items_freight_sum"].fillna(0)
    df["delivery_delay_days"] = (
        df["order_delivered_customer_date"] - df["order_estimated_delivery_date"]
    ).dt.days
    df["actual_delivery_days"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.days
    df["on_time_flag"] = np.where(
        df["order_delivered_customer_date"].notna() & (df["order_status"] == "delivered"),
        (df["delivery_delay_days"] <= 0).astype(float),
        np.nan,
    )
    df["freight_ratio"] = np.where(
        df["items_price_sum"] > 0,
        df["items_freight_sum"] / df["items_price_sum"],
        np.nan,
    )
    df["order_month"] = df["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    df["order_year"] = df["order_purchase_timestamp"].dt.year
    df["review_bucket"] = pd.cut(
        df["review_score"], bins=[0, 2, 3, 5],
        labels=["Detractor (1-2)", "Neutral (3)", "Promoter (4-5)"],
    )
    df["delivery_speed_bucket"] = pd.cut(
        df["actual_delivery_days"], bins=[-1, 3, 7, 14, 30, 1000],
        labels=["≤3d", "4–7d", "8–14d", "15–30d", "30d+"],
    )

    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_items(_v: str = LOADER_VERSION) -> pd.DataFrame:
    client = get_supabase_client()
    try:
        items = fetch_all(client, "olist_order_items")
        products = fetch_all(client, "olist_products")
        sellers = fetch_all(client, "olist_sellers")
        cat_tr = fetch_all(client, "product_category_name_translation")
        orders = fetch_all(client, "olist_orders")
        customers = fetch_all(client, "olist_customers")
    except Exception as e:
        st.error("❌ No se pudieron leer las tablas de Supabase.")
        st.exception(e)
        st.stop()

    orders = orders[["order_id", "order_status", "order_purchase_timestamp", "customer_id"]].copy()
    orders["order_purchase_timestamp"] = pd.to_datetime(
        orders["order_purchase_timestamp"], errors="coerce", utc=True
    ).dt.tz_localize(None)
    customers = customers[["customer_id", "customer_state"]]
    for c in ["price", "freight_value"]:
        items[c] = pd.to_numeric(items[c], errors="coerce")

    df = (
        items
        .merge(products[["product_id", "product_category_name"]], on="product_id", how="left")
        .merge(cat_tr, on="product_category_name", how="left")
        .merge(sellers[["seller_id", "seller_state"]], on="seller_id", how="left")
        .merge(orders, on="order_id", how="left")
        .merge(customers, on="customer_id", how="left")
    )
    df["category_en"] = df["product_category_name_english"].fillna(df["product_category_name"])
    df["line_revenue"] = df["price"] + df["freight_value"]
    return df


df_orders = load_orders()
df_items = load_items()


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def fmt_money_brl(v: float) -> str:
    if pd.isna(v):
        return "—"
    if abs(v) >= 1e9:
        return f"R$ {v/1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"R$ {v/1e6:,.2f}M"
    if abs(v) >= 1e3:
        return f"R$ {v/1e3:,.1f}K"
    return f"R$ {v:,.0f}"


def fmt_int(v: float) -> str:
    if pd.isna(v):
        return "—"
    return f"{int(v):,}".replace(",", ".")


def kpi_card(label: str, value: str, accent_from: str, accent_to: str, delta: str = "", delta_dir: str = "") -> str:
    delta_class = f"kpi-delta {delta_dir}" if delta_dir else "kpi-delta"
    delta_html = f'<div class="{delta_class}">{delta}</div>' if delta else ""
    return f"""
    <div class="kpi-card" style="--accent-from:{accent_from};--accent-to:{accent_to};">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """


def delta_str(curr: float, prev: float, fmt) -> tuple[str, str]:
    if prev is None or pd.isna(prev) or prev == 0 or pd.isna(curr):
        return "", ""
    pct = (curr - prev) / prev
    arrow = "▲" if pct >= 0 else "▼"
    direction = "up" if pct >= 0 else "down"
    return f"{arrow} {pct:+.1%} vs período anterior", direction


# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='padding:8px 4px 18px 4px;'>"
        "<div style='font-size:0.72rem;letter-spacing:0.18em;color:#818cf8;font-weight:600;'>ANALAITICA</div>"
        "<div style='font-size:1.25rem;font-weight:700;color:#fff;margin-top:4px;'>Olist Marketplace Insights</div>"
        "<div style='font-size:0.72rem;color:#64748b;margin-top:6px;'>Fuente: Supabase · CC BY-NC-SA 4.0</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    if st.button("🔄 Refrescar datos desde Supabase", use_container_width=True,
                 help="Vacía la caché (TTL 5 min) y vuelve a leer las 8 tablas en vivo."):
        load_orders.clear()
        load_items.clear()
        st.rerun()

    min_date = pd.Timestamp("2017-01-01").date()
    max_date = pd.Timestamp("2018-08-31").date()
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_in = st.date_input(
            "Desde", value=min_date,
            min_value=min_date, max_value=max_date,
            format="YYYY-MM-DD",
            help="Fecha inicial del análisis. El dataset cubre Sep 2016 - Oct 2018, "
                 "pero limitamos al rango Ene 2017 - Ago 2018 porque los meses extremos "
                 "tienen cobertura parcial y distorsionan las series temporales.",
        )
    with col_d2:
        end_in = st.date_input(
            "Hasta", value=max_date,
            min_value=min_date, max_value=max_date,
            format="YYYY-MM-DD",
            help="Fecha final del análisis. Filtra por `order_purchase_timestamp` "
                 "(fecha de compra del pedido).",
        )
    date_start, date_end = pd.Timestamp(start_in), pd.Timestamp(end_in)
    if date_end < date_start:
        st.warning("La fecha 'Hasta' es anterior a 'Desde'. Se invierte el orden.")
        date_start, date_end = date_end, date_start

    estados = sorted(df_orders["customer_state"].dropna().unique())
    estado_sel = st.multiselect(
        "Estado del cliente", estados, default=[],
        format_func=state_label,
        help="Filtra los pedidos por estado brasileño del comprador. Las opciones muestran "
             "la sigla oficial seguida del nombre (ej. 'RJ — Rio de Janeiro'). "
             "Vacío = todos los 27 estados. Útil para zoom geográfico.",
    )

    cats = sorted(df_orders["primary_category_en"].dropna().unique())
    cat_sel = st.multiselect(
        "Categoría principal", cats, default=[],
        help="Filtra por categoría dominante del pedido (en inglés, traducida del "
             "portugués). Si un pedido tiene varios productos, se usa la categoría "
             "que más se repite. Vacío = todas las categorías.",
    )

    statuses = sorted(df_orders["order_status"].dropna().unique())
    status_sel = st.multiselect(
        "Estado del pedido", statuses, default=["delivered"],
        help="Estado del ciclo de vida del pedido: delivered = entregado al cliente, "
             "shipped = en tránsito, canceled = cancelado, etc. Por defecto solo "
             "'delivered' para ver 'negocio cerrado'. Si lo quitas, los KPIs incluyen "
             "cancelaciones y pedidos en proceso.",
    )

    st.markdown("---")
    st.caption(f"Pedidos totales: **{len(df_orders):,}**")
    st.caption(f"Cobertura: **{df_orders['order_purchase_timestamp'].min():%b %Y} → "
               f"{df_orders['order_purchase_timestamp'].max():%b %Y}**")


# ─────────────────────────────────────────────────────────────
# Filtrado
# ─────────────────────────────────────────────────────────────
def apply_mask(df: pd.DataFrame, ts_col: str, state_col: str, cat_col: str | None = None) -> pd.DataFrame:
    mask = df[ts_col].between(date_start, date_end + pd.Timedelta(days=1))
    if estado_sel:
        mask &= df[state_col].isin(estado_sel)
    if cat_sel and cat_col and cat_col in df.columns:
        mask &= df[cat_col].isin(cat_sel)
    if status_sel and "order_status" in df.columns:
        mask &= df["order_status"].isin(status_sel)
    return df[mask]


df_view = apply_mask(df_orders, "order_purchase_timestamp", "customer_state", "primary_category_en")
df_items_view = apply_mask(df_items, "order_purchase_timestamp", "customer_state", "category_en")


# ─────────────────────────────────────────────────────────────
# Análisis del slice (sidebar dinámico — debajo de los filtros)
# ─────────────────────────────────────────────────────────────
def render_slice_analysis() -> None:
    """Compara el slice filtrado vs el universo global del mismo order_status."""
    with st.sidebar:
        st.markdown("---")
        st.markdown(
            "<div style='font-size:0.72rem;text-transform:uppercase;"
            "letter-spacing:0.18em;color:#818cf8;font-weight:600;margin-bottom:6px;'>"
            "🔍 Análisis del slice</div>",
            unsafe_allow_html=True,
        )

        n_view = len(df_view)
        pct_view = n_view / max(len(df_orders), 1)
        st.caption(f"**{n_view:,}** pedidos · {pct_view:.1%} del total")

        if n_view == 0:
            st.caption("⚠️ Sin pedidos para los filtros actuales.")
            return

        # Referencia global: mismo order_status pero sin filtros geográficos/categóricos/de fecha
        ref = df_orders[df_orders["order_status"].isin(status_sel)] if status_sel else df_orders
        if len(ref) == 0:
            ref = df_orders

        def arrow_pp(delta_pp: float) -> str:
            return "↑" if delta_pp > 0.5 else ("↓" if delta_pp < -0.5 else "≈")

        def arrow_pct(delta: float) -> str:
            return "↑" if delta > 0.02 else ("↓" if delta < -0.02 else "≈")

        # 💳 Método de pago dominante
        pay_local = df_view["payment_type"].value_counts(normalize=True).dropna()
        pay_ref = ref["payment_type"].value_counts(normalize=True).dropna()
        if not pay_local.empty:
            top_pay = pay_local.idxmax()
            share_local = pay_local.iloc[0]
            share_ref = pay_ref.get(top_pay, 0)
            delta_pp = (share_local - share_ref) * 100
            st.caption(
                f"💳 **{top_pay}** {share_local:.0%} "
                f"({arrow_pp(delta_pp)} {abs(delta_pp):.0f}pp vs global)"
            )

        # 🎯 Ticket promedio
        n_loc = df_view["order_id"].nunique()
        n_ref = ref["order_id"].nunique()
        if n_loc and n_ref:
            ticket_local = df_view["revenue"].sum() / n_loc
            ticket_ref = ref["revenue"].sum() / n_ref
            delta = (ticket_local - ticket_ref) / ticket_ref if ticket_ref else 0
            st.caption(
                f"🎯 Ticket **{fmt_money_brl(ticket_local)}** "
                f"({arrow_pct(delta)} {abs(delta):.0%} vs global)"
            )

        # 🚚 On-time delivery
        ot_local = df_view["on_time_flag"].mean()
        ot_ref = ref["on_time_flag"].mean()
        if pd.notna(ot_local) and pd.notna(ot_ref):
            delta_pp = (ot_local - ot_ref) * 100
            flag = "🟢" if ot_local >= 0.90 else "🟡"
            st.caption(
                f"🚚 On-time **{ot_local:.0%}** {flag} "
                f"({arrow_pp(delta_pp)} {abs(delta_pp):.0f}pp vs global)"
            )

        # ⭐ Review medio
        rv_local = df_view["review_score"].mean()
        rv_ref = ref["review_score"].mean()
        if pd.notna(rv_local) and pd.notna(rv_ref):
            delta = rv_local - rv_ref
            arrow = "↑" if delta > 0.05 else ("↓" if delta < -0.05 else "≈")
            st.caption(
                f"⭐ Review **{rv_local:.2f}** "
                f"({arrow} {abs(delta):.2f} vs {rv_ref:.2f} global)"
            )

        # 🛍 Categoría líder (solo si no filtraste por categoría)
        if not cat_sel:
            cat_rev = (
                df_view.dropna(subset=["primary_category_en"])
                .groupby("primary_category_en")["revenue"].sum()
                .sort_values(ascending=False)
            )
            if not cat_rev.empty:
                top_cat = cat_rev.index[0]
                share = cat_rev.iloc[0] / cat_rev.sum()
                st.caption(f"🛍 Top categoría: **{top_cat}** ({share:.0%} del GMV)")

        # 📍 Estado líder (solo si no filtraste por estado)
        if not estado_sel:
            st_rev = (
                df_view.dropna(subset=["customer_state"])
                .groupby("customer_state")["revenue"].sum()
                .sort_values(ascending=False)
            )
            if not st_rev.empty:
                top_st = st_rev.index[0]
                share = st_rev.iloc[0] / st_rev.sum()
                st.caption(f"📍 Top estado: **{state_label(top_st)}** ({share:.0%} del GMV)")


render_slice_analysis()

# Período anterior (mismo largo, inmediatamente previo) para deltas
window = date_end - date_start
prev_start = date_start - window - pd.Timedelta(days=1)
prev_end = date_start - pd.Timedelta(days=1)
df_prev = df_orders[df_orders["order_purchase_timestamp"].between(prev_start, prev_end)]
if estado_sel:
    df_prev = df_prev[df_prev["customer_state"].isin(estado_sel)]
if cat_sel:
    df_prev = df_prev[df_prev["primary_category_en"].isin(cat_sel)]
if status_sel:
    df_prev = df_prev[df_prev["order_status"].isin(status_sel)]


# ─────────────────────────────────────────────────────────────
# Hero
# ─────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="hero">
        <h1>🛒 Olist Marketplace</h1>
        <p>Análisis retrospectivo del marketplace brasileño ·
        {date_start:%b %Y} → {date_end:%b %Y} ·
        {len(df_view):,} pedidos en vista</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────────────────────
gmv = df_view["revenue"].sum()
n_orders = df_view["order_id"].nunique()
avg_ticket = gmv / n_orders if n_orders else 0
on_time = df_view["on_time_flag"].mean()
avg_review = df_view["review_score"].mean()

# Prev period equivalents
prev_gmv = df_prev["revenue"].sum()
prev_orders = df_prev["order_id"].nunique()
prev_ticket = prev_gmv / prev_orders if prev_orders else None
prev_ontime = df_prev["on_time_flag"].mean()
prev_review = df_prev["review_score"].mean()

d_gmv, dd_gmv = delta_str(gmv, prev_gmv, fmt_money_brl)
d_ord, dd_ord = delta_str(n_orders, prev_orders, fmt_int)
d_tic, dd_tic = delta_str(avg_ticket, prev_ticket, fmt_money_brl)
d_ot,  dd_ot  = delta_str(on_time, prev_ontime, lambda v: f"{v:.1%}")
d_rv,  dd_rv  = delta_str(avg_review, prev_review, lambda v: f"{v:.2f}")

cols = st.columns(5)
cards = [
    ("GMV",                fmt_money_brl(gmv),        "#06b6d4", "#3b82f6", d_gmv, dd_gmv),
    ("Pedidos",            fmt_int(n_orders),         "#f97316", "#ef4444", d_ord, dd_ord),
    ("Ticket promedio",    fmt_money_brl(avg_ticket), "#eab308", "#f59e0b", d_tic, dd_tic),
    ("On-time delivery",   f"{on_time:.1%}" if pd.notna(on_time) else "—",
                                                       "#10b981", "#22c55e", d_ot,  dd_ot),
    ("Review medio",       f"{avg_review:.2f} ★" if pd.notna(avg_review) else "—",
                                                       "#6366f1", "#a855f7", d_rv,  dd_rv),
]
for col, (label, value, c1, c2, dlt, ddir) in zip(cols, cards):
    col.markdown(kpi_card(label, value, c1, c2, dlt, ddir), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Layout Plotly compartido
# ─────────────────────────────────────────────────────────────
plotly_layout = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(255,255,255,0.02)",
    font=dict(color="#cbd5e1", family="Inter"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
    legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
    margin=dict(l=10, r=10, t=30, b=10),
)


# ─────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📈 Crecimiento", "🚚 Logística & Satisfacción", "🛍 Categorías & Sellers"])


# ───────── TAB 1 — CRECIMIENTO ─────────
with tab1:
    st.markdown('<div class="section-title">Evolución mensual de GMV y volumen de pedidos</div>',
                unsafe_allow_html=True)
    monthly = (
        df_view.groupby("order_month")
        .agg(gmv=("revenue", "sum"), n_orders=("order_id", "nunique"))
        .reset_index()
        .sort_values("order_month")
    )
    fig1 = go.Figure()
    # Tooltips enriquecidos: además del valor, incluyen el ticket promedio
    # del mes, una pista de contexto que el ejecutivo busca al pasar el cursor.
    monthly["avg_ticket_hover"] = monthly["gmv"] / monthly["n_orders"]
    fig1.add_trace(go.Scatter(
        x=monthly["order_month"], y=monthly["gmv"],
        name="GMV", mode="lines+markers",
        line=dict(color=PALETTE["accent"], width=3),
        fill="tozeroy", fillcolor="rgba(6,182,212,0.15)",
        customdata=monthly[["n_orders", "avg_ticket_hover"]].values,
        hovertemplate=(
            "<b>%{x|%b %Y}</b><br>"
            "GMV: R$ %{y:,.0f}<br>"
            "Pedidos: %{customdata[0]:,}<br>"
            "Ticket: R$ %{customdata[1]:,.0f}<extra></extra>"
        ),
    ))
    fig1.add_trace(go.Scatter(
        x=monthly["order_month"], y=monthly["n_orders"],
        name="Pedidos", mode="lines+markers", yaxis="y2",
        line=dict(color=PALETTE["secondary"], width=3, dash="dot"),
        hovertemplate="<b>%{x|%b %Y}</b><br>Pedidos: %{y:,}<extra></extra>",
    ))
    layout1 = dict(plotly_layout)
    layout1["yaxis"] = dict(gridcolor="rgba(255,255,255,0.06)", title="GMV (R$)", tickformat=",.0f")
    layout1["yaxis2"] = dict(overlaying="y", side="right", showgrid=False, title="Pedidos")
    fig1.update_layout(**layout1, height=400)
    st.plotly_chart(fig1, use_container_width=True)

    col_a, col_b = st.columns([1.2, 1])

    with col_a:
        st.markdown('<div class="section-title">Ticket promedio vs volumen mensual</div>',
                    unsafe_allow_html=True)
        monthly["avg_ticket"] = monthly["gmv"] / monthly["n_orders"]
        monthly["year"] = monthly["order_month"].dt.year.astype(str)
        try:
            fig2 = px.scatter(
                monthly, x="n_orders", y="avg_ticket", size="gmv", color="year",
                color_discrete_sequence=[PALETTE["accent"], PALETTE["secondary"], PALETTE["warning"]],
                trendline="ols", trendline_color_override="#a855f7",
                hover_data={"order_month": "|%b %Y", "gmv": ":,.0f"},
            )
        except Exception:
            fig2 = px.scatter(
                monthly, x="n_orders", y="avg_ticket", size="gmv", color="year",
                color_discrete_sequence=[PALETTE["accent"], PALETTE["secondary"], PALETTE["warning"]],
                hover_data={"order_month": "|%b %Y", "gmv": ":,.0f"},
            )
        fig2.update_layout(**plotly_layout, height=360,
                           xaxis_title="Pedidos en el mes", yaxis_title="Ticket promedio (R$)")
        st.plotly_chart(fig2, use_container_width=True)

    with col_b:
        st.markdown('<div class="section-title">Mix de método de pago</div>',
                    unsafe_allow_html=True)
        pay_mix = (
            df_view.dropna(subset=["payment_type"])
            .groupby(["order_month", "payment_type"])
            .size().reset_index(name="n")
        )
        if not pay_mix.empty:
            pay_mix["share"] = pay_mix.groupby("order_month")["n"].transform(lambda s: s / s.sum())
            color_map_pay = {
                "credit_card": PALETTE["accent"],
                "boleto":      PALETTE["warning"],
                "voucher":     PALETTE["secondary"],
                "debit_card":  PALETTE["success"],
                "not_defined": PALETTE["muted"],
            }
            # Barras apiladas al 100% — los notebooks recomiendan barras en lugar
            # de área apilada cuando lo que importa es comparar composición.
            fig3 = px.bar(
                pay_mix, x="order_month", y="share", color="payment_type",
                color_discrete_map=color_map_pay, barmode="stack",
                hover_data={"share": ":.1%", "n": True, "order_month": "|%b %Y"},
            )
            fig3.update_layout(**plotly_layout, height=360, yaxis_tickformat=".0%",
                               yaxis_title="Participación", bargap=0.12,
                               legend_title_text="Método")
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No hay datos de pago para los filtros seleccionados.")


# ───────── TAB 2 — LOGÍSTICA & SATISFACCIÓN ─────────
with tab2:
    st.markdown('<div class="section-title">Tiempo de entrega vs calificación del cliente</div>',
                unsafe_allow_html=True)
    df_heat = df_view.dropna(subset=["delivery_speed_bucket", "review_score"])
    if not df_heat.empty:
        fig4 = px.density_heatmap(
            df_heat, x="delivery_speed_bucket", y="review_score",
            nbinsy=5, color_continuous_scale="Inferno",
            category_orders={"delivery_speed_bucket": ["≤3d", "4–7d", "8–14d", "15–30d", "30d+"]},
        )
        fig4.update_layout(**plotly_layout, height=380,
                           xaxis_title="Tiempo real de entrega",
                           yaxis_title="Review (1-5)",
                           coloraxis_colorbar=dict(title="Pedidos"))
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No hay datos suficientes para el heatmap.")

    col_l, col_r = st.columns([1.2, 1])

    with col_l:
        st.markdown('<div class="section-title">On-time delivery por estado (peores arriba)</div>',
                    unsafe_allow_html=True)
        by_state = (
            df_view.dropna(subset=["on_time_flag"])
            .groupby("customer_state")
            .agg(on_time=("on_time_flag", "mean"),
                 n=("order_id", "nunique"))
            .reset_index()
            .query("n >= 50")
            .sort_values("on_time")
            .head(15)
        )
        if not by_state.empty:
            mean_ot = df_view["on_time_flag"].mean()
            fig5 = px.bar(
                by_state, x="on_time", y="customer_state", orientation="h",
                color="on_time",
                color_continuous_scale=[(0, PALETTE["danger"]),
                                        (0.5, PALETTE["warning"]),
                                        (1, PALETTE["success"])],
                range_color=[0.7, 1.0],
                text=by_state["on_time"].map(lambda v: f"{v:.0%}"),
                hover_data={"n": True, "on_time": ":.1%"},
            )
            fig5.update_traces(textposition="outside")
            fig5.add_vline(x=mean_ot, line_color="#94a3b8", line_dash="dot",
                           annotation_text=f"media {mean_ot:.0%}",
                           annotation_position="top right",
                           annotation_font_color="#94a3b8")
            fig5.update_layout(**plotly_layout, height=440,
                               xaxis_tickformat=".0%", coloraxis_showscale=False,
                               yaxis_title="", xaxis_title="On-time %")
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("No hay estados con suficientes pedidos en los filtros.")

    with col_r:
        st.markdown('<div class="section-title">Distribución de reseñas</div>',
                    unsafe_allow_html=True)
        rev_dist = (
            df_view.dropna(subset=["review_score"])
            .groupby("review_score").size().reset_index(name="n")
        )
        if not rev_dist.empty:
            rev_dist["share"] = rev_dist["n"] / rev_dist["n"].sum()
            score_colors = {1: "#ef4444", 2: "#f97316", 3: "#eab308",
                            4: "#84cc16", 5: "#22c55e"}
            fig6 = px.bar(
                rev_dist, x="review_score", y="n",
                color="review_score", color_discrete_map=score_colors,
                text=rev_dist["share"].map(lambda v: f"{v:.0%}"),
            )
            fig6.update_traces(textposition="outside", showlegend=False)
            fig6.update_layout(**plotly_layout, height=440,
                               xaxis_title="Calificación", yaxis_title="Pedidos",
                               coloraxis_showscale=False)
            st.plotly_chart(fig6, use_container_width=True)


# ───────── TAB 3 — CATEGORÍAS & SELLERS ─────────
with tab3:
    st.markdown('<div class="section-title">Cuadrante de categorías — GMV vs reseña media</div>',
                unsafe_allow_html=True)
    cat_summary = (
        df_view.dropna(subset=["primary_category_en"])
        .groupby("primary_category_en")
        .agg(gmv=("revenue", "sum"),
             orders=("order_id", "nunique"),
             review=("review_score", "mean"))
        .reset_index()
        .query("orders >= 20")
    )
    if not cat_summary.empty:
        top_cats = cat_summary.nlargest(20, "gmv")
        median_gmv = top_cats["gmv"].median()
        median_rev = top_cats["review"].median()
        fig7 = px.scatter(
            top_cats, x="gmv", y="review", size="orders", text="primary_category_en",
            color="review", color_continuous_scale=[(0, PALETTE["danger"]),
                                                     (0.5, PALETTE["warning"]),
                                                     (1, PALETTE["success"])],
            range_color=[3.5, 4.8], log_x=True,
            size_max=46,
            hover_data={"gmv": ":,.0f", "orders": True, "review": ":.2f",
                        "primary_category_en": False},
        )
        fig7.update_traces(textposition="top center", textfont=dict(size=10, color="#cbd5e1"))
        fig7.add_vline(x=median_gmv, line_color="#475569", line_dash="dot")
        fig7.add_hline(y=median_rev, line_color="#475569", line_dash="dot")
        # Etiquetas de cuadrante — guían la lectura sin requerir leyenda externa.
        x_hi = top_cats["gmv"].max()
        x_lo = top_cats["gmv"].min()
        y_hi = top_cats["review"].max()
        y_lo = top_cats["review"].min()
        for x, y, txt, color in [
            (x_hi, y_hi, "⭐ Estrellas",     PALETTE["success"]),
            (x_hi, y_lo, "🔥 A intervenir",  PALETTE["danger"]),
            (x_lo, y_hi, "🌱 Nicho sano",    PALETTE["accent"]),
            (x_lo, y_lo, "⚓ Deadweight",    PALETTE["muted"]),
        ]:
            fig7.add_annotation(
                x=x, y=y, text=f"<b>{txt}</b>", showarrow=False,
                font=dict(size=10, color=color),
                bgcolor="rgba(15,18,34,0.7)", bordercolor=color, borderwidth=1, borderpad=4,
                xanchor="right" if x == x_hi else "left",
                yanchor="top" if y == y_hi else "bottom",
            )
        fig7.update_layout(**plotly_layout, height=460,
                           xaxis_title="GMV (R$, log) — líneas punteadas en las medianas",
                           yaxis_title="Review medio",
                           coloraxis_showscale=False)
        st.plotly_chart(fig7, use_container_width=True)

    st.markdown('<div class="section-title">Pareto de sellers — concentración del GMV</div>',
                unsafe_allow_html=True)
    df_items_filt = df_items_view[df_items_view["order_status"] == "delivered"] if status_sel == ["delivered"] else df_items_view
    seller_rev = (
        df_items_filt.dropna(subset=["seller_id"])
        .groupby("seller_id")["line_revenue"].sum()
        .sort_values(ascending=False).reset_index()
    )
    if not seller_rev.empty:
        seller_rev["cum_share"] = seller_rev["line_revenue"].cumsum() / seller_rev["line_revenue"].sum()
        seller_rev["rank"] = np.arange(1, len(seller_rev) + 1)
        idx_50 = int(seller_rev.loc[seller_rev["cum_share"] >= 0.5, "rank"].iloc[0])
        idx_80 = int(seller_rev.loc[seller_rev["cum_share"] >= 0.8, "rank"].iloc[0])
        share_top5pct = float(
            seller_rev.head(max(1, int(len(seller_rev) * 0.05)))["line_revenue"].sum()
            / seller_rev["line_revenue"].sum()
        )

        top_show = seller_rev.head(min(200, len(seller_rev)))
        fig8 = go.Figure()
        fig8.add_trace(go.Bar(
            x=top_show["rank"], y=top_show["line_revenue"],
            marker_color=PALETTE["accent"], name="GMV seller",
            hovertemplate="Seller #%{x}<br>GMV: R$ %{y:,.0f}<extra></extra>",
        ))
        fig8.add_trace(go.Scatter(
            x=seller_rev["rank"], y=seller_rev["cum_share"], yaxis="y2",
            mode="lines", line=dict(color=PALETTE["secondary"], width=3),
            name="Acumulado",
            hovertemplate="Top %{x} sellers<br>Acumulado: %{y:.1%}<extra></extra>",
        ))
        fig8.add_vline(x=idx_50, line_color=PALETTE["success"], line_dash="dot",
                       annotation_text=f"50% en top {idx_50}",
                       annotation_position="top",
                       annotation_font_color=PALETTE["success"])
        fig8.add_vline(x=idx_80, line_color=PALETTE["warning"], line_dash="dot",
                       annotation_text=f"80% en top {idx_80}",
                       annotation_position="top",
                       annotation_font_color=PALETTE["warning"])
        layout8 = dict(plotly_layout)
        layout8["yaxis"] = dict(gridcolor="rgba(255,255,255,0.06)", title="GMV por seller (R$)")
        layout8["yaxis2"] = dict(overlaying="y", side="right", showgrid=False,
                                 tickformat=".0%", title="Acumulado", range=[0, 1.02])
        fig8.update_layout(**layout8, height=420, xaxis_title="Ranking de sellers")
        st.plotly_chart(fig8, use_container_width=True)
    else:
        share_top5pct = float("nan")
        idx_50 = idx_80 = 0

    st.markdown('<div class="section-title">Tabla de categorías</div>', unsafe_allow_html=True)
    cat_table = (
        df_view.dropna(subset=["primary_category_en"])
        .groupby("primary_category_en")
        .agg(orders=("order_id", "nunique"),
             gmv=("revenue", "sum"),
             ticket=("revenue", "mean"),
             review=("review_score", "mean"),
             on_time=("on_time_flag", "mean"))
        .reset_index()
        .sort_values("gmv", ascending=False)
        .rename(columns={"primary_category_en": "Categoría"})
    )
    if not cat_table.empty:
        styled = (
            cat_table.style
            .background_gradient(subset=["review"], cmap="RdYlGn", vmin=3.5, vmax=4.8)
            .background_gradient(subset=["on_time"], cmap="RdYlGn", vmin=0.75, vmax=1.0)
            .format({
                "gmv": lambda v: fmt_money_brl(v),
                "ticket": lambda v: fmt_money_brl(v),
                "review": "{:.2f}",
                "on_time": "{:.1%}",
                "orders": "{:,}",
            })
        )
        st.dataframe(styled, use_container_width=True, hide_index=True, height=380)


# ─────────────────────────────────────────────────────────────
# Lectura analítica
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Lectura analítica</div>', unsafe_allow_html=True)

# Umbrales adaptativos — se reducen si el slice es chico para que la narrativa
# siga funcionando incluso con filtros narrow (ej. un estado con pocos pedidos).
n_view = len(df_view)
min_cat_orders = max(1, min(20, n_view // 50))
min_state_orders = max(1, min(50, n_view // 20))

cat_for_lead = (
    df_view.dropna(subset=["primary_category_en"])
    .groupby("primary_category_en")
    .agg(gmv=("revenue", "sum"), review=("review_score", "mean"), orders=("order_id", "nunique"))
    .query(f"orders >= {min_cat_orders}")
    .sort_values("gmv", ascending=False)
)
state_for_risk = (
    df_view.dropna(subset=["on_time_flag"])
    .groupby("customer_state")
    .agg(on_time=("on_time_flag", "mean"),
         delay=("delivery_delay_days", "mean"),
         n=("order_id", "nunique"))
    .query(f"n >= {min_state_orders}")
    .sort_values("on_time")
)

if cat_for_lead.empty:
    st.info("Sin datos suficientes para la lectura analítica con los filtros actuales.")
else:
    cat_top = cat_for_lead.index[0]
    rev_top = cat_for_lead.iloc[0]["gmv"]
    rev_score_top = cat_for_lead.iloc[0]["review"]
    ot_global = df_view["on_time_flag"].mean()
    concentration = share_top5pct if not pd.isna(share_top5pct) else 0.0

    # Mejor categoría por review (si hay >1 categoría con datos)
    if len(cat_for_lead) > 1:
        cat_best_review = cat_for_lead.sort_values("review", ascending=False).iloc[0]
        frase_review = (
            f" La categoría mejor calificada del slice es "
            f"<b>{cat_best_review.name}</b> con <b>{cat_best_review['review']:.2f}★</b> "
            f"de reseña media — un buen modelo a replicar."
        )
    else:
        frase_review = ""

    # Frase logística — adaptativa al número de estados en el slice
    states_in_view = df_view["customer_state"].dropna().unique()
    if len(states_in_view) <= 1 and not state_for_risk.empty:
        # Slice de un solo estado: comparamos ESE estado vs el global del dataset
        only_state = state_for_risk.index[0]
        ot_state = state_for_risk.iloc[0]["on_time"]
        delay_state = state_for_risk.iloc[0]["delay"]
        ot_global_ref = df_orders[df_orders["order_status"].isin(status_sel)]["on_time_flag"].mean() if status_sel else df_orders["on_time_flag"].mean()
        delta_pp = (ot_state - ot_global_ref) * 100
        signo = "por encima" if delta_pp >= 0 else "por debajo"
        flag_state = "🟢 funciona bien" if ot_state >= ot_global_ref else "🟡 hay espacio de mejora"
        frase_logistica = (
            f"<b>{state_label(only_state)}</b> entrega el <b>{ot_state:.1%}</b> de los pedidos a tiempo "
            f"({flag_state}, <b>{abs(delta_pp):.1f}pp {signo}</b> del global "
            f"<b>{ot_global_ref:.1%}</b>), con un retraso promedio de "
            f"<b>{delay_state:.1f}</b> días sobre la fecha estimada."
        )
    elif len(state_for_risk) >= 2:
        # Multi-estado: marca peor Y mejor — simetría ganador/perdedor
        state_worst = state_for_risk.index[0]
        ot_worst = state_for_risk.iloc[0]["on_time"]
        delay_worst = state_for_risk.iloc[0]["delay"]
        state_best = state_for_risk.index[-1]
        ot_best = state_for_risk.iloc[-1]["on_time"]
        delay_best = state_for_risk.iloc[-1]["delay"]
        gap_pp = (ot_best - ot_worst) * 100
        # Top 3 funcionan bien (cabeza de la cola)
        top_funcionan = state_for_risk.tail(3).index.tolist()[::-1]  # mejor primero
        top_funcionan_str = ", ".join(f"<b>{state_label(s)}</b>" for s in top_funcionan)
        frase_logistica = (
            f"🟢 <b>Estados que funcionan</b>: {top_funcionan_str} — "
            f"liderado por <b>{state_label(state_best)}</b> con <b>{ot_best:.1%}</b> on-time "
            f"y entregas <b>{abs(delay_best):.1f}d</b> antes de lo estimado.<br>"
            f"🟡 <b>Estado a intervenir</b>: <b>{state_label(state_worst)}</b> con <b>{ot_worst:.1%}</b> "
            f"on-time (brecha de <b>{gap_pp:.1f}pp</b> vs el mejor) — candidato directo "
            f"para renegociar tarifas y SLAs de freight."
        )
    elif not state_for_risk.empty:
        # Solo 1 estado pasa el umbral
        only_state = state_for_risk.index[0]
        ot_state = state_for_risk.iloc[0]["on_time"]
        flag_state = "🟢 funciona bien" if ot_state >= 0.90 else "🟡 a intervenir"
        frase_logistica = (
            f"{flag_state}: <b>{state_label(only_state)}</b> entrega el "
            f"<b>{ot_state:.1%}</b> de los pedidos a tiempo."
        )
    else:
        frase_logistica = (
            f"Sin datos de entrega suficientes para evaluar la logística en este slice "
            f"(se requieren al menos {min_state_orders} pedidos delivered por estado)."
        )

    verdict_emoji = "🟢" if ot_global and ot_global >= 0.90 else "🟡"
    verdict_txt = ("operativa por encima del benchmark del 90%."
                   if ot_global and ot_global >= 0.90 else
                   "operativa por debajo del benchmark del 90%, hay espacio de mejora logística.")

    st.markdown(
        f"""
        <div class="insight-box">
        🛍 La categoría <b>{cat_top}</b> lidera el período con
        <b>{fmt_money_brl(rev_top)}</b> de GMV y una reseña media de
        <b>{rev_score_top:.2f}★</b>, marcando el motor comercial del slice.{frase_review}<br><br>
        {frase_logistica}<br><br>
        🏗 El <b>5%</b> superior de sellers concentra el <b>{concentration:.0%}</b> del GMV,
        evidenciando un riesgo de dependencia que conviene diversificar mediante
        captación activa en el long-tail.<br><br>
        {verdict_emoji} <b>Veredicto:</b> la operación está {verdict_txt}
        <br><br>
        <span style='color:#64748b;font-size:0.85rem;'>
        Datos: Olist marketplace · {len(df_view):,} pedidos analizados entre
        {date_start:%b %Y} y {date_end:%b %Y}.
        Sep 2016 y Sep–Oct 2018 omitidos por defecto por cobertura parcial.
        </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
