"""
app/app.py — Dashboard analítico E-commerce SA (Streamlit) · Taller 2.

Mensaje central D2: "el negocio deja dinero sobre la mesa en electrónica", capturable en
dos estrategias — Estrategia 1 (recuperar carritos abandonados, PN1) y Estrategia 2
(retener al núcleo recurrente, PN2) — con PN3 (cuándo/con qué activar el incentivo).

DISEÑO (iteración v2 "comunicar limpio"): cada sección sigue UN patrón fijo —
  1) una frase de mensaje (takeaway),
  2) un gráfico HÉROE cuyo título es la acción (verbo + cifra) con la anotación que traduce
     el hallazgo dentro del propio gráfico,
  3) a lo sumo un apoyo (o 2–3 chips de cifra),
  4) un chip de acción.
Se elimina el bloque de 4 tarjetas (Contexto/Hallazgo/Traducción/Acción): esa info va en el
título-acción y la anotación del héroe (§3.1 Data-to-Ink; §3.4 jerarquía). Resumen y
Estrategia 1 NO comparten el mismo héroe. Un solo acento (rojo); contexto en grises (§3.2).

MEMORIA: el app NO carga el clickstream crudo ni importa src/prep.py ni src/metrics.py.
Solo consume los 5 parquets agregados (~3,9 MB) vía src/agg_metrics.py, con @st.cache_data.
Cifras idénticas al notebook (src/verify_aggregates.py). Pico de RAM objetivo < 250 MB.

Caveats de fidelidad de los filtros (el caso SIN filtros es exacto, igual que el notebook;
ver "Acerca de los datos"): hora en métricas de unidad = hora del primer evento de la unidad;
la marca no entra en el agregado horario; recurrencia/timing por categoría dominante.

Ejecutar:  .venv\\Scripts\\python.exe -m streamlit run app/app.py
"""
import sys
from pathlib import Path

import streamlit as st

_APP_DIR = Path(__file__).resolve().parent
_ROOT = _APP_DIR.parent
sys.path.append(str(_ROOT))
sys.path.insert(0, str(_APP_DIR))
from src import agg_metrics as am  # noqa: E402
import charts  # noqa: E402
import ui  # noqa: E402
from theme import fmt_money, fmt_money_short, fmt_pct  # noqa: E402

st.set_page_config(page_title="E-commerce SA — Inteligencia de conversión", page_icon="🛒", layout="wide")

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


ui.inject_global_css()
ui.header_bar()

units = load_units()
occ = load_occasions()
hourly = load_hourly()
price_cat = load_price_cat()
A = load_anchors()


# ── Sidebar: controles globales (revelación progresiva, §4.3) ─────────────────
st.sidebar.header("Filtros")
cats_all = sorted(units["category_main"].dropna().unique().tolist())
sel_cats = st.sidebar.multiselect("Categoría", cats_all, default=[], help="Vacío = todas las categorías")
hr = st.sidebar.slider("Hora del día", 0, 23, (0, 23))

with st.sidebar.expander("Filtros avanzados"):
    top_brands = units["brand"].value_counts().head(30).index.tolist()
    sel_brands = st.multiselect("Marca (top 30 por volumen)", top_brands, default=[],
                                help="Vacío = todas las marcas")
    seg = st.radio("Segmento de comprador", ["Todos", "Recurrentes", "One-time"], index=0)

st.sidebar.markdown("---")
ui.about_data_expander()  # caveat metodológico fuera del flujo visual del tablero

_SEG = {"Recurrentes": "recurrent", "One-time": "onetime"}


# ── Filtros del sidebar aplicados a cada agregado (a su grano) ────────────────
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
    if seg in _SEG:  # la marca NO entra en este agregado (ver "Acerca de los datos")
        m &= h["segment"].eq(_SEG[seg])
    return h[m]


fu = filter_units(units)
fo = filter_occ(occ)
fh = filter_hourly(hourly)


def _min_txt(m):
    return f"{m:.1f} min".replace(".", ",") if m == m else "—"


def _days_txt(d):
    return f"{d:.1f} días".replace(".", ",") if d == d else "—"


# ── Guarda global: sin datos bajo los filtros del sidebar ─────────────────────
if not len(fu):
    st.warning("Ningún evento cumple los filtros del sidebar. Ajusta los controles.")
    st.stop()

