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
import importlib
import sys
from pathlib import Path

import streamlit as st

_APP_DIR = Path(__file__).resolve().parent
_ROOT = _APP_DIR.parent
sys.path.append(str(_ROOT))
sys.path.insert(0, str(_APP_DIR))
from src import agg_metrics as am  # noqa: E402
import theme  # noqa: E402
import ui  # noqa: E402
import charts  # noqa: E402

# Streamlit Community Cloud, tras un redeploy "en caliente" (git pull sin reiniciar el
# proceso), puede dejar en sys.modules una versión CACHEADA de estos módulos hermanos
# (los importamos vía sys.path, no como paquete, así que su watcher no siempre los recarga).
# Eso provoca AttributeError al usar código nuevo (p. ej. ui.about_data_expander) contra un
# módulo viejo. Forzamos recarga del archivo recién clonado en cada arranque para auto-curar
# el deploy. Orden: theme primero (ui/charts dependen de él). Coste despreciable.
for _m in (theme, ui, charts, am):
    importlib.reload(_m)
from theme import fmt_money, fmt_money_short, fmt_pct  # noqa: E402

st.set_page_config(page_title="E-commerce SA — Inteligencia de conversión", page_icon="🛒", layout="wide")

FOCO = "electronics"


# ── Carga de AGREGADOS (cacheada; nunca el clickstream crudo) ─────────────────
# La caché se versiona por una huella de los parquets (mtime+size). Así, cuando Streamlit
# Community Cloud hace un redeploy "en caliente" y los parquets cambian, el argumento `v`
# cambia y la caché se invalida sola (de lo contrario @st.cache_data devolvería el resultado
# viejo aunque el dato haya cambiado — fue la causa de un KeyError tras añadir columnas).
_AGG_FILES = (am.AGG_UNITS, am.AGG_OCCASIONS, am.AGG_HOURLY,
              am.AGG_PRICE_CAT, am.AGG_REVENUE_CAT, am.AGG_ANCHORS)


def _data_version():
    parts = []
    for p in _AGG_FILES:
        try:
            s = p.stat()
            parts.append(f"{s.st_mtime_ns}:{s.st_size}")
        except OSError:
            parts.append("na")
    return "|".join(parts)


@st.cache_data(show_spinner="Cargando agregados…")
def load_units(v):
    return am.load_units()


@st.cache_data(show_spinner=False)
def load_occasions(v):
    return am.load_occasions()


@st.cache_data(show_spinner=False)
def load_hourly(v):
    return am.load_hourly()


@st.cache_data(show_spinner=False)
def load_price_cat(v):
    return am.load_price_cat()


@st.cache_data(show_spinner=False)
def load_revenue_cat(v):
    return am.load_revenue_cat()


@st.cache_data(show_spinner=False)
def load_anchors(v):
    return am.load_anchors()


ui.inject_global_css()
ui.header_bar()

_DV = _data_version()
units = load_units(_DV)
occ = load_occasions(_DV)
hourly = load_hourly(_DV)
price_cat = load_price_cat(_DV)
revenue_cat = load_revenue_cat(_DV)
A = load_anchors(_DV)


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

# Cifras-ancla fijas para los títulos-acción y el Plan (no se mueven con los filtros).
# El retén se calcula desde la recurrencia COMPLETA (no del esquema de anclas) para no
# depender de columnas nuevas en el parquet de anclas.
FOCO_STAKE = A["rev_en_juego_foco"]                       # $2,08 M en electronics
TOTAL_STAKE = A["rev_en_juego_total"]                     # $2,53 M en juego (total)
FOCO_SHARE = FOCO_STAKE / TOTAL_STAKE * 100               # 82% del premio
RECOVER_10 = FOCO_STAKE * 0.10                            # +$207.700/mes (recuperar 10% en electronics)
_rec_full = am.recurrence(occ)                            # recurrencia sobre la muestra completa
GAP_OT_REC = _rec_full["ticket_repeat"] - _rec_full["ticket_one_time"]  # brecha de ticket
RETAIN_5 = _rec_full["one_time"] * 0.05 * GAP_OT_REC      # +$306.850 (mover 5% de one-time a recurrente)


# ── Navegación prominente ─────────────────────────────────────────────────────
tab_resumen, tab_e1, tab_e2, tab_cuando, tab_plan = st.tabs(
    ["Resumen", "Estrategia 1 · Conversión", "Estrategia 2 · Retención", "Cuándo activar", "Plan de acción"]
)


