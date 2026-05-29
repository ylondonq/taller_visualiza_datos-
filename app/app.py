"""
app/app.py — Dashboard analítico E-commerce SA (Streamlit) · Taller 2.

Mensaje central D2: "el negocio deja dinero sobre la mesa en electrónica", capturable en
dos momentos — Palanca A (recuperar carritos abandonados, PN1) y Palanca B (retener al
núcleo recurrente, PN2) — con PN3 (cuándo/con qué activar el incentivo).

DISEÑO (rediseño BI estratégico, principios del curso):
  · Marca + navegación prominente arriba (orientación del neófito, §4.3).
  · Jerarquía HÉROE + SOPORTE por sección: una sola gráfica grande; el resto degradado o
    tras revelación progresiva (§3.4 jerarquía + §3.1 Data-to-Ink; mata el "tablero de avión").
  · Un único acento (rojo); contexto en grises (§3.2 preatentivos). Sin verde/azul decorativos.
  · Ayudas NO-gráfico: banner de acción, tarjetas KPI jerarquizadas, insight cards CHTA,
    glosario, callouts (§3.5 acto de habla "motivar").
  · Cross-filter estilo Power BI dentro de las pestañas analíticas (§4.1 drill-down), sobre
    los AGREGADOS cacheados; el Resumen queda sin interacción obligatoria (test de 30 s).

MEMORIA: el app NO carga el clickstream crudo ni importa src/prep.py ni src/metrics.py.
Solo consume los 5 parquets agregados (~3,9 MB) vía src/agg_metrics.py, con @st.cache_data.
Cifras idénticas al notebook (src/verify_aggregates.py). Pico de RAM objetivo < 250 MB.

Caveats de fidelidad de los filtros (el caso SIN filtros es exacto, igual que el notebook):
  · Hora en métricas de unidad → corta por la hora del PRIMER evento de la unidad.
  · Marca → no afecta la figura de intensidad horaria (no entra en ese agregado).
  · Recurrencia/timing → se filtran por la categoría/marca DOMINANTE de cada ocasión.

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
ui.caveat("⚠️ Ventana = solo octubre 2019 (muestra por usuario, semilla 42). Son señales "
          "sólidas para decidir, no verdades definitivas.")

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
    if seg in _SEG:  # la marca NO entra en este agregado (ver caveats arriba)
        m &= h["segment"].eq(_SEG[seg])
    return h[m]


fu = filter_units(units)
fo = filter_occ(occ)
fh = filter_hourly(hourly)


# ── Cross-filter (selección Plotly -> filtra el resto de la pestaña) ──────────
def _picked_cats(sel):
    """Extrae las categorías seleccionadas de un evento/estado de st.plotly_chart.
    Usa customdata (categoría) y, como respaldo, la coordenada 'y' (barras horizontales)."""
    if sel is None:
        return []
    s = sel.get("selection") if isinstance(sel, dict) else getattr(sel, "selection", None)
    if s is None:
        return []
    pts = s.get("points") if isinstance(s, dict) else getattr(s, "points", None)
    out = []
    for p in (pts or []):
        cd = p.get("customdata") if isinstance(p, dict) else None
        if cd:
            out.append(cd[0] if isinstance(cd, (list, tuple)) else cd)
        else:
            y = p.get("y") if isinstance(p, dict) else None
            if isinstance(y, str):
                out.append(y)
    seen, res = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            res.append(c)
    return res


def active_xfilter(base_key):
    """Categorías activas del cross-filter de esa pestaña (lee el estado del widget)."""
    n = st.session_state.get(base_key + "_nonce", 0)
    return _picked_cats(st.session_state.get(f"{base_key}_{n}")) or None


def clear_xfilter(base_key):
    """Callback de 'Limpiar selección': sube el nonce -> widget nuevo, sin selección."""
    st.session_state[base_key + "_nonce"] = st.session_state.get(base_key + "_nonce", 0) + 1


def selectable_chart(fig, base_key, key_suffix=""):
    """Dibuja una figura con selección activada bajo la clave de nonce de su cross-filter."""
    n = st.session_state.get(base_key + "_nonce", 0)
    st.plotly_chart(fig, on_select="rerun", key=f"{base_key}_{n}{key_suffix}", width="stretch")


def _min_txt(median_min):
    return f"{median_min:.1f} min".replace(".", ",") if median_min == median_min else "—"


# ── Guarda global: sin datos bajo los filtros del sidebar ─────────────────────
if not len(fu):
    st.warning("Ningún evento cumple los filtros del sidebar. Ajusta los controles.")
    st.stop()

# KPIs reactivos (sobre los agregados filtrados por el sidebar)
k_ab = am.abandonment(fu)
k_ras = am.revenue_at_stake(fu)
k_ds = am.decision_speed(fu)
k_rec = am.recurrence(fo)


# ── Navegación prominente ─────────────────────────────────────────────────────
tab_resumen, tab_a, tab_b, tab_cuando = st.tabs(
    ["Resumen", "Palanca A · Conversión", "Palanca B · Retención", "Cuándo activar"]
)


# ===== RESUMEN (estratégico, cero interacción requerida — test de 30 s) ========
with tab_resumen:
    ui.section_header(
        "El negocio deja dinero sobre la mesa en electrónica",
        "Dos palancas, una misma categoría: recuperar antes de comprar y retener después.",
    )
    ui.action_banner(
        "Recupera los carritos abandonados de electrónica en la franja matutina y retén al "
        "núcleo recurrente con un nudge de recompra a 24–72 h en su misma categoría."
    )

    kpis = [
        ("Revenue en juego", fmt_money_short(k_ras["total_en_juego"]), "carritos abandonados", True),
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
        ui.callout(fmt_money_short(A["rev_en_juego_foco"]), "en juego solo en electronics (82% del premio)")
        ui.caveat("**Palanca A** — antes de comprar: incentivo de cierre en pantalla, en la mañana.")
        ui.caveat("**Palanca B** — después: nudge de recompra a 24–72 h al recurrente.")

    st.markdown("")
    ui.glossary_expander()
    ui.caveat("Las demás historias (conversión, retención, cuándo activar) están en las "
              "pestañas de arriba.")


# ===== PALANCA A — CONVERSIÓN (PN1) ============================================
with tab_a:
    base = "xf_a"
    active = active_xfilter(base)
    fu_a = fu if not active else fu[fu["category_main"].isin(active)]

    ui.insight_card(
        contexto="De cada producto que llega al carrito, ~1 de cada 3 no se compra.",
        hallazgo=f"El abandono ({fmt_pct(k_ab['abandono_global'])}) se concentra en "
                 f"electrónica y electrodomésticos.",
        traduccion=f"{fmt_money_short(k_ras['total_en_juego'])} en juego en carritos "
                   f"abandonados, la mayoría en {FOCO}.",
        accion="Incentivo de cierre (recordatorio de carrito, urgencia/stock, financiación) "
               "a los carritos abandonados de electrónica.",
    )
    ui.action_banner("Prioriza la recuperación de carritos de electrónica: ahí está el 82% del premio.")

    # Héroe seleccionable (desde el nivel del sidebar -> siempre re-elegible)
    selectable_chart(charts.hero_revenue_at_stake(am.revenue_at_stake(fu), foco=FOCO), base)
    if active:
        ui.filter_chip("Filtrando el detalle por: " + ", ".join(active),
                       on_clear=lambda: clear_xfilter(base), key="a_clear")
    else:
        ui.caveat("💡 Haz clic en una barra para filtrar el detalle por esa categoría.")

    with st.expander("Ver detalle analítico", expanded=bool(active)):
        if not len(fu_a):
            st.info("Sin unidades para la selección actual.")
        else:
            d1, d2 = st.columns(2)
            with d1:
                st.plotly_chart(charts.funnel_chart(am.abandonment(fu_a)), key="a_funnel", width="stretch")
                bm = am.brand_mix(fu_a, foco=FOCO)
                if len(bm["g"]):
                    st.plotly_chart(charts.brand_chart(bm), key="a_brand", width="stretch")
                else:
                    st.info(f"Sin marcas con suficiente volumen en {FOCO} para la selección.")
            with d2:
                st.plotly_chart(charts.abandonment_by_category(am.abandonment(fu)), key="a_abandono", width="stretch")
                ui.caveat("El mapa de abandono por categoría se mantiene completo como referencia; "
                          "el funnel y las marcas reaccionan a tu selección.")


# ===== PALANCA B — RETENCIÓN (PN2) =============================================
with tab_b:
    rt = am.repurchase_timing(fo)
    dias_txt = f"{rt['median_days']:.1f}".replace(".", ",") if rt["median_days"] == rt["median_days"] else "—"

    ui.insight_card(
        contexto="La mayoría de compradores compra una sola vez.",
        hallazgo=f"El {fmt_pct(k_rec['pct_repeat'])} recurrente concentra el "
                 f"{fmt_pct(k_rec['pct_rev_repeat'])} del revenue (ticket "
                 f"{fmt_money(k_rec['ticket_repeat'])} vs {fmt_money(k_rec['ticket_one_time'])}).",
        traduccion="Retener a ese núcleo rinde más que captar un comprador nuevo.",
        accion=f"Nudge de recompra a 24–72 h: la 2a compra llega en mediana {dias_txt} días, "
               f"{fmt_pct(rt['same_pct'])} en la misma categoría.",
    )
    ui.action_banner("Activa un programa de recompra para el núcleo recurrente: 1 de cada 3 "
                     "compradores ya trae 7 de cada 10 dólares.")

    if k_rec["repeat"] > 0:
        h1, h2 = st.columns([3, 1], gap="large")
        with h1:
            st.plotly_chart(charts.hero_retention(k_rec), key="b_hero", width="stretch")
        with h2:
            st.markdown("")
            ui.callout(fmt_pct(k_rec["pct_rev_repeat"]), "del revenue lo trae el núcleo recurrente")
    else:
        st.info("Sin compradores recurrentes en el filtro actual (prueba 'Segmento = Todos').")

    with st.expander("Ver detalle analítico", expanded=False):
        d1, d2 = st.columns(2)
        with d1:
            st.plotly_chart(charts.ticket_chart(k_rec), key="b_ticket", width="stretch")
        with d2:
            if rt["n_recurrent"] > 0:
                st.plotly_chart(charts.timing_chart(rt), key="b_timing", width="stretch")
            else:
                st.info("Sin pares de recompra en el filtro actual.")
    ui.caveat("En esta pestaña el control es el **segmento** del sidebar (Recurrentes / One-time); "
              "la retención se mide a nivel de comprador, no por categoría.")


# ===== CUÁNDO ACTIVAR (PN3) ====================================================
with tab_cuando:
    base = "xf_c"
    active = active_xfilter(base)
    fu_c = fu if not active else fu[fu["category_main"].isin(active)]
    fh_c = fh if not active else fh[fh["category_main"].isin(active)]

    hi = am.hourly_intensity(fh_c)
    peak_h = int(hi["compras_x100_vistas"].idxmax()) if len(hi) else 0

    ui.insight_card(
        contexto="El tráfico pica en la tarde, pero no toda visita tiene la misma intención.",
        hallazgo=f"La mañana convierte ~2× por visita (pico de intensidad a las {peak_h}h) y el "
                 f"comprador con intención decide en {_min_txt(k_ds['median_min'])}.",
        traduccion="El momento y el tipo de incentivo importan más que el precio.",
        accion="Activa en la franja matutina (6–10 h) con incentivo inmediato/en pantalla; "
               "el precio NO es el freno.",
    )
    ui.action_banner("Concentra el incentivo en la mañana: misma visita, el doble de intención de compra.")

    if len(hi):
        st.plotly_chart(charts.hourly_intensity_chart(hi), key="c_hourly", width="stretch")
    else:
        st.info("Sin eventos para la selección/franja actual.")
    if active:
        ui.filter_chip("Filtrando por: " + ", ".join(active),
                       on_clear=lambda: clear_xfilter(base), key="c_clear")

    with st.expander("Ver detalle analítico", expanded=bool(active)):
        d1, d2 = st.columns(2)
        with d1:
            if len(fu_c):
                st.plotly_chart(charts.decision_speed_chart(am.decision_speed(fu_c)), key="c_speed", width="stretch")
            else:
                st.info("Sin unidades para la selección actual.")
        with d2:
            pc = am.price_vs_conversion(fu, price_cat)  # control seleccionable (todas las categorías)
            if len(pc):
                selectable_chart(charts.price_vs_conversion_chart(pc, foco=FOCO), base)
                ui.caveat("💡 Haz clic en una categoría para enfocar la intensidad horaria y la "
                          "velocidad de decisión en ella.")
            else:
                st.info("No hay categorías con ≥500 unidades en el filtro actual.")
