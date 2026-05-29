"""
app/app.py — FASE III: Dashboard analítico (Streamlit) del Taller 2.

Mensaje central D2: "el negocio deja dinero sobre la mesa en electrónica", capturable en
dos momentos — Palanca A (recuperar carritos abandonados, PN1) y Palanca B (retener al
núcleo recurrente, PN2) — con PN3 (cuándo/con qué activar el incentivo).

Diseño: titular-acción FIJO arriba (cifras ancla, ya precomputadas) + KPIs y gráficos
REACTIVOS a los filtros del sidebar. 4 pestañas (Resumen / A / B / Cuándo).

MEMORIA: este dashboard NO carga el clickstream crudo (~980k filas / ~238 MB) ni deriva
métricas al vuelo sobre él. Carga AGREGADOS pequeños precomputados por src/build_aggregates.py
(~3,9 MB en disco / ~11 MB en RAM) y los filtra a su propio grano. Esto evita el pico de
RAM que tumbaba la app en el tier gratuito de Streamlit Community Cloud. Las cifras son
idénticas a las del notebook (verificado en src/verify_aggregates.py).

Notas de fidelidad de los filtros (el caso SIN filtros es idéntico al notebook):
  · El filtro de HORA en las métricas de unidad (funnel/abandono/revenue/decisión) corta por
    la hora del PRIMER evento de la unidad, no troceando eventos sueltos (más coherente).
  · El filtro de MARCA no afecta a la figura de intensidad horaria (la marca no entra en ese
    agregado: 2.572 marcas lo dispararían). Sí afecta al resto.
  · Recurrencia/timing se filtran por la categoría/marca DOMINANTE de cada ocasión de compra.

Ejecutar:  .venv\\Scripts\\python.exe -m streamlit run app/app.py
"""
import sys
from pathlib import Path

import streamlit as st

# Rutas: raíz del repo (para config y src/*) y carpeta app/ (para módulos hermanos).
# OJO: la carpeta se llama 'app' y el script también 'app.py' → para evitar el choque de
# nombres importamos theme/charts como módulos hermanos (no 'from app import ...').
_APP_DIR = Path(__file__).resolve().parent
_ROOT = _APP_DIR.parent
sys.path.append(str(_ROOT))
sys.path.insert(0, str(_APP_DIR))
from src import agg_metrics as am  # noqa: E402
import charts  # noqa: E402
from theme import fmt_money, fmt_money_short, fmt_pct  # noqa: E402

st.set_page_config(page_title="Taller 2 — Incentivos e-commerce", page_icon="💡", layout="wide")

FOCO = "electronics"


# ── Carga de AGREGADOS (cacheada; nunca el clickstream crudo) ─────────────────
@st.cache_data(show_spinner="Cargando agregados…")
def load_units():
    return am.load_units()


@st.cache_data(show_spinner=False)
def load_occasions():
    return am.load_occasions()


@st.cache_data(show_spinner=False)
def load_hourly():
    return am.load_hourly()


@st.cache_data(show_spinner=False)
def load_price_cat():
    return am.load_price_cat()


@st.cache_data(show_spinner=False)
def load_anchors():
    return am.load_anchors()


units = load_units()
occ = load_occasions()
hourly = load_hourly()
price_cat = load_price_cat()
A = load_anchors()


# ── Sidebar: filtros (revelación progresiva) ──────────────────────────────────
st.sidebar.header("Filtros")
cats_all = sorted(units["category_main"].dropna().unique().tolist())
sel_cats = st.sidebar.multiselect("Categoría", cats_all, default=[],
                                  help="Vacío = todas las categorías")
hr = st.sidebar.slider("Hora del día", 0, 23, (0, 23))

with st.sidebar.expander("Filtros avanzados"):
    top_brands = units["brand"].value_counts().head(30).index.tolist()
    sel_brands = st.multiselect("Marca (top 30 por volumen)", top_brands, default=[],
                                help="Vacío = todas las marcas")
    seg = st.radio("Segmento de comprador", ["Todos", "Recurrentes", "One-time"], index=0)

st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠️ Ventana = solo octubre 2019 (muestra por usuario, semilla 42). Son señales "
    "sólidas para decidir, no verdades definitivas."
)

_SEG = {"Recurrentes": "recurrent", "One-time": "onetime"}


# ── Aplicar filtros a cada agregado (a su grano) ──────────────────────────────
def filter_units(u):
    m = u["unit_hour"].between(hr[0], hr[1])
    if sel_cats:
        m &= u["category_main"].isin(sel_cats)
    if sel_brands:
        m &= u["brand"].isin(sel_brands)
    if seg in _SEG:
        m &= u["segment"].eq(_SEG[seg])
    return u[m]


