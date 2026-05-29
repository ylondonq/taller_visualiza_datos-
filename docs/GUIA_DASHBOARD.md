# Guía del dashboard — E-commerce SA (Taller 2)

> Qué hay en cada sección del tablero (`app/app.py`), para qué sirve y de dónde salen las
> cifras. App en vivo: https://taller02dataviz.streamlit.app/ · Entrada: `app/app.py`.
> Las cifras son idénticas al notebook del EDA (verificado en `src/verify_aggregates.py`, 48/48).

## Mensaje central
**El negocio deja dinero sobre la mesa en electrónica**, capturable con dos jugadas en la
misma categoría: **recuperar** carritos abandonados (antes de comprar) y **retener** al núcleo
recurrente (después). Narrativa de las pestañas: **Resumen (dónde) → Estrategia 1 (conversión)
→ Estrategia 2 (retención) → Cuándo activar (cuándo/con qué) → Plan de acción (cierre con $).**

## Semántica de color (clave de lectura)
- 🟢 **Verde** = ganancia **real / positiva** (ingresos de hoy, mejor conversión).
- 🔴 **Rojo** = dinero en **riesgo / perdido / a actuar** (revenue en juego, abandono, franja a activar).
- ⚪ **Gris** = contexto ("el resto"). El color solo aparece donde hay que mirar.

## Elementos comunes (en todas las vistas)
- **Barra de marca (arriba):** logo "E", "E-commerce SA · Inteligencia de conversión & incentivos"
  y chip "Datos: Oct 2019 · muestra por usuario".
- **Sidebar — Filtros (controles globales):** `Categoría` (multiselect), `Hora del día` (slider
  0–23), y en *Filtros avanzados*: `Marca` (top 30) y `Segmento` (Todos / Recurrentes / One-time).
  Abajo, expander **"Acerca de los datos"** con la nota metodológica (ventana = solo octubre 2019,
  muestra por usuario, semilla 42).
- **Fila de KPIs (en Resumen):** 5 indicadores reactivos a los filtros, con tono semántico —
  **Revenue en juego** `$2,54 M USD` 🔴 (riesgo) · **Abandono de carrito** `32,4%` · **Conversión
  por unidad** `2,44%` · **Recurrentes** `31,7% (= 69% del revenue)` 🟢 (valor) · **Decisión
  (mediana)** `2,2 min`.

---

## 1. Resumen  (pestaña estratégica — test de 30 s, sin interacción)
Responde **dos preguntas** en orden, con la misma categoría como respuesta a ambas:
- **Título:** *"¿Dónde ganamos hoy y dónde podríamos ganar más?"*
- **Gráfico 1 — ¿Dónde se gana hoy?** Barras horizontales de **ingresos reales por categoría**
  (`% del revenue`). **Electronics en verde 🟢 = 78%** de los ingresos (appliances 5,5%, computers
  4,3%; top-3 ≈ 88%). Fuente: `agg_revenue_cat`.
- **Gráfico 2 — ¿Dónde hay por recuperar?** Barras horizontales del **revenue en juego** (carritos
  abandonados) por categoría. **Electronics en rojo 🔴 = 82%** del premio (`$2,08 M`). Fuente:
  `agg_units` (unidades con carrito y sin compra).
- **Síntesis:** *"Es donde más se gana hoy **y** donde más hay por recuperar"* → la misma categoría
  sostiene el negocio y guarda la mayor oportunidad.
- **Glosario** (expander): abandono/conversión por unidad, recurrente, revenue en juego, nudge.

## 2. Estrategia 1 · Conversión  (PN1 — recuperar antes de comprar)
- **Mensaje:** *"¿En qué productos de electrónica y a qué hora vale aumentar la conversión?"*
- **Héroe (izquierda):** **embudo por unidad** Vista → Carrito → Compra
  (`642.169 → 23.174 → 15.663`, con %), con la caída carrito→compra (**abandono 32,4%**) resaltada
  en rojo y la nota *"de los 23.174 que llegan al carrito, ~5.048 son de electronics"*.
- **Apoyo (derecha) — 3 stat-chips:** 🛒 `70%` de los carritos = Apple + Samsung · 🏷️ `$732`
  mayor ticket (Apple) · ⏱️ `7h` pico de compra de electronics (franja 6–10 h).
- **Chip de acción:** recordatorio de carrito a Apple y Samsung con cierre inmediato
  (urgencia/stock, financiación), en la franja matutina (pico 7h).
- **Detalle (expander "Ver detalle analítico"):** abandono % por categoría + marcas (abandonados
  vs comprados).

## 3. Estrategia 2 · Retención  (PN2 — retener después de comprar)
- **Mensaje:** *"El 31,7% de los compradores trae el 69,0% del revenue."*
- **Héroe (izquierda):** dos barras 100% apiladas (**Compradores 31,7% / Revenue 69%**),
  recurrentes en rojo, one-time en gris, con conector "el mismo grupo".
  Título-acción: *"Fideliza al tercio que ya vuelve: genera 2 de cada 3 dólares."*
