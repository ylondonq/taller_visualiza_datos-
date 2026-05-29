"""
app/ui.py — Sistema de componentes del dashboard E-commerce SA (ayudas NO-gráfico).

Devuelve HTML inyectado con st.markdown(..., unsafe_allow_html=True) o renderiza widgets
de Streamlit directamente. Centraliza la marca, las tarjetas KPI, la CHTA estructurada,
el banner de acción, los encabezados de sección, los chips de filtro y el glosario.

Principios del curso:
  · Data-to-Ink (§3.1) + Gestalt/proximidad (§3.3): aire y separadores finos en vez de
    cajas/sombras pesadas; lo que es un concepto va junto.
  · Atributos preatentivos (§3.2): un único acento rojo para lo importante; resto gris.
  · Acto de habla "motivar" (§3.5): banner de acción e insight cards con jerarquía.
  · Orientación del neófito (§0/§4.3): marca, glosario y chip de contexto de datos.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme  # noqa: E402


# ── CSS global (una sola inyección) ────────────────────────────────────────────
_CSS = """
<style>
/* Tipografía y lienzo (Data-to-Ink: superficie limpia) */
html, body, [class*="css"], .stMarkdown, .stApp { font-family: __FONT__; }
.stApp { background: __BG__; }
.block-container { padding-top: 1.1rem; padding-bottom: 3rem; max-width: 1280px; }

/* Quitar chrome de Streamlit que no aporta (menú/footer/toolbar) */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }

/* Navegación prominente: pestañas grandes con estado activo de alto contraste (§3.4) */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid __GRAY200__; }
.stTabs [data-baseweb="tab"] {
  height: auto; padding: 11px 18px; font-size: 15px; font-weight: 500;
  color: __GRAY600__; background: transparent; border-radius: 8px 8px 0 0;
}
.stTabs [data-baseweb="tab"]:hover { color: __GRAY900__; background: __GRAY100__; }
.stTabs [aria-selected="true"] {
  color: __RED__ !important; background: transparent;
  border-bottom: 3px solid __RED__;
}

/* Barra de marca */
.ecsa-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 4px 16px 4px; margin-bottom: 4px; border-bottom: 1px solid __GRAY200__;
}
.ecsa-brand { display: flex; align-items: center; gap: 14px; }
.ecsa-logo {
  width: 44px; height: 44px; border-radius: 12px; background: __RED__;
  color: #fff; font-weight: 600; font-size: 24px; line-height: 44px; text-align: center;
  box-shadow: 0 1px 2px rgba(0,0,0,.12);
}
.ecsa-brand-name { font-size: 20px; font-weight: 600; color: __GRAY900__; line-height: 1.15; }
.ecsa-brand-sub { font-size: 13px; color: __GRAY600__; }
.ecsa-datachip {
  font-size: 12.5px; color: __GRAY600__; background: __GRAY100__;
  border: 1px solid __GRAY200__; border-radius: 999px; padding: 6px 14px; white-space: nowrap;
}

/* Encabezado de sección */
.ecsa-sec-title { font-size: 22px; font-weight: 600; color: __GRAY900__; margin: 6px 0 2px 0; }
.ecsa-sec-sub { font-size: 15px; color: __GRAY600__; margin-bottom: 10px; }

/* Tarjeta KPI (jerarquía: ancla resaltada) */
.ecsa-kpi {
  padding: 14px 16px; border: 1px solid __GRAY200__; border-radius: 12px;
  background: __SURFACE__; height: 100%;
}
.ecsa-kpi.accent { border-color: __RED__; border-top: 3px solid __RED__; background: __REDSOFT__; }
.ecsa-kpi .lbl { font-size: 12.5px; color: __GRAY600__; text-transform: uppercase; letter-spacing: .03em; }
.ecsa-kpi .val { font-size: 26px; font-weight: 600; color: __GRAY900__; line-height: 1.25; margin-top: 2px; }
.ecsa-kpi.accent .val { color: __RED__; }
.ecsa-kpi .sub { font-size: 12.5px; color: __GRAY600__; margin-top: 2px; }

/* Callout de número grande (cuando un solo número ES la historia, §3.2 tamaño) */
.ecsa-callout { padding: 6px 2px 10px 2px; }
.ecsa-callout .big { font-size: 44px; font-weight: 600; color: __RED__; line-height: 1.05; }
.ecsa-callout .cap { font-size: 14px; color: __GRAY600__; margin-top: 2px; }

/* Banner de acción (acto de habla "motivar", §3.5) */
.ecsa-banner {
  display: flex; align-items: center; gap: 12px;
  background: __REDSOFT__; border-left: 4px solid __RED__; border-radius: 8px;
  padding: 12px 16px; margin: 6px 0 14px 0;
}
.ecsa-banner .tag {
  font-size: 11px; font-weight: 600; color: #fff; background: __RED__;
  border-radius: 6px; padding: 3px 9px; text-transform: uppercase; letter-spacing: .04em; white-space: nowrap;
}
.ecsa-banner .txt { font-size: 15.5px; color: __GRAY900__; }

