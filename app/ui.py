"""
app/ui.py — Sistema de componentes del dashboard E-commerce SA (ayudas NO-gráfico).

Iteración v2 "comunicar limpio": cada sección = una frase de mensaje + un héroe con
título-acción + a lo sumo un apoyo (o 2–3 chips de cifra) + un chip de acción. Se elimina
el bloque de 4 tarjetas CHTA (esa información va en el título-acción y la anotación del
héroe, igual que en la Fase II del notebook): es "tinta que no cuenta historia" (§3.1).

Componentes:
  header_bar()                      — barra de marca (con padding-top para no recortar el logo).
  section_header(titulo, sub)       — encabezado de sección con jerarquía.
  kpi_card(label, value, sub, accent) — tarjeta KPI; accent resalta en rojo (solo el ancla).
  message_line(texto)               — UNA frase de mensaje (reemplaza el bloque de 4 tarjetas).
  action_chip(texto, icon)          — pill con acento rojo: la acción recomendada en una línea.
  stat_chip(icono, valor, etiqueta) — número grande + icono + etiqueta (HTML para columnas).
  callout(value, caption)           — número grande como héroe textual.
  time_panel(...)                   — panel de reloj (cronómetro + mini-timeline + badge) para
                                      CUALQUIER métrica de tiempo (recompra, decisión, franja).
  glossary_expander()               — glosario para el neófito.
  about_data_expander()             — caveat metodológico, fuera del flujo visual.

Principios: Data-to-Ink (§3.1) + Gestalt/proximidad (§3.3) + §3.2 preatentivos (un solo
acento rojo) + §3.5 acto de habla "motivar".
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme  # noqa: E402


# ── CSS global (una sola inyección) ────────────────────────────────────────────
_CSS = """
<style>
html, body, [class*="css"], .stMarkdown, .stApp { font-family: __FONT__; }
.stApp { background: __BG__; }
/* padding-top generoso: la cabecera de Streamlit estaba recortando el logo de marca */
.block-container { padding-top: 2.6rem; padding-bottom: 3rem; max-width: 1280px; }

/* Quitar chrome de Streamlit que no aporta, sin comerse el tope del lienzo */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
header[data-testid="stHeader"] { background: transparent; height: 0; }

/* Navegación prominente: pestañas grandes con activo de alto contraste (§3.4) */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid __GRAY200__; }
.stTabs [data-baseweb="tab"] {
  height: auto; padding: 11px 18px; font-size: 15px; font-weight: 500;
  color: __GRAY600__; background: transparent; border-radius: 8px 8px 0 0;
}
.stTabs [data-baseweb="tab"]:hover { color: __GRAY900__; background: __GRAY100__; }
.stTabs [aria-selected="true"] {
  color: __RED__ !important; background: transparent; border-bottom: 3px solid __RED__;
}

/* Barra de marca */
.ecsa-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 4px 16px 4px; margin-bottom: 4px; border-bottom: 1px solid __GRAY200__;
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

/* Frase de mensaje (takeaway) */
.ecsa-msg { font-size: 17px; font-weight: 500; color: __GRAY900__; margin: 6px 0 12px 0; }

/* Tarjeta KPI (jerarquía: ancla resaltada) */
.ecsa-kpi { padding: 14px 16px; border: 1px solid __GRAY200__; border-radius: 12px; background: __SURFACE__; height: 100%; }
.ecsa-kpi.accent { border-color: __RED__; border-top: 3px solid __RED__; background: __REDSOFT__; }
.ecsa-kpi .lbl { font-size: 12.5px; color: __GRAY600__; text-transform: uppercase; letter-spacing: .03em; }
.ecsa-kpi .val { font-size: 26px; font-weight: 600; color: __GRAY900__; line-height: 1.25; margin-top: 2px; }
.ecsa-kpi.accent .val { color: __RED__; }
.ecsa-kpi .sub { font-size: 12.5px; color: __GRAY600__; margin-top: 2px; }

/* Callout de número grande */
.ecsa-callout { padding: 6px 2px 10px 2px; }
.ecsa-callout .big { font-size: 44px; font-weight: 600; color: __RED__; line-height: 1.05; }
.ecsa-callout .cap { font-size: 14px; color: __GRAY600__; margin-top: 2px; }

/* Chip de acción (pill, acto de habla "motivar") */
.ecsa-actionchip {
  display: inline-flex; align-items: center; gap: 8px; margin: 6px 0 2px 0;
  border: 1px solid __RED__; color: __RED__; background: __REDSOFT__;
  border-radius: 999px; padding: 9px 16px; font-size: 14.5px; font-weight: 500;
}

/* Chip de cifra (número grande + icono + etiqueta) */
.ecsa-stat {
  display: flex; align-items: center; gap: 12px; height: 100%;
  border: 1px solid __GRAY200__; border-radius: 12px; padding: 12px 16px; background: __SURFACE__;
}
.ecsa-stat .ic { font-size: 24px; flex: none; }
.ecsa-stat .big { font-size: 22px; font-weight: 600; color: __GRAY900__; line-height: 1.15; }
.ecsa-stat .lbl { font-size: 13px; color: __GRAY600__; }

