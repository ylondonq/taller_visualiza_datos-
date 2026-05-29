"""
app/charts.py — Figuras Plotly del dashboard (E-commerce SA).

Cada función recibe los agregados de src.agg_metrics y devuelve un go.Figure listo para
st.plotly_chart. Reconstruye en Plotly nativo los héroes A y B y el resto de gráficos de
soporte.

DISCIPLINA DE COLOR (§3.2 atributos preatentivos / §3.4 gramática visual): el ÚNICO acento
es BRAND_RED, reservado para el elemento a resaltar (electronics / recurrentes / pico / lo
que se pierde). Todo el contexto va en grises (más claro = más al fondo). NO hay verde ni
azul: si dos series compiten, se separan por luminosidad de gris, no por matiz. Títulos
autoexplicativos orientados a acción (§3.5).

Las gráficas con dimensión de categoría (revenue por categoría, abandono por categoría,
precio vs conversión) llevan `customdata` con la categoría para alimentar el cross-filter
estilo Power BI del app (selección -> filtra el resto de la pestaña).
"""
import sys
from pathlib import Path

import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme  # noqa: E402
from theme import (  # noqa: E402
    BRAND_RED, BRAND_GREEN, GRAY_900, GRAY_600, GRAY_400, GRAY_200,
    fmt_money, fmt_money_short, fmt_pct, fmt_int,
)

CTX = GRAY_400        # contexto principal (series "el resto")
CTX_BG = GRAY_200     # contexto al fondo (lo menos importante)


# ── Ingresos reales por categoría (Resumen · pregunta 1: dónde se gana hoy) ────
def revenue_share_chart(rev_cat, foco="electronics", title=None, top_n=6, height=360):
    """Barras horizontales del % de ingresos REALES por categoría; foco en rojo, resto gris.
    Responde '¿cuáles negocios me dan más ingresos?'."""
    rc = rev_cat.sort_values("revenue", ascending=False).head(top_n).iloc[::-1]
    cats = [str(c) for c in rc["category_main"]]
    vals = rc["pct"].tolist()
    # VERDE para el foco: son ingresos REALES (ganancia positiva), no dinero en riesgo.
    colors = [BRAND_GREEN if c == foco else CTX_BG for c in cats]
    fig = theme.base_fig()
    fig.add_bar(
        x=vals, y=cats, orientation="h", marker_color=colors, customdata=cats,
        text=[fmt_pct(v) for v in vals], textposition="outside", textfont=dict(color=GRAY_600),
        hovertemplate="%{customdata}: %{x:.1f}% de los ingresos<extra></extra>",
    )
    fig.update_layout(
        title=title or "Dónde se gana hoy: ingresos por categoría",
        xaxis_title="% de los ingresos", yaxis_title="Categoría",
        xaxis_range=[0, max(vals) * 1.18], height=height, showlegend=False,
    )
    return fig


# ── Héroe A (PN1): revenue en juego por categoría ─────────────────────────────
def hero_revenue_at_stake(ras, foco="electronics", title=None, height=420, annotate=True):
    """Barras horizontales del revenue abandonado por categoría; foco en rojo, resto gris.
    Responde '¿en cuáles podría tener más si se concretaran las compras?'."""
    prize = ras["prize"].sort_values("revenue_en_juego")  # menor->mayor (mayor arriba)
    cats = list(prize.index)
    vals = prize["revenue_en_juego"].tolist()
    colors = [BRAND_RED if c == foco else CTX_BG for c in cats]

    fig = theme.base_fig()
    fig.add_bar(
        x=vals, y=cats, orientation="h", marker_color=colors,
        customdata=cats,
        text=[fmt_money_short(v) for v in vals], textposition="outside",
        textfont=dict(color=GRAY_600),
        hovertemplate="%{customdata}: %{x:$,.0f} en juego<extra></extra>",
    )
    top = prize["revenue_en_juego"].max()
    fig.update_layout(
        title=title or "Dónde se queda el dinero: carritos abandonados por categoría",
        xaxis_title="Revenue en juego (USD)", yaxis_title="Categoría",
        xaxis_range=[0, top * 1.18], height=height, showlegend=False,
    )
    if annotate and foco in prize.index:
        fig.add_annotation(
            x=prize.loc[foco, "revenue_en_juego"], y=foco,
            text="82% del premio total<br>se concentra aquí",
            showarrow=True, arrowhead=2, arrowcolor=BRAND_RED, ax=-90, ay=-30,
            font=dict(color=BRAND_RED, size=12), align="left",
        )
    return fig