def filter_occ(o):
    m = o["hour"].between(hr[0], hr[1])
    if sel_cats:
        m &= o["category"].isin(sel_cats)
    if sel_brands:
        m &= o["brand"].isin(sel_brands)
    if seg in _SEG:
        m &= o["segment"].eq(_SEG[seg])
    return o[m]


def filter_hourly(h):
    m = h["hour"].between(hr[0], hr[1])
    if sel_cats:
        m &= h["category_main"].isin(sel_cats)  # excluye el bucket "(sin categoria)"
    if seg in _SEG:  # la marca NO entra en este agregado (ver nota de fidelidad arriba)
        m &= h["segment"].eq(_SEG[seg])
    return h[m]


fu = filter_units(units)
fo = filter_occ(occ)
fh = filter_hourly(hourly)
filtros_activos = bool(sel_cats or sel_brands or seg != "Todos" or hr != (0, 23))


# ── Titular fijo (cifras ancla, NO reaccionan a los filtros) ──────────────────
st.markdown(f"## 💡 El negocio deja dinero sobre la mesa en **{FOCO}**")
st.markdown(
    f"**{fmt_money_short(A['rev_en_juego_foco'])}** en carritos abandonados de {FOCO} esperan recuperación, "
    f"y **{fmt_pct(A['pct_repeat'])}** de los compradores (los recurrentes) ya traen el "
    f"**{fmt_pct(A['pct_rev_repeat'])}** del revenue. Dos palancas, una misma categoría:"
)
c1, c2 = st.columns(2)
c1.success("**Palanca A — antes de comprar:** recuperar carritos abandonados con incentivo "
           "inmediato/en pantalla en la **franja matutina**.")
c2.info("**Palanca B — después de comprar:** nudge de recompra a **24–72 h** en la misma "
        "categoría al núcleo recurrente.")

st.markdown("---")
st.caption("Indicadores (reaccionan a los filtros del sidebar):" if filtros_activos
           else "Indicadores (muestra completa — usa el sidebar para filtrar):")

# KPIs reactivos sobre los agregados filtrados
k_ab = am.abandonment(fu) if len(fu) else None
k_rec = am.recurrence(fo) if len(fo) else None
k_ras = am.revenue_at_stake(fu) if len(fu) else None
k_ds = am.decision_speed(fu) if len(fu) else None

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Revenue en juego", fmt_money_short(k_ras["total_en_juego"]) if k_ras else "—")
m2.metric("Abandono de carrito", fmt_pct(k_ab["abandono_global"]) if k_ab else "—")
m3.metric("Conversión por unidad", fmt_pct(k_ab["gf"]["conv_rate"], 2) if k_ab else "—")
m4.metric("Recurrentes / su revenue",
          f"{fmt_pct(k_rec['pct_repeat'])} / {fmt_pct(k_rec['pct_rev_repeat'])}" if k_rec else "—")
m5.metric("Decisión (mediana)",
          f"{k_ds['median_min']:.1f} min".replace(".", ",") if k_ds and k_ds["median_min"] == k_ds["median_min"] else "—")

if not len(fu):
    st.warning("Ningún evento cumple los filtros actuales. Ajusta el sidebar.")
    st.stop()


# ── Pestañas ──────────────────────────────────────────────────────────────────
tab_resumen, tab_a, tab_b, tab_cuando = st.tabs(
    ["📊 Resumen", "🅰️ Palanca A — Conversión", "🅱️ Palanca B — Retención", "⏰ Cuándo activar"]
)

# --- Resumen: los dos héroes lado a lado (test de 30 s) ---
with tab_resumen:
    st.markdown(
        "**Contexto:** la conversión vive en 1–3%; el reto es asignar incentivos sin "
        "descontar a quien ya iba a comprar. **Hallazgo:** el dinero perdido y el valor "
        "recurrente se concentran en electrónica. **Acción:** dos palancas en paralelo."
    )
    h1, h2 = st.columns(2)
    with h1:
        st.plotly_chart(charts.hero_revenue_at_stake(k_ras, foco=FOCO), key="hero_a", width="stretch")
    with h2:
        if k_rec and k_rec["repeat"] > 0:
            st.plotly_chart(charts.hero_retention(k_rec), key="hero_b", width="stretch")
        else:
            st.info("Sin compradores recurrentes en el filtro actual (prueba con 'Segmento = Todos').")

