import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ARCHIVO = "datos_financieros_negocio.csv"

st.set_page_config(
    page_title="Financial Insights · Analaitica",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# Estilos (CSS custom — Streamlit renderiza con React)
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
# Datos
# ─────────────────────────────────────────────────────────────
@st.cache_data
def cargar_datos(ruta: str) -> pd.DataFrame:
    df = pd.read_csv(ruta)
    df["periodo"] = pd.to_datetime(df["periodo"], format="%Y-%m")
    df["utilidad_operativa"] = df["ingresos"] - df["costos"] - df["gastos"]
    df["margen_operativo"] = df["utilidad_operativa"] / df["ingresos"]
    return df.sort_values("periodo")


df = cargar_datos(ARCHIVO)


def fmt_money(v: float) -> str:
    if abs(v) >= 1e9:
        return f"${v/1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:,.2f}M"
    if abs(v) >= 1e3:
        return f"${v/1e3:,.1f}K"
    return f"${v:,.0f}"


def kpi_card(label: str, value: str, accent_from: str, accent_to: str, delta: str = ""):
    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ""
    return f"""
    <div class="kpi-card" style="--accent-from:{accent_from};--accent-to:{accent_to};">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """


# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='padding:8px 4px 18px 4px;'>"
        "<div style='font-size:0.72rem;letter-spacing:0.18em;color:#818cf8;font-weight:600;'>ANALAITICA</div>"
        "<div style='font-size:1.25rem;font-weight:700;color:#fff;margin-top:4px;'>Financial Insights</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    unidades = sorted(df["unidad_negocio"].unique())
    unidad_sel = st.selectbox("Unidad de negocio", unidades)

    periodos = df["periodo"].dt.to_period("M").astype(str).unique().tolist()
    rango = st.select_slider(
        "Rango de periodos",
        options=periodos,
        value=(periodos[0], periodos[-1]),
    )
    st.markdown("---")
    st.caption(f"Registros totales: **{len(df):,}**")
    st.caption(f"Unidades: **{len(unidades)}**")


# ─────────────────────────────────────────────────────────────
# Filtrado
# ─────────────────────────────────────────────────────────────
mask = (
    (df["periodo"] >= pd.Period(rango[0], "M").start_time)
    & (df["periodo"] <= pd.Period(rango[1], "M").end_time)
)
df_rango = df[mask]
filtro = df_rango[df_rango["unidad_negocio"] == unidad_sel]

# ─────────────────────────────────────────────────────────────
# Hero
# ─────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="hero">
        <h1>💠 {unidad_sel}</h1>
        <p>Indicadores financieros · {rango[0]} → {rango[1]}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────────────────────
ingresos = float(filtro["ingresos"].sum())
costos = float(filtro["costos"].sum())
gastos = float(filtro["gastos"].sum())
utilidad = float(filtro["utilidad_operativa"].sum())
margen = utilidad / ingresos if ingresos else 0

cols = st.columns(5)
cards = [
    ("Ingresos", fmt_money(ingresos), "#06b6d4", "#3b82f6"),
    ("Costos", fmt_money(costos), "#f97316", "#ef4444"),
    ("Gastos", fmt_money(gastos), "#eab308", "#f59e0b"),
    ("Utilidad operativa", fmt_money(utilidad), "#10b981", "#22c55e"),
    ("Margen operativo", f"{margen:.1%}", "#6366f1", "#a855f7"),
]
for col, (label, value, c1, c2) in zip(cols, cards):
    col.markdown(kpi_card(label, value, c1, c2), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Tabs (charts + comparativa + datos)
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

tab1, tab2, tab3 = st.tabs(["📈 Evolución", "🏢 Comparativa", "🧾 Datos"])

with tab1:
    st.markdown('<div class="section-title">Evolución mensual de ingresos y utilidad</div>',
                unsafe_allow_html=True)
    serie = filtro.sort_values("periodo")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=serie["periodo"], y=serie["ingresos"],
        name="Ingresos", mode="lines+markers",
        line=dict(color="#3b82f6", width=3),
        fill="tozeroy", fillcolor="rgba(59,130,246,0.12)",
    ))
    fig.add_trace(go.Scatter(
        x=serie["periodo"], y=serie["utilidad_operativa"],
        name="Utilidad operativa", mode="lines+markers",
        line=dict(color="#22c55e", width=3),
        fill="tozeroy", fillcolor="rgba(34,197,94,0.12)",
    ))
    fig.update_layout(**plotly_layout, height=420)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Margen operativo mensual</div>',
                unsafe_allow_html=True)
    fig_m = px.area(
        serie, x="periodo", y="margen_operativo",
        color_discrete_sequence=["#a855f7"],
    )
    fig_m.update_traces(line=dict(width=3))
    fig_m.update_layout(**plotly_layout, height=280, yaxis_tickformat=".0%")
    st.plotly_chart(fig_m, use_container_width=True)