- **Apoyo (derecha) — reloj de recompra:** ⏱️ **"¿cuándo vuelve?"** mediana **1,8 días**, con
  mini-línea de tiempo (42% al día siguiente · 75% en la 1ª semana · 91% ≤14 d) y la **ventana
  24–72 h resaltada** (el momento del nudge); + número grande 🔁 **"85,5%"** *"¿a qué vuelve? — la
  misma categoría"*.
- **Chip de acción:** nudge de recompra a 24–72 h, en la misma categoría.
- **Detalle (expander):** ticket promedio (recurrente ~5× el one-time) + histograma de días a la 2ª compra.

## 4. Cuándo activar  (PN3 — cuándo y con qué)
- **Mensaje:** *"La mañana convierte ~2× por visita: concentra el incentivo en la franja 6–10 h."*
- **Héroe (izquierda):** **intensidad horaria** (compras por 100 vistas) con la **franja 6–10 h
  resaltada como banda roja** (pico 7h dentro). Un solo visual horario (sin distribución duplicada).
- **Apoyo (derecha):**
  - **"El precio no es el freno"** (tarjeta): **Electronics $152 → 3,92%** 🟢 (la mejor conversión)
    vs la categoría más barata → peor conversión. Mensaje: *las categorías más baratas convierten
    peor, no mejor.*
  - **Reloj de decisión:** ⏱️ **2,2 min** (mediana del 1er view a la compra), *"77,8% decide en <5 min".*
- **Chip de acción:** activa en la franja 6–10 h con incentivo inmediato/en pantalla; el precio no
  es el freno.
- **Detalle (expander):** histograma de velocidad de decisión + scatter precio vs conversión
  (electronics en verde 🟢 y bola más grande).

## 5. Plan de acción  (cierre que motiva — el "qué hacer" en $)
Lectura de color: el **problema en rojo** arriba → las **ganancias en verde** abajo.
- **Titular:** *"Hay **$2,53 M USD** sobre la mesa — y casi todo está en electrónica."*
  ($ en 🔴 rojo: dinero en riesgo).
- **Dos tarjetas de acción (USD), con el monto en 🟢 verde (ganancia al actuar):**
  - **Estrategia 1 · Recuperar** — carritos de Apple y Samsung, cierre inmediato en la mañana →
    **+$207.700 / mes** (recuperando el 10% de lo abandonado en electronics).
  - **Estrategia 2 · Retener** — nudge de recompra 24–72 h, misma categoría → **+$306.850**
    (moviendo el 5% de los compradores de una vez al núcleo recurrente).
- **Hipótesis a validar (cierre, marco del curso):** *si concentramos el incentivo donde ya
  hay señal (carritos de electrónica = intención; recurrentes = lealtad) en su momento de mayor
  propensión (mañana 6–10 h; recompra 24–72 h), entonces subiremos conversión y recompra sin
  erosionar margen, porque el incentivo va a quien casi compra o ya vuelve, no a quien compraría
  igual.* **Validación:** A/B test (tratado vs. control) midiendo el **uplift** incremental, no la
  conversión total. (Conecta el tablero con el proyecto integrador: propensión + uplift.)
- Layout: headline + dos tarjetas + hipótesis (cierre limpio, test de 30 s).

---

## De dónde salen las cifras (arquitectura de datos)
El dashboard **no carga el clickstream crudo**: consume 5 parquets pequeños (~3,9 MB) que
precomputa `src/build_aggregates.py` desde la muestra por usuario, con las **mismas fórmulas del
notebook**:
- `agg_units` — 1 fila por unidad (sesión × producto): banderas de funnel, categoría, marca,
  precio, hora, minutos de decisión, segmento. → funnel, abandono, revenue en juego, marca,
  velocidad, precio-vs-conversión.
- `agg_occasions` — 1 fila por ocasión de compra: revenue, ítems, categoría/marca dominante,
  instante, segmento. → recurrencia, ticket, timing de recompra.
- `agg_hourly` — conteo por hora × tipo × categoría × segmento. → intensidad horaria.
- `agg_price_cat` — precio por categoría (producto único). → precio vs conversión.
- `agg_revenue_cat` — revenue real por categoría. → "dónde se gana hoy" (78%).
- `agg_anchors` — cifras fijas del titular.

Las métricas (`src/agg_metrics.py`) reproducen el notebook; `src/verify_aggregates.py` compara
**48/48** contra el cálculo directo sobre la muestra completa. Pico de RAM del app ~220 MB.
**Caveats** (en "Acerca de los datos"): ventana = solo octubre 2019; el filtro de hora en
métricas de unidad corta por la hora del primer evento de la unidad; el filtro de marca no afecta
la intensidad horaria; recurrencia/timing se filtran por la categoría/marca dominante de la ocasión.