# --- Palanca A: PN1 ---
with tab_a:
    st.markdown(
        "#### PN1 — ¿Dónde perdemos conversión y cuánto vale recuperarla?\n"
        f"**Contexto:** de cada producto que llega al carrito, ~1/3 no se compra. "
        f"**Hallazgo:** el abandono ({fmt_pct(k_ab['abandono_global'])}) se concentra en "
        f"electrónica/electrodomésticos. **Traducción:** {fmt_money_short(k_ras['total_en_juego'])} "
        f"en juego, la mayoría en {FOCO}. **Acción:** incentivo de cierre (recordatorio de "
        "carrito, urgencia/stock, financiación) a los carritos abandonados de electrónica."
    )
    ca1, ca2 = st.columns(2)
    with ca1:
        st.plotly_chart(charts.hero_revenue_at_stake(k_ras, foco=FOCO), key="a_revenue", width="stretch")
        st.plotly_chart(charts.funnel_chart(k_ab), key="a_funnel", width="stretch")
    with ca2:
        st.plotly_chart(charts.abandonment_by_category(k_ab), key="a_abandono", width="stretch")
        bm = am.brand_mix(fu, foco=FOCO)
        if len(bm["g"]):
            st.plotly_chart(charts.brand_chart(bm), key="a_brand", width="stretch")
        else:
            st.info(f"Sin marcas con suficiente volumen en {FOCO} para el filtro actual.")

# --- Palanca B: PN2 ---
with tab_b:
    rt = am.repurchase_timing(fo)
    dias_txt = f"{rt['median_days']:.1f}".replace(".", ",") if rt["median_days"] == rt["median_days"] else "—"
    st.markdown(
        "#### PN2 — ¿Quiénes son los clientes valiosos y cómo retenerlos?\n"
        f"**Contexto:** la mayoría compra una sola vez. **Hallazgo:** el "
        f"{fmt_pct(k_rec['pct_repeat'])} recurrente concentra el {fmt_pct(k_rec['pct_rev_repeat'])} "
        f"del revenue (ticket {fmt_money(k_rec['ticket_repeat'])} vs {fmt_money(k_rec['ticket_one_time'])}). "
        f"**Traducción:** retener a ese núcleo rinde más que captar uno nuevo. **Acción:** "
        f"nudge de recompra a 24–72 h (la 2a compra llega en mediana {dias_txt} días, "
        f"{fmt_pct(rt['same_pct'])} en la misma categoría)."
    )
    cb1, cb2 = st.columns(2)
    with cb1:
        if k_rec["repeat"] > 0:
            st.plotly_chart(charts.hero_retention(k_rec), key="b_hero", width="stretch")
        else:
            st.info("Sin recurrentes en el filtro actual.")
        st.plotly_chart(charts.ticket_chart(k_rec), key="b_ticket", width="stretch")
    with cb2:
        if rt["n_recurrent"] > 0:
            st.plotly_chart(charts.timing_chart(rt), key="b_timing", width="stretch")
        else:
            st.info("Sin pares de recompra en el filtro actual (prueba 'Segmento = Todos').")

# --- Cuándo activar: PN3 ---
with tab_cuando:
    hi = am.hourly_intensity(fh)
    pc = am.price_vs_conversion(fu, price_cat)
    peak_h = int(hi["compras_x100_vistas"].idxmax()) if len(hi) else 0
    min_txt = f"{k_ds['median_min']:.1f}".replace(".", ",") if k_ds["median_min"] == k_ds["median_min"] else "—"
    st.markdown(
        "#### PN3 — ¿Cuándo y con qué activar el incentivo?\n"
        "**Contexto:** el tráfico pica en la tarde, pero no toda visita tiene la misma "
        "intención. **Hallazgo:** la mañana convierte ~2× por visita (pico de intensidad a "
        f"las {peak_h}h) y el comprador con intención decide en {min_txt} min. "
        "**Traducción:** el momento y el tipo de incentivo importan más que el precio. "
        "**Acción:** activar en la franja matutina (6–10 h), incentivo inmediato/en "
        "pantalla; el precio NO es el freno."
    )
    if len(hi):
        st.plotly_chart(charts.hourly_intensity_chart(hi), key="c_hourly", width="stretch")
        st.caption("La figura horaria no reacciona al filtro de marca (la marca no entra en "
                   "su agregado).")
    cc1, cc2 = st.columns(2)
    with cc1:
        st.plotly_chart(charts.decision_speed_chart(k_ds), key="c_speed", width="stretch")
    with cc2:
        if len(pc):
            st.plotly_chart(charts.price_vs_conversion_chart(pc, foco=FOCO), key="c_price", width="stretch")
        else:
            st.info("No hay categorías con ≥500 unidades en el filtro actual.")