# ── Héroe B (PN2): concentración de valor de los recurrentes ──────────────────
def hero_retention(rec, title=None):
    """Dos barras 100% apiladas: el 31,7% de compradores (recurrentes) = 69% del revenue."""
    pct_rep = rec["pct_repeat"]
    pct_rev_rep = rec["pct_rev_repeat"]
    x = ["Compradores", "Revenue"]

    fig = theme.base_fig()
    fig.add_bar(
        name="Recurrentes (≥2 compras)", x=x, y=[pct_rep, pct_rev_rep],
        marker_color=BRAND_RED,
        text=[fmt_pct(pct_rep), fmt_pct(pct_rev_rep)], textposition="inside",
        insidetextfont=dict(color="white", size=15),
        hovertemplate="Recurrentes: %{y:.1f}%<extra></extra>",
    )
    fig.add_bar(
        name="One-time (1 compra)", x=x, y=[100 - pct_rep, 100 - pct_rev_rep],
        marker_color=CTX,
        text=[fmt_pct(100 - pct_rep), fmt_pct(100 - pct_rev_rep)], textposition="inside",
        insidetextfont=dict(color="white", size=13),
        hovertemplate="One-time: %{y:.1f}%<extra></extra>",
    )
    fig.update_layout(
        barmode="stack",
        title=title or "El mismo grupo: 1 de cada 3 compradores trae 7 de cada 10 dólares",
        yaxis=dict(title="% del total", range=[0, 100], ticksuffix="%"),
        height=420, legend=dict(orientation="h", y=1.08, x=0),
    )
    # flecha que conecta el mismo grupo de un eje al otro (recorrido visual, §3.4)
    fig.add_annotation(
        x=0, y=pct_rep / 2, ax=1, ay=pct_rev_rep / 2, xref="x", yref="y", axref="x", ayref="y",
        text="", showarrow=True, arrowhead=2, arrowcolor=BRAND_RED, arrowwidth=2,
    )
    return fig


# ── Funnel por unidad (PN1) ───────────────────────────────────────────────────
def funnel_chart(ab, title=None, note=None):
    """Funnel por unidad (producto-en-sesión): vistas -> carrito -> compra. La caída
    carrito->compra (los carritos abandonados) se resalta en rojo y con anotación in-situ.
    title: título-acción (verbo + cifra). note: subtítulo/anotación que traduce el hallazgo."""
    gf = ab["gf"]
    abandono = 100 - gf["cart_to_purchase"]
    vals = [gf["n_units"], gf["reached_cart"], gf["reached_purchase"]]
    # etiquetas con separador de miles es-CO (puntos) y % con coma decimal — NUNCA "k"
    def _miles(n):
        return f"{int(round(n)):,}".replace(",", ".")

    def _pct1(p):
        return f"{p:.1f}".replace(".", ",")
    labels = [f"{_miles(v)} ({_pct1(v / vals[0] * 100)}%)" for v in vals]
    fig = theme.base_fig()
    fig.add_trace(go.Funnel(
        y=["Vista", "Llega al carrito", "Compra"],
        x=vals, text=labels, textinfo="text",
        marker_color=[CTX_BG, CTX, BRAND_RED],  # gradiente gris->rojo: la compra es lo que importa
        hovertemplate="%{y}: %{text}<extra></extra>",
    ))
    fig.update_layout(
        title=title or f"Funnel por unidad — solo el {fmt_pct(gf['conv_rate'], 2)} de lo visto se compra",
        height=420, showlegend=False, margin=dict(l=10, r=20, t=60, b=64),
    )
    # anotación dentro del gráfico: la fuga que importa (carrito -> compra), en rojo
    fig.add_annotation(
        x=0.97, y=0.5, xref="paper", yref="paper", xanchor="right", showarrow=False,
        text=f"<b>{fmt_pct(abandono)}</b><br>llega al carrito<br>y no compra",
        font=dict(color=BRAND_RED, size=13), align="right",
    )
    if note:
        fig.add_annotation(
            x=0.0, y=-0.18, xref="paper", yref="paper", xanchor="left", showarrow=False,
            text=note, font=dict(color=GRAY_600, size=12.5), align="left",
        )
    return fig