/* Insight card: CHTA estructurada (§3.5 patrón Contexto->Hallazgo->Traduccion->Accion) */
.ecsa-insight {
  border: 1px solid __GRAY200__; border-radius: 12px; padding: 4px 18px; margin-bottom: 14px;
  background: __SURFACE__;
}
.ecsa-insight .row { display: flex; gap: 12px; padding: 11px 0; border-bottom: 1px solid __GRAY100__; }
.ecsa-insight .row:last-child { border-bottom: none; }
.ecsa-insight .ic { font-size: 16px; width: 22px; text-align: center; flex: none; }
.ecsa-insight .lbl { font-size: 11.5px; font-weight: 600; color: __GRAY600__; text-transform: uppercase; letter-spacing: .04em; width: 96px; flex: none; padding-top: 1px; }
.ecsa-insight .body { font-size: 15px; color: __GRAY900__; }
.ecsa-insight .row.accion .body { font-weight: 500; }
.ecsa-insight .row.accion .lbl { color: __RED__; }

/* Chip de filtro activo */
.ecsa-chip {
  display: inline-block; font-size: 13px; color: __RED__; background: __REDSOFT__;
  border: 1px solid __RED__; border-radius: 999px; padding: 4px 12px;
}
.ecsa-caveat { font-size: 12.5px; color: __GRAY600__; }
</style>
"""


def _css():
    repl = {
        "__FONT__": theme.FONT_STACK, "__BG__": theme.BG, "__SURFACE__": theme.SURFACE,
        "__RED__": theme.BRAND_RED, "__REDSOFT__": theme.RED_SOFT,
        "__GRAY900__": theme.GRAY_900, "__GRAY600__": theme.GRAY_600,
        "__GRAY200__": theme.GRAY_200, "__GRAY100__": theme.GRAY_100,
    }
    css = _CSS
    for k, v in repl.items():
        css = css.replace(k, v)
    return css


def inject_global_css():
    """Inyecta el bloque <style> global una sola vez por sesión."""
    st.markdown(_css(), unsafe_allow_html=True)


# ── Componentes ────────────────────────────────────────────────────────────────
def header_bar():
    """Barra de marca E-commerce SA + chip de contexto de datos (orientación del neófito)."""
    st.markdown(
        '<div class="ecsa-header">'
        '  <div class="ecsa-brand">'
        '    <div class="ecsa-logo">E</div>'
        '    <div>'
        '      <div class="ecsa-brand-name">E-commerce SA</div>'
        '      <div class="ecsa-brand-sub">Inteligencia de conversión &amp; incentivos</div>'
        '    </div>'
        '  </div>'
        '  <div class="ecsa-datachip">Datos: Oct 2019 · muestra por usuario</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def section_header(titulo, subtitulo=""):
    sub = f'<div class="ecsa-sec-sub">{subtitulo}</div>' if subtitulo else ""
    st.markdown(f'<div class="ecsa-sec-title">{titulo}</div>{sub}', unsafe_allow_html=True)


def kpi_card(label, value, sub=None, accent=False):
    """HTML de una tarjeta KPI. accent=True la resalta en rojo (solo el KPI ancla)."""
    cls = "ecsa-kpi accent" if accent else "ecsa-kpi"
    subhtml = f'<div class="sub">{sub}</div>' if sub else ""
    return (f'<div class="{cls}"><div class="lbl">{label}</div>'
            f'<div class="val">{value}</div>{subhtml}</div>')


def callout(value, caption):
    """Número grande como héroe textual (cuando un solo número es la historia)."""
    st.markdown(
        f'<div class="ecsa-callout"><div class="big">{value}</div>'
        f'<div class="cap">{caption}</div></div>',
        unsafe_allow_html=True,
    )


def action_banner(texto):
    """Franja de acción recomendada (acto de habla 'motivar')."""
    st.markdown(
        f'<div class="ecsa-banner"><span class="tag">Acción</span>'
        f'<span class="txt">{texto}</span></div>',
        unsafe_allow_html=True,
    )


def insight_card(contexto, hallazgo, traduccion, accion):
    """CHTA como tarjeta estructurada con iconos (no como párrafo gris)."""
    rows = [
        ("🧭", "Contexto", contexto, ""),
        ("🔎", "Hallazgo", hallazgo, ""),
        ("💱", "Traducción", traduccion, ""),
        ("✅", "Acción", accion, "accion"),
    ]
    html = '<div class="ecsa-insight">'
    for ic, lbl, body, extra in rows:
        html += (f'<div class="row {extra}"><div class="ic">{ic}</div>'
                 f'<div class="lbl">{lbl}</div><div class="body">{body}</div></div>')
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def filter_chip(label, on_clear, key="clear"):
    """Renderiza un chip de filtro activo + botón 'Limpiar selección' (cross-filter)."""
    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown(f'<div class="ecsa-chip">🔗 {label}</div>', unsafe_allow_html=True)
    with c2:
        st.button("Limpiar selección", on_click=on_clear, key=key, width="stretch")


def caveat(texto):
    st.markdown(f'<div class="ecsa-caveat">{texto}</div>', unsafe_allow_html=True)


def glossary_expander():
    """Glosario para el usuario que no conoce el negocio (orientación del neófito)."""
    with st.expander("¿Qué significan estos términos?"):
        st.markdown(
            "- **Abandono por unidad** — de cada producto que llega al carrito, qué % no "
            "termina en compra (grano: producto dentro de una sesión).\n"
            "- **Conversión por unidad** — de cada producto visto, qué % se compra.\n"
            "- **Recurrente** — comprador con **2 o más** ocasiones de compra (sesiones "
            "distintas con compra); _one-time_ = una sola.\n"
            "- **Revenue en juego** — dinero de los carritos abandonados que podría "
            "recuperarse (suma del precio de esos productos).\n"
            "- **Nudge** — empujón de marketing oportuno y de bajo costo (recordatorio, "
            "urgencia, financiación) para mover al cliente al siguiente paso."
        )