k_ab = am.abandonment(fu)
k_ras = am.revenue_at_stake(fu)
k_ds = am.decision_speed(fu)
k_rec = am.recurrence(fo)

# Cifras-ancla fijas para los títulos-acción (no se mueven con los filtros)
FOCO_STAKE = A["rev_en_juego_foco"]                       # $2,08 M en electronics
FOCO_SHARE = FOCO_STAKE / A["rev_en_juego_total"] * 100   # 82% del premio
RECOVER_10 = FOCO_STAKE * 0.10                            # $207.700/mes (recuperar 10%)


# ── Navegación prominente ─────────────────────────────────────────────────────
tab_resumen, tab_e1, tab_e2, tab_cuando = st.tabs(
    ["Resumen", "Estrategia 1 · Conversión", "Estrategia 2 · Retención", "Cuándo activar"]
)


# ===== RESUMEN (estratégico, cero interacción — test de 30 s) ==================
with tab_resumen:
    ui.section_header(
        "¿En qué categoría se nos queda el dinero?",
        "La respuesta está concentrada en una sola categoría.",
    )
    kpis = [
        ("Revenue en juego", f"{fmt_money_short(k_ras['total_en_juego'])} USD", "carritos abandonados", True),
        ("Abandono de carrito", fmt_pct(k_ab["abandono_global"]), "de lo que llega al carrito", False),
        ("Conversión por unidad", fmt_pct(k_ab["gf"]["conv_rate"], 2), "de lo visto se compra", False),
        ("Recurrentes", fmt_pct(k_rec["pct_repeat"]), f"= {fmt_pct(k_rec['pct_rev_repeat'])} del revenue", False),
        ("Decisión (mediana)", _min_txt(k_ds["median_min"]), "del 1er view a la compra", False),
    ]
    for col, (lbl, val, sub, acc) in zip(st.columns(5), kpis):
        col.markdown(ui.kpi_card(lbl, val, sub, acc), unsafe_allow_html=True)

    st.markdown("")
    hcol, ccol = st.columns([3, 1], gap="large")
    with hcol:
        st.plotly_chart(charts.hero_revenue_at_stake(k_ras, foco=FOCO), key="r_hero", width="stretch")
    with ccol:
        st.markdown("")
        ui.callout(fmt_money_short(FOCO_STAKE), f"en juego solo en electronics ({FOCO_SHARE:.0f}% del premio)")
    ui.glossary_expander()


# ===== ESTRATEGIA 1 · CONVERSIÓN (PN1) =========================================
with tab_e1:
    ui.message_line("Dónde perdemos la venta y cuánto vale recuperarla.")

    hcol, scol = st.columns([3, 2], gap="large")
    with hcol:
        st.plotly_chart(
            charts.funnel_chart(
                k_ab,
                title=f"Recuperar el 10% de los carritos de electrónica = {fmt_money(RECOVER_10)}/mes",
                note=f"El {FOCO_SHARE:.0f}% del revenue abandonado está en electronics ({fmt_money_short(FOCO_STAKE)}).",
            ),
            key="e1_hero", width="stretch",
        )
    with scol:
        st.markdown("")
        bm = am.brand_mix(fu, foco=FOCO)
        g = bm["g"]
        if len(g) and bm["n_total"]:
            gg = g.sort_values("carritos", ascending=False)
            top2 = gg.head(2)
            share = top2["carritos"].sum() / bm["n_total"] * 100
            names = " + ".join(str(b).title() for b in top2.index)
            top_brand = str(gg.index[0]).title()
            top_ticket = float(gg.iloc[0]["ticket"])
            st.markdown(ui.stat_chip("🛒", fmt_pct(share, 0), f"de los carritos: {names}"),
                        unsafe_allow_html=True)
            st.markdown("")
            st.markdown(ui.stat_chip("🏷️", fmt_money(top_ticket), f"ticket medio · {top_brand}"),
                        unsafe_allow_html=True)
        else:
            st.info(f"Sin marcas con volumen suficiente en {FOCO} para el filtro actual.")

    ui.action_chip("Incentivo de cierre inmediato/en pantalla, en la franja matutina.", icon="🎯")

    with st.expander("Ver detalle analítico"):
        d1, d2 = st.columns(2)
        with d1:
            st.plotly_chart(charts.abandonment_by_category(k_ab), key="e1_abandono", width="stretch")
        with d2:
            if len(g):
                st.plotly_chart(charts.brand_chart(bm), key="e1_brand", width="stretch")
            else:
                st.info("Sin marcas suficientes para el detalle.")