# ── Héroe intensidad horaria de un panel (PN3) ────────────────────────────────
def hourly_intensity_hero(hi, title=None, band=(6, 10)):
    """Un solo panel: compras por 100 vistas por hora. La FRANJA estratégica (6–10 h) se
    resalta como banda roja translúcida y sus barras en rojo; el resto del día en gris.
    No se marca una sola hora: la decisión es activar en toda la franja matutina (§3.4)."""
    horas = list(hi.index)
    lo, hi_b = band
    colors = [BRAND_RED if lo <= h <= hi_b else CTX_BG for h in horas]
    fig = theme.base_fig()
    fig.add_bar(x=horas, y=hi["compras_x100_vistas"], marker_color=colors,
                hovertemplate="%{x}h: %{y:.2f} compras/100 vistas<extra></extra>")
    fig.add_vrect(
        x0=lo - 0.5, x1=hi_b + 0.5, fillcolor=BRAND_RED, opacity=0.08, line_width=0,
        annotation_text=f"Franja matutina {lo}–{hi_b} h", annotation_position="top left",
        annotation_font=dict(color=BRAND_RED, size=12),
    )
    fig.update_layout(
        title=title or f"Franja matutina ({lo}–{hi_b} h): convierte ~2× por visita",
        xaxis_title="Hora del día", yaxis_title="Compras por 100 vistas",
        height=420, showlegend=False,
    )
    return fig


# ── Abandono por categoría (PN1) ──────────────────────────────────────────────
def abandonment_by_category(ab, foco=("electronics", "computers")):
    """Tasa de abandono por categoría, anotada con el volumen de carritos abandonados."""
    aband_cat = ab["aband_cat"].sort_values("abandono")
    cats = list(aband_cat.index)
    vals = aband_cat["abandono"].tolist()
    vols = aband_cat["abandonados"].tolist()
    colors = [BRAND_RED if c in foco else CTX_BG for c in cats]

    fig = theme.base_fig()
    fig.add_bar(
        x=vals, y=cats, orientation="h", marker_color=colors,
        customdata=cats,
        text=[f"{fmt_int(v)} carritos" for v in vols], textposition="outside",
        textfont=dict(color=GRAY_600),
        hovertemplate="%{customdata}: %{x:.1f}% abandono<extra></extra>",
    )
    g = ab["abandono_global"]
    fig.add_vline(x=g, line_dash="dash", line_color=BRAND_RED,
                  annotation_text=f"Global {fmt_pct(g)}", annotation_position="top")
    fig.update_layout(
        title="Abandono de carrito por categoría (% que llega al carrito y no compra)",
        xaxis_title="% de abandono", yaxis_title=None,
        xaxis_range=[0, max(vals) * 1.25], height=420, showlegend=False,
    )
    return fig


# ── Marca dentro de electronics (PN1) ─────────────────────────────────────────
def brand_chart(bm, top_n=8):
    """Carritos por marca dentro de la categoría foco. Rojo = abandonados (lo que se pierde),
    gris = comprados. SIN verde: un solo color semántico (§3.2)."""
    g = bm["g"].sort_values("carritos", ascending=False).head(top_n).iloc[::-1]
    fig = theme.base_fig()
    fig.add_bar(name="Abandonados", x=g["abandonados"], y=g.index, orientation="h",
                marker_color=BRAND_RED,
                hovertemplate="%{y}: %{x:,} abandonados<extra></extra>")
    fig.add_bar(name="Comprados", x=g["comprados"], y=g.index, orientation="h",
                marker_color=CTX,
                hovertemplate="%{y}: %{x:,} comprados<extra></extra>")
    fig.update_layout(
        barmode="stack",
        title=f"Marcas en {bm['foco']}: dónde están los carritos (y cuántos se pierden)",
        xaxis_title="Carritos (unidades producto-en-sesión)", yaxis_title=None,
        height=420, legend=dict(orientation="h", y=1.08, x=0),
    )
    return fig