# ===== RESUMEN (estratégico, cero interacción — test de 30 s) ==================
with tab_resumen:
    ui.section_header(
        "¿Cuáles negocios me dan más ingresos y en cuáles podría tener aún más "
        "si se concretaran las compras?",
        "La respuesta es la misma categoría que ya sostiene el negocio.",
    )
    # Tono semántico: rojo = dinero en riesgo (a actuar); verde = valor real/positivo; gris = neutro.
    kpis = [
        ("Revenue en juego", f"{fmt_money_short(TOTAL_STAKE)} USD", "carritos abandonados", "red"),
        ("Abandono de carrito", fmt_pct(k_ab["abandono_global"]), "de lo que llega al carrito", None),
        ("Conversión por unidad", fmt_pct(k_ab["gf"]["conv_rate"], 2), "de lo visto se compra", None),
        ("Recurrentes", fmt_pct(k_rec["pct_repeat"]), f"= {fmt_pct(k_rec['pct_rev_repeat'])} del revenue", "green"),
        ("Decisión (mediana)", _min_txt(k_ds["median_min"]), "del 1er view a la compra", None),
    ]
    for col, (lbl, val, sub, acc) in zip(st.columns(5), kpis):
        col.markdown(ui.kpi_card(lbl, val, sub, acc), unsafe_allow_html=True)

    st.markdown("")
    # Narrativa en el ORDEN de las dos preguntas: (1) dónde se gana hoy, (2) dónde por recuperar.
    elec_pct = float(revenue_cat.set_index("category_main").loc[FOCO, "pct"]) \
        if FOCO in revenue_cat["category_main"].astype(str).tolist() else 0.0
    q1, q2 = st.columns(2, gap="large")
    with q1:
        st.plotly_chart(
            charts.revenue_share_chart(
                revenue_cat, foco=FOCO,
                title=f"1 · Dónde se gana hoy: {FOCO} = {elec_pct:.0f}% de los ingresos"),
            key="r_revenue_real", width="stretch",
        )
    with q2:
        st.plotly_chart(
            charts.hero_revenue_at_stake(
                am.revenue_at_stake(units), foco=FOCO, annotate=False, height=360,
                title=f"2 · Dónde hay por recuperar: {FOCO} = {FOCO_SHARE:.0f}% ({fmt_money_short(FOCO_STAKE)})"),
            key="r_revenue_stake", width="stretch",
        )
    ui.message_line("Es donde más se gana hoy <b>y</b> donde más hay por recuperar: "
                    "la misma categoría sostiene el negocio y guarda la mayor oportunidad.")
    ui.glossary_expander()