with tab2:
    st.markdown('<div class="section-title">Comparación entre unidades de negocio</div>',
                unsafe_allow_html=True)
    resumen = (
        df_rango.groupby("unidad_negocio", as_index=False)
        .agg(ingresos=("ingresos", "sum"),
             costos=("costos", "sum"),
             gastos=("gastos", "sum"),
             utilidad_operativa=("utilidad_operativa", "sum"))
    )
    resumen["margen_operativo"] = resumen["utilidad_operativa"] / resumen["ingresos"]
    resumen = resumen.sort_values("ingresos", ascending=False)

    barras = resumen.melt(
        id_vars="unidad_negocio",
        value_vars=["ingresos", "costos", "gastos", "utilidad_operativa"],
        var_name="indicador", value_name="valor",
    )
    paleta = {
        "ingresos": "#3b82f6",
        "costos": "#ef4444",
        "gastos": "#f59e0b",
        "utilidad_operativa": "#22c55e",
    }
    fig_b = px.bar(
        barras, x="unidad_negocio", y="valor", color="indicador",
        barmode="group", color_discrete_map=paleta,
    )
    fig_b.update_layout(**plotly_layout, height=420)
    st.plotly_chart(fig_b, use_container_width=True)

    st.markdown('<div class="section-title">Margen operativo por unidad</div>',
                unsafe_allow_html=True)
    fig_m2 = px.bar(
        resumen.sort_values("margen_operativo", ascending=False),
        x="unidad_negocio", y="margen_operativo",
        color="margen_operativo", color_continuous_scale="Viridis",
        text=resumen["margen_operativo"].map(lambda v: f"{v:.1%}"),
    )
    fig_m2.update_traces(textposition="outside")
    fig_m2.update_layout(**plotly_layout, height=320,
                         yaxis_tickformat=".0%", coloraxis_showscale=False)
    st.plotly_chart(fig_m2, use_container_width=True)

with tab3:
    st.markdown('<div class="section-title">Datos de la unidad seleccionada</div>',
                unsafe_allow_html=True)
    st.dataframe(
        filtro.assign(
            margen_operativo=filtro["margen_operativo"].map(lambda v: f"{v:.1%}"),
        ),
        use_container_width=True,
        hide_index=True,
    )

# ─────────────────────────────────────────────────────────────
# Lectura analítica
# ─────────────────────────────────────────────────────────────
resumen_total = (
    df_rango.groupby("unidad_negocio", as_index=False)
    .agg(ingresos=("ingresos", "sum"),
         utilidad_operativa=("utilidad_operativa", "sum"))
)
resumen_total["margen_operativo"] = (
    resumen_total["utilidad_operativa"] / resumen_total["ingresos"]
)
mejor_margen = resumen_total.loc[resumen_total["margen_operativo"].idxmax()]
peor_margen = resumen_total.loc[resumen_total["margen_operativo"].idxmin()]
mayor_ingreso = resumen_total.loc[resumen_total["ingresos"].idxmax()]
ranking = (
    resumen_total.sort_values("margen_operativo", ascending=False)
    .reset_index(drop=True)
)
posicion = int(ranking.index[ranking["unidad_negocio"] == unidad_sel][0]) + 1

st.markdown('<div class="section-title">Lectura analítica</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="insight-box">
    <b>{mayor_ingreso['unidad_negocio']}</b> lidera en ingresos con
    <b>{fmt_money(mayor_ingreso['ingresos'])}</b>. El mejor margen operativo lo registra
    <b>{mejor_margen['unidad_negocio']}</b> ({mejor_margen['margen_operativo']:.1%}),
    mientras que <b>{peor_margen['unidad_negocio']}</b>
    queda al final con {peor_margen['margen_operativo']:.1%} —
    una brecha de
    <b>{(mejor_margen['margen_operativo'] - peor_margen['margen_operativo']):.1%}</b>
    que sugiere oportunidades claras de eficiencia operativa.<br><br>
    La unidad seleccionada (<b>{unidad_sel}</b>) tiene un margen de
    <b>{margen:.1%}</b> y ocupa la posición <b>#{posicion}</b> de
    {len(resumen_total)}. {'🟢 Su rentabilidad está por encima del promedio.'
        if margen > resumen_total['margen_operativo'].mean() else
        '🟡 Su rentabilidad está por debajo del promedio del portafolio.'}
    </div>
    """,
    unsafe_allow_html=True,
)