# ── Timing de recompra (PN2) ──────────────────────────────────────────────────
def timing_chart(rt, cap_days=30):
    """Distribución de días entre la 1a y la 2a compra (cap en la ventana de octubre)."""
    days = rt["days"]
    days = days[days <= cap_days]
    fig = theme.base_fig()
    fig.add_histogram(x=days, nbinsx=30, marker_color=CTX,
                      hovertemplate="%{x:.0f} días: %{y} usuarios<extra></extra>")
    med = rt["median_days"]
    fig.add_vline(x=med, line_dash="dash", line_color=BRAND_RED,
                  annotation_text=f"Mediana {med:.1f} días".replace(".", ","),
                  annotation_position="top")
    fig.update_layout(
        title="¿Cuándo vuelve el comprador? Días entre la 1a y la 2a compra",
        xaxis_title="Días hasta la 2a compra (ventana octubre)", yaxis_title="Usuarios recurrentes",
        height=380, showlegend=False,
    )
    return fig


# ── Ticket por segmento (PN2) ─────────────────────────────────────────────────
def ticket_chart(rec):
    """Ticket promedio one-time vs recurrente (≈5×)."""
    fig = theme.base_fig()
    vals = [rec["ticket_one_time"], rec["ticket_repeat"]]
    fig.add_bar(
        x=["One-time", "Recurrente"], y=vals, marker_color=[CTX, BRAND_RED],
        text=[fmt_money(v) for v in vals], textposition="outside",
        textfont=dict(color=GRAY_600),
        hovertemplate="%{x}: %{y:$,.0f}<extra></extra>",
    )
    fig.update_layout(
        title="Ticket promedio: el recurrente vale ~5× más",
        yaxis_title="USD por comprador", xaxis_title=None,
        yaxis_range=[0, max(vals) * 1.2], height=380, showlegend=False,
    )
    return fig


# (Se eliminó hourly_intensity_chart de 2 paneles: la distribución normalizada era
#  redundante con la intensidad. Cuándo activar usa solo hourly_intensity_hero con la
#  banda 6–10 h. §7: "deja UN solo visual horario").


# ── Velocidad de decisión (PN3) ───────────────────────────────────────────────
def decision_speed_chart(ds, cap_min=30):
    """Distribución del tiempo de decisión (minutos), cap para legibilidad."""
    dt = ds["decision_time"]
    dt = dt[dt <= cap_min]
    fig = theme.base_fig()
    fig.add_histogram(x=dt, nbinsx=30, marker_color=CTX,
                      hovertemplate="%{x:.0f} min: %{y} unidades<extra></extra>")
    med = ds["median_min"]
    fig.add_vline(x=med, line_dash="dash", line_color=BRAND_RED,
                  annotation_text=f"Mediana {med:.1f} min".replace(".", ","),
                  annotation_position="top")
    fig.update_layout(
        title=f"Decisión en minutos: {fmt_pct(ds['pct_lt5'])} compra en <5 min",
        xaxis_title="Minutos del 1er view a la compra (≤30 min)", yaxis_title="Unidades",
        height=380, showlegend=False,
    )
    return fig


# ── Precio vs conversión (PN3) ────────────────────────────────────────────────
def price_vs_conversion_chart(pc, foco="electronics"):
    """Scatter precio mediana por categoría vs conversión; el precio no es el freno.
    Electronics en VERDE y con bola más grande: es la mejor conversión (ganancia positiva)."""
    cats = list(pc.index)
    colors = [BRAND_GREEN if c == foco else CTX for c in cats]
    sizes = [20 if c == foco else 11 for c in cats]
    fig = theme.base_fig()
    fig.add_scatter(
        x=pc["precio_mediana"], y=pc["conv_rate"], mode="markers+text",
        text=cats, textposition="top center", textfont=dict(size=11, color=GRAY_600),
        marker=dict(size=sizes, color=colors), customdata=cats,
        hovertemplate="%{customdata}<br>precio mediana %{x:$,.0f}<br>conv %{y:.2f}%<extra></extra>",
    )
    fig.update_layout(
        title="El precio no es el freno: las categorías baratas convierten peor, no mejor",
        xaxis_title="Precio mediana por producto (USD)", yaxis_title="Conversión por unidad (%)",
        height=420, showlegend=False,
    )
    return fig