# ===== ESTRATEGIA 2 · RETENCIÓN (PN2) ==========================================
with tab_e2:
    rt = am.repurchase_timing(fo)
    ratio = (k_rec["ticket_repeat"] / k_rec["ticket_one_time"]
             if k_rec["ticket_one_time"] else float("nan"))
    ratio_txt = f"{ratio:.1f}×".replace(".", ",") if ratio == ratio else "—"
    ui.message_line(
        f"El {fmt_pct(k_rec['pct_repeat'])} de los compradores trae el "
        f"{fmt_pct(k_rec['pct_rev_repeat'])} del revenue — ticket {ratio_txt} "
        f"({fmt_money(k_rec['ticket_repeat'])} vs {fmt_money(k_rec['ticket_one_time'])})."
    )

    if k_rec["repeat"] > 0:
        hcol, tcol = st.columns([3, 2], gap="large")
        with hcol:
            st.plotly_chart(
                charts.hero_retention(
                    k_rec, title="Fideliza al tercio que ya vuelve: genera 2 de cada 3 dólares"),
                key="e2_hero", width="stretch",
            )
        with tcol:
            st.markdown("")
            days = rt["days"]
            milestones = None
            if len(days):
                p1 = float((days <= 1).mean() * 100)
                p7 = float((days <= 7).mean() * 100)
                milestones = [(100 * 1 / 14, f"1 día · {p1:.0f}%"), (100 * 7 / 14, f"7 días · {p7:.0f}%")]
            ui.time_panel(
                value=_days_txt(rt["median_days"]),
                caption="mediana hasta la 2ª compra",
                milestones=milestones,
                badge=f"{fmt_pct(rt['same_pct'])} vuelve a la misma categoría"
                      if rt["same_pct"] == rt["same_pct"] else None,
            )
    else:
        st.info("Sin compradores recurrentes en el filtro actual (prueba 'Segmento = Todos').")

    ui.action_chip("Nudge de recompra a 24–72 h, en la misma categoría.", icon="🔔")

    with st.expander("Ver detalle analítico"):
        d1, d2 = st.columns(2)
        with d1:
            st.plotly_chart(charts.ticket_chart(k_rec), key="e2_ticket", width="stretch")
        with d2:
            if rt["n_recurrent"] > 0:
                st.plotly_chart(charts.timing_chart(rt), key="e2_timing", width="stretch")
            else:
                st.info("Sin pares de recompra en el filtro actual.")


# ===== CUÁNDO ACTIVAR (PN3) ====================================================
with tab_cuando:
    hi = am.hourly_intensity(fh)
    peak_h = int(hi["compras_x100_vistas"].idxmax()) if len(hi) else 0
    ui.message_line(f"La mañana convierte ~2× por visita (pico {peak_h}h).")

    if len(hi):
        hcol, tcol = st.columns([3, 2], gap="large")
        with hcol:
            st.plotly_chart(charts.hourly_intensity_hero(hi), key="c_hero", width="stretch")
        with tcol:
            st.markdown("")
            ui.time_panel(
                value=_min_txt(k_ds["median_min"]),
                caption="mediana de decisión (1er view → compra)",
                sub=f"{fmt_pct(k_ds['pct_lt5'])} decide en menos de 5 min",
            )
    else:
        st.info("Sin eventos para la franja/filtro actual.")

    ui.action_chip("Activa 6–10 h con incentivo inmediato/en pantalla; el precio no es el freno.",
                   icon="🎯")

    with st.expander("Ver detalle analítico"):
        if len(hi):
            st.plotly_chart(charts.hourly_intensity_chart(hi), key="c_hourly_detail", width="stretch")
        d1, d2 = st.columns(2)
        with d1:
            st.plotly_chart(charts.decision_speed_chart(k_ds), key="c_speed", width="stretch")
        with d2:
            pc = am.price_vs_conversion(fu, price_cat)
            if len(pc):
                st.plotly_chart(charts.price_vs_conversion_chart(pc, foco=FOCO), key="c_price", width="stretch")
            else:
                st.info("No hay categorías con ≥500 unidades en el filtro actual.")
