"""
app/theme.py — Sistema de diseño (tokens) y plantilla Plotly del dashboard E-commerce SA.

REGLA DE COLOR (§3.2 atributos preatentivos / §3.4 gramática visual):
  El contexto va siempre en la escala de GRISES. Hay DOS acentos, con semántica fija (no
  decorativa): ROJO (BRAND_RED) = dinero en RIESGO / perdido / lo que hay que actuar
  (revenue en juego, abandono, franja a activar); VERDE (BRAND_GREEN) = ganancia REAL /
  positiva (los ingresos de hoy y la categoría que mejor convierte: electronics). Nada de
  azul. Si dos series compiten en un mismo gráfico, se separan por luminosidad de gris.

Tipografía (§3.4 jerarquía): una sola familia sans del sistema, dos pesos (400 regular,
500 medio). Tamaños: título 22, subtítulo 18, cuerpo 15–16.

Principios: Data-to-Ink (§3.1) fondos limpios sin grilla/borde; jerarquía tipográfica
(título oscuro, secundario gris).
"""
import plotly.graph_objects as go
import plotly.io as pio

# ── Tokens de diseño ───────────────────────────────────────────────────────────
BRAND_RED = "#C8102E"   # rojo institucional E-commerce SA — acento de RIESGO/pérdida (lo a actuar)
RED_SOFT = "#FBEAEC"    # rojo muy diluido para fondos de realce (banners/insight)
BRAND_GREEN = "#2E7D32" # verde — ganancia REAL/positiva (electronics como ingreso de hoy)
GREEN_SOFT = "#E8F3EC"  # verde muy diluido para fondos

# Escala de grises (de oscuro a claro). El contexto vive aquí.
GRAY_900 = "#1F2328"    # texto principal / títulos
GRAY_600 = "#57606A"    # texto secundario
GRAY_400 = "#8C959F"    # series de contexto en gráficos
GRAY_200 = "#D0D7DE"    # líneas/bordes sutiles, "el resto" claro
GRAY_100 = "#F4F6F8"    # superficies / fondos de tarjeta

BG = "#FFFFFF"          # fondo del lienzo
SURFACE = "#FFFFFF"     # superficie de tarjetas
TEXT = GRAY_900
MUTED = GRAY_600

FONT_STACK = "'Segoe UI', system-ui, -apple-system, 'Helvetica Neue', Arial, sans-serif"

# Tamaños tipográficos (px)
SIZE_TITLE = 22
SIZE_SUBTITLE = 18
SIZE_BODY = 15

# ── Alias de compatibilidad usados por app/charts.py ───────────────────────────
# (charts.py se escribe ya con la disciplina de un solo acento: rojo = resaltar,
#  grises = contexto; estos alias mapean a los tokens nuevos).
CRIT = BRAND_RED        # el elemento crítico (lo único que salta a la vista)
GREY = GRAY_400         # contexto / "el resto"
GREY_LIGHT = GRAY_200   # contexto aún más al fondo
DARK = GRAY_900         # texto de títulos
# MUTED ya definido arriba (texto secundario)

# ── Plantilla Plotly registrada como "taller" ──────────────────────────────────
_template = go.layout.Template()
_template.layout = go.Layout(
    font=dict(family=FONT_STACK, size=14, color=GRAY_900),
    title=dict(font=dict(size=SIZE_SUBTITLE, color=GRAY_900), x=0.0, xanchor="left"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    # colorway en grises + rojo: el rojo solo aparece donde se asigna explícitamente.
    colorway=[GRAY_400, BRAND_RED, GRAY_200, GRAY_600],
    xaxis=dict(showgrid=False, zeroline=False, showline=True, linecolor=GRAY_200,
               ticks="outside", tickcolor=GRAY_200, tickfont=dict(color=GRAY_600)),
    yaxis=dict(showgrid=False, zeroline=False, showline=False, tickfont=dict(color=GRAY_600)),
    margin=dict(l=10, r=20, t=56, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(color=GRAY_600)),
    hoverlabel=dict(font_size=13, font_family=FONT_STACK, bgcolor="white",
                    bordercolor=GRAY_200, font_color=GRAY_900),
)
pio.templates["taller"] = _template


def base_fig():
    """Figura vacía con la plantilla del taller (fondo transparente, sin grilla)."""
    fig = go.Figure()
    fig.update_layout(template="taller")
    return fig


# ── Helpers de formato (es-CO: coma decimal) ────────────────────────────────────
def fmt_money(x, decimals=0):
    """Monto en USD con separador de miles. Ej: 2076999 -> '$2,076,999'."""
    try:
        return f"${x:,.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def fmt_money_short(x):
    """Monto compacto para titulares. Ej: 2076999 -> '$2,08 M'."""
    try:
        if abs(x) >= 1_000_000:
            return f"${x/1_000_000:.2f} M".replace(".", ",")
        if abs(x) >= 1_000:
            return f"${x/1_000:.0f} K"
        return f"${x:,.0f}"
    except (TypeError, ValueError):
        return "—"


def fmt_pct(x, decimals=1):
    """Porcentaje con coma decimal. Ej: 32.4 -> '32,4%'."""
    try:
        return f"{x:.{decimals}f}%".replace(".", ",")
    except (TypeError, ValueError):
        return "—"


def fmt_int(x):
    """Entero con separador de miles. Ej: 7511 -> '7,511'."""
    try:
        return f"{int(round(x)):,}"
    except (TypeError, ValueError):
        return "—"