/* Panel de reloj (todo lo temporal) */
.ecsa-time { border: 1px solid __GRAY200__; border-radius: 12px; padding: 16px 18px; background: __SURFACE__; }
.ecsa-time .head { display: flex; align-items: center; gap: 14px; }
.ecsa-time .ic { font-size: 30px; line-height: 1; }
.ecsa-time .val { font-size: 30px; font-weight: 600; color: __GRAY900__; line-height: 1.05; }
.ecsa-time .cap { font-size: 13px; color: __GRAY600__; }
.ecsa-time .track { position: relative; height: 6px; background: __GRAY100__; border-radius: 999px; margin: 26px 8px 30px 8px; }
.ecsa-time .fill { position: absolute; left: 0; top: 0; height: 6px; background: __RED__; border-radius: 999px; }
.ecsa-time .mk { position: absolute; top: -5px; width: 14px; height: 14px; border-radius: 50%; background: __RED__; border: 2px solid #fff; box-shadow: 0 0 0 1px __GRAY200__; transform: translateX(-50%); }
.ecsa-time .mklbl { position: absolute; top: 13px; font-size: 11.5px; color: __GRAY600__; transform: translateX(-50%); white-space: nowrap; }
.ecsa-time .badge { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: __RED__; background: __REDSOFT__; border: 1px solid __RED__; border-radius: 999px; padding: 4px 12px; }
.ecsa-time .sub { font-size: 13px; color: __GRAY600__; margin-top: 6px; }

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
    st.markdown(_css(), unsafe_allow_html=True)


# ── Componentes ────────────────────────────────────────────────────────────────
def header_bar():
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


def message_line(texto):
    """Una sola frase de mensaje (el takeaway). Reemplaza el bloque de 4 tarjetas."""
    st.markdown(f'<div class="ecsa-msg">{texto}</div>', unsafe_allow_html=True)


def kpi_card(label, value, sub=None, accent=False):
    cls = "ecsa-kpi accent" if accent else "ecsa-kpi"
    subhtml = f'<div class="sub">{sub}</div>' if sub else ""
    return (f'<div class="{cls}"><div class="lbl">{label}</div>'
            f'<div class="val">{value}</div>{subhtml}</div>')


def callout(value, caption):
    st.markdown(
        f'<div class="ecsa-callout"><div class="big">{value}</div>'
        f'<div class="cap">{caption}</div></div>',
        unsafe_allow_html=True,
    )


def action_chip(texto, icon="🔔"):
    """Pill con acento rojo: la acción recomendada en una sola línea (§3.5 'motivar')."""
    st.markdown(f'<div class="ecsa-actionchip">{icon}&nbsp;{texto}</div>', unsafe_allow_html=True)


def stat_chip(icono, valor, etiqueta):
    """HTML de un chip de cifra (número grande + icono + etiqueta) para colocar en columnas."""
    return (f'<div class="ecsa-stat"><div class="ic">{icono}</div>'
            f'<div><div class="big">{valor}</div><div class="lbl">{etiqueta}</div></div></div>')


def time_panel(value, caption, milestones=None, badge=None, sub=None, icon="⏱️"):
    """Panel de reloj para métricas de tiempo: cronómetro (número grande) + mini-timeline
    opcional (lista de (pct, etiqueta)) + badge opcional + sub-línea. Rojo solo como acento.

    milestones: lista de (pct_en_0_100, etiqueta). El relleno llega hasta el último hito.
    """
    html = ('<div class="ecsa-time">'
            f'<div class="head"><div class="ic">{icon}</div>'
            f'<div><div class="val">{value}</div><div class="cap">{caption}</div></div></div>')
    if milestones:
        maxpct = max(p for p, _ in milestones)
        html += f'<div class="track"><div class="fill" style="width:{maxpct:.1f}%"></div>'
        for pct, label in milestones:
            html += (f'<div class="mk" style="left:{pct:.1f}%"></div>'
                     f'<div class="mklbl" style="left:{pct:.1f}%">{label}</div>')
        html += "</div>"
    if badge:
        html += f'<div class="badge">🔁&nbsp;{badge}</div>'
    if sub:
        html += f'<div class="sub">{sub}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def caveat(texto):
    st.markdown(f'<div class="ecsa-caveat">{texto}</div>', unsafe_allow_html=True)


def glossary_expander():
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


def about_data_expander():
    """Honestidad metodológica fuera del flujo visual del tablero."""
    with st.expander("Acerca de los datos"):
        st.markdown(
            "Ventana = **solo octubre 2019**. Muestra **por usuario** (cluster sampling, "
            "semilla 42): se eligen usuarios al azar y se traen todos sus eventos, preservando "
            "sesiones e historial. Clickstream REES46 de e-commerce. Son señales sólidas para "
            "decidir, no verdades definitivas (un comprador 'one-time' podría volver en noviembre)."
        )