# ===== ESTRATEGIA 1 · CONVERSIÓN (PN1) =========================================
with tab_e1:
    ui.message_line("¿En qué productos de electrónica y a qué hora vale aumentar la conversión?")

    cf = k_ab["cat_funnel"]
    elec_cart = int(cf.loc[FOCO, "reached_cart"]) if FOCO in cf.index else 0
    rc_txt = f"{k_ab['gf']['reached_cart']:,}".replace(",", ".")
    ec_txt = f"{elec_cart:,}".replace(",", ".")

    hcol, scol = st.columns([3, 2], gap="large")
    with hcol:
        st.plotly_chart(
            charts.funnel_chart(
                k_ab,
                title="1 de cada 3 que llega al carrito no compra: recupéralo",
                note=f"De los {rc_txt} que llegan al carrito, ~{ec_txt} son de electronics.",
            ),
            key="e1_hero", width="stretch",
        )
    with scol:
        st.markdown("")
        bm = am.brand_mix(fu, foco=FOCO)
        g = bm["g"]
        # pico de compra de electronics (franja matutina), desde el agregado horario
        he = hourly[(hourly["category_main"].astype(str) == FOCO)
                    & (hourly["event_type"].astype(str) == "purchase")]
        he_h = he.groupby("hour")["n"].sum()
        elec_peak = int(he_h.idxmax()) if len(he_h) else 7
        if len(g) and bm["n_total"]:
            gg = g.sort_values("carritos", ascending=False)
            top2 = gg.head(2)
            share2 = top2["carritos"].sum() / bm["n_total"] * 100
            names = " + ".join(str(b).title() for b in top2.index)
            tk_brand = str(gg["ticket"].idxmax()).title()
            tk_val = float(gg["ticket"].max())
            st.markdown(ui.stat_chip("🛒", fmt_pct(share2, 0), f"de los carritos: {names}"),
                        unsafe_allow_html=True)
            st.markdown("")
            st.markdown(ui.stat_chip("🏷️", fmt_money(tk_val), f"mayor ticket · {tk_brand}"),
                        unsafe_allow_html=True)
            st.markdown("")
            st.markdown(ui.stat_chip("⏱️", f"{elec_peak}h", "pico de compra de electronics (6–10 h)"),
                        unsafe_allow_html=True)
        else:
            st.info(f"Sin marcas con volumen suficiente en {FOCO} para el filtro actual.")

    ui.action_chip("Recordatorio de carrito a Apple y Samsung con cierre inmediato "
                   "(urgencia/stock, financiación), en la franja matutina (pico 7h).", icon="🎯")

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
    ui.message_line(
        f"El {fmt_pct(k_rec['pct_repeat'])} de los compradores trae el "
        f"{fmt_pct(k_rec['pct_rev_repeat'])} del revenue."
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
            milestones, sub = None, None
            if len(days):
                p1 = float((days <= 1).mean() * 100)
                p7 = float((days <= 7).mean() * 100)
                p14 = float((days <= 14).mean() * 100)
                milestones = [(100 / 14, f"1 día · {p1:.0f}%"), (700 / 14, f"7 días · {p7:.0f}%")]
                sub = f"{p14:.0f}% vuelve en ≤14 días"
            # "¿cuándo vuelve?": timeline 0→14 d con la ventana del nudge 24–72 h resaltada
            ui.time_panel(
                value=_days_txt(rt["median_days"]),
                caption="¿cuándo vuelve? · mediana a la 2ª compra",
                milestones=milestones, band=(100 / 14, 300 / 14, "nudge 24–72 h"), sub=sub,
            )
            st.markdown("")
            # "¿a qué vuelve?": número grande de misma-categoría
            if rt["same_pct"] == rt["same_pct"]:
                ui.callout(fmt_pct(rt["same_pct"]), "¿a qué vuelve? — la misma categoría 🔁")
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
    pc = am.price_vs_conversion(fu, price_cat)
    ui.message_line("La mañana convierte ~2× por visita: concentra el incentivo en la franja 6–10 h.")

    if len(hi):
        hcol, scol = st.columns([3, 2], gap="large")
        with hcol:
            st.plotly_chart(charts.hourly_intensity_hero(hi), key="c_hero", width="stretch")
        with scol:
            # "El precio no es el freno" — evidencia del 'con qué' (no precio), con relevancia.
            if len(pc) and FOCO in pc.index:
                cheap_cat = pc["precio_mediana"].idxmin()
                best = {"name": FOCO.title(), "price": fmt_money(pc.loc[FOCO, "precio_mediana"]),
                        "conv": fmt_pct(pc.loc[FOCO, "conv_rate"], 2)}
                cheap = {"name": str(cheap_cat).title(), "price": fmt_money(pc.loc[cheap_cat, "precio_mediana"]),
                         "conv": fmt_pct(pc.loc[cheap_cat, "conv_rate"], 2)}
                ui.price_compare_card(best, cheap)
            else:
                ui.caveat("Sin categorías con ≥500 unidades para comparar precio vs conversión.")
            st.markdown("")
            ui.time_panel(value=_min_txt(k_ds["median_min"]), caption="decisión: 1er view → compra",
                          sub=f"{fmt_pct(k_ds['pct_lt5'])} decide en menos de 5 min")
    else:
        st.info("Sin eventos para la franja/filtro actual.")

    ui.action_chip("Activa en la franja 6–10 h con incentivo inmediato/en pantalla; "
                   "el precio no es el freno.", icon="🎯")

    with st.expander("Ver detalle analítico"):
        d1, d2 = st.columns(2)
        with d1:
            st.plotly_chart(charts.decision_speed_chart(k_ds), key="c_speed", width="stretch")
        with d2:
            if len(pc):
                st.plotly_chart(charts.price_vs_conversion_chart(pc, foco=FOCO), key="c_price", width="stretch")
            else:
                st.info("No hay categorías con ≥500 unidades en el filtro actual.")


# ===== PLAN DE ACCIÓN (cierre que motiva — solo headline + 2 tarjetas, §8) =====
with tab_plan:
    # Titular: "$2,53 M" (trunca a 2 decimales, como pide el prompt; el KPI muestra el redondeo 2,54)
    _total_m = f"${int(TOTAL_STAKE / 10000) / 100:.2f} M USD".replace(".", ",")
    ui.plan_headline(f"Hay <b>{_total_m}</b> sobre la mesa — y casi todo está en electrónica.")
    p1, p2 = st.columns(2, gap="large")
    p1.markdown(
        ui.action_card(
            "Estrategia 1 · Recuperar",
            "Carritos de Apple y Samsung, cierre inmediato en la mañana.",
            f"+{fmt_money(RECOVER_10)}", "/ mes — recuperando el 10% de lo abandonado en electronics"),
        unsafe_allow_html=True)
    p2.markdown(
        ui.action_card(
            "Estrategia 2 · Retener",
            "Nudge de recompra a 24–72 h, en la misma categoría.",
            f"+{fmt_money(RETAIN_5)}", "moviendo el 5% de los compradores de una vez al núcleo recurrente"),
        unsafe_allow_html=True)
