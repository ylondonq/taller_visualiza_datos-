"""
src/build_aggregates.py — FASE III (refactor de memoria): precómputo de agregados.

PROBLEMA: el dashboard cargaba el clickstream entero (muestra_usuarios.parquet, ~980k
filas / ~238 MB en RAM) y derivaba TODAS las métricas al vuelo, además de copiar/ordenar
ese frame en cada llamada (revenue_at_stake hace df.copy(), decision_speed ordena las 980k
filas, y el app calcula métricas sobre el df completo Y sobre el filtrado). El pico de RAM
supera el ~1 GB del tier gratuito de Streamlit Community Cloud → la app se cae.

SOLUCIÓN: leer la muestra UNA sola vez (con la MISMA limpieza/features de src/prep.py y las
MISMAS fórmulas de src/funnel.py y src/metrics.py), colapsarla a unos pocos agregados
pequeños y guardarlos en data/processed/ como parquets con dtype 'category'. El dashboard
luego carga SOLO esos agregados (ver src/agg_metrics.py) y nunca toca el clickstream crudo.

Agregados producidos (grano mínimo para reproducir las cifras y sostener los filtros):
  agg_units.parquet      — 1 fila por UNIDAD (user_session × product_id): banderas de
                            funnel, category_main, brand, price (mediana del par), hora del
                            primer evento de la unidad, minutos de decisión y segmento del
                            usuario. Reproduce funnel/abandono/revenue/marca/velocidad/precio.
  agg_occasions.parquet  — 1 fila por OCASIÓN de compra (user_id × user_session): revenue,
                            ítems, categoría dominante, marca dominante, instante y hora,
                            segmento. Reproduce recurrencia/ticket/timing de recompra.
  agg_hourly.parquet     — conteo por (hour, event_type, category_main, segment). Reproduce
                            la intensidad horaria. NO incluye brand (2.572 marcas dispararían
                            el tamaño) → el filtro de marca no afecta a esta figura.
  agg_price_cat.parquet  — precio por categoría (sobre la mediana por producto único). FIJO:
                            el precio no depende de hora/segmento.
  agg_anchors.parquet    — cifras ancla del titular (FIJAS, sobre el df sin filtrar), tomadas
                            directamente de src/metrics.py (la verdad de tierra del notebook).

NO modifica config.py ni src/funnel.py. Las rutas de los agregados se derivan de
config.DATA_PROCESSED para no tocar la fuente única de rutas.

Ejecutar:  $env:PYTHONUTF8=1; .venv\\Scripts\\python.exe -m src.build_aggregates
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402
from src import prep, metrics  # noqa: E402
from src.funnel import UNIT  # ["user_session", "product_id"]  # noqa: E402

# Rutas de los agregados (derivadas de config, sin tocar config.py)
AGG_UNITS = config.DATA_PROCESSED / "agg_units.parquet"
AGG_OCCASIONS = config.DATA_PROCESSED / "agg_occasions.parquet"
AGG_HOURLY = config.DATA_PROCESSED / "agg_hourly.parquet"
AGG_PRICE_CAT = config.DATA_PROCESSED / "agg_price_cat.parquet"
AGG_ANCHORS = config.DATA_PROCESSED / "agg_anchors.parquet"

NO_CAT = "(sin categoria)"  # sentinela para eventos sin category_main en el agregado horario


def _user_segment(df):
    """Mapea cada user_id COMPRADOR a 'recurrent' (>=2 ocasiones) u 'onetime' (1 ocasión).

    Misma definición que metrics.recurrence (ocasión = sesión distinta con compra) y que el
    `recurrent_user_ids()` del app viejo. Los no-compradores quedan fuera del mapa (→ 'nonbuyer').
    """
    purch = df[df["event_type"] == "purchase"]
    occ_per_user = purch.groupby("user_id")["user_session"].nunique()
    return pd.Series(
        np.where(occ_per_user >= 2, "recurrent", "onetime"),
        index=occ_per_user.index,
    )


def build_units(df, user_segment):
    """Tabla a grano UNIDAD (user_session × product_id). Espeja src/funnel._unit_flags y los
    agregados de metrics.revenue_at_stake / brand_mix / decision_speed (price=mediana del par,
    category/brand constantes por producto)."""
    ev = df[[*UNIT, "event_type", "event_time", "price", "category_main", "brand", "user_id"]].copy()
    ev["is_view"] = ev["event_type"].eq("view")
    ev["is_cart"] = ev["event_type"].eq("cart")
    ev["is_purchase"] = ev["event_type"].eq("purchase")

    g = ev.groupby(UNIT, observed=True)
    units = g.agg(
        has_view=("is_view", "any"),
        has_cart=("is_cart", "any"),
        has_purchase=("is_purchase", "any"),
        price=("price", "median"),                 # = revenue_at_stake / brand_mix
        category_main=("category_main", "first"),  # constante por product_id
        brand=("brand", "first"),                  # constante por product_id
        first_event=("event_time", "min"),
        user_id=("user_id", "first"),
    )

    # decision_min = minutos del 1er VIEW del producto a su 1ra COMPRA (= metrics.decision_speed).
    # Solo definido cuando la unidad tiene view Y purchase; NaN en otro caso (= dropna del orig).
    first_view = ev[ev["is_view"]].groupby(UNIT, observed=True)["event_time"].min()
    purchase_time = ev[ev["is_purchase"]].groupby(UNIT, observed=True)["event_time"].min()
    units["decision_min"] = (purchase_time - first_view).dt.total_seconds() / 60

    units["unit_hour"] = units.pop("first_event").dt.hour.astype("int8")
    units["segment"] = units.pop("user_id").map(user_segment).fillna("nonbuyer")

    units = units.reset_index(drop=True)  # ni session ni product hacen falta tras colapsar
    for c in ["category_main", "brand", "segment"]:
        units[c] = units[c].astype("category")
    units["price"] = units["price"].astype("float32")
    units["decision_min"] = units["decision_min"].astype("float32")
    return units


def _mode_or_na(s):
    """Moda ignorando nulos (= lambda usada en metrics.repurchase_timing)."""
    s = s.dropna()
    return s.mode().iloc[0] if s.size else pd.NA


def build_occasions(df, user_segment):
    """Tabla a grano OCASIÓN de compra (user_id × user_session). Espeja el `occ` interno de
    metrics.recurrence y metrics.repurchase_timing (t = min del evento de compra; categoría/
    marca = moda entre los eventos purchase de la sesión)."""
    purch = df[df["event_type"] == "purchase"]
    occ = purch.groupby(["user_id", "user_session"], observed=True).agg(
        revenue=("price", "sum"),
        items=("event_type", "size"),
        t=("event_time", "min"),
        category=("category_main", _mode_or_na),
        brand=("brand", _mode_or_na),
    ).reset_index()

    occ["hour"] = occ["t"].dt.hour.astype("int8")
    occ["segment"] = occ["user_id"].map(user_segment)
    occ["revenue"] = occ["revenue"].astype("float32")
    occ["items"] = occ["items"].astype("int16")
    for c in ["category", "brand", "segment"]:
        occ[c] = occ[c].astype("category")
    return occ


def build_hourly(df, user_segment):
    """Conteo por (hour, event_type, category_main, segment). Reproduce metrics.hourly_intensity
    (que agrupa por hour×event_type) tras sumar sobre category/segment. Nulos de category_main
    se guardan como sentinela para no perderlos al filtrar por categoría."""
    h = df[["hour", "event_type", "category_main", "user_id"]].copy()
    h["segment"] = h["user_id"].map(user_segment).fillna("nonbuyer")
    h["category_main"] = h["category_main"].fillna(NO_CAT)
    hourly = (
        h.groupby(["hour", "event_type", "category_main", "segment"], observed=True)
        .size()
        .reset_index(name="n")
    )
    hourly["hour"] = hourly["hour"].astype("int8")
    hourly["n"] = hourly["n"].astype("int32")
    for c in ["event_type", "category_main", "segment"]:
        hourly[c] = hourly[c].astype("category")
    return hourly


def build_price_cat(df):
    """Precio por categoría sobre la MEDIANA por producto único (= metrics.price_vs_conversion).
    Es FIJO: el precio de un producto no es función de la hora/segmento."""
    prod_precio = (
        df[df["category_main"].notna()]
        .groupby(["category_main", "product_id"])["price"]
        .median()
    )
    price_cat = (
        prod_precio.groupby("category_main")
        .agg(precio_promedio="mean", precio_mediana="median", n_productos="count")
        .round(2)
        .reset_index()
    )
    price_cat["category_main"] = price_cat["category_main"].astype("category")
    return price_cat


def build_anchors(df):
    """Cifras ancla del titular (FIJAS), tomadas de src/metrics.py sobre el df SIN filtrar:
    son exactamente las del notebook (verdad de tierra)."""
    ab = metrics.abandonment(df)
    rec = metrics.recurrence(df)
    ras = metrics.revenue_at_stake(df)
    ds = metrics.decision_speed(df)
    rt = metrics.repurchase_timing(df)
    foco = "electronics"
    return pd.DataFrame([{
        "abandono_global": ab["abandono_global"],
        "conv_global": ab["gf"]["conv_rate"],
        "rev_en_juego_foco": float(ras["prize"].loc[foco, "revenue_en_juego"]) if foco in ras["prize"].index else 0.0,
        "rev_en_juego_total": ras["total_en_juego"],
        "pct_repeat": rec["pct_repeat"],
        "pct_rev_repeat": rec["pct_rev_repeat"],
        "ticket_one_time": rec["ticket_one_time"],
        "ticket_repeat": rec["ticket_repeat"],
        "median_min": ds["median_min"],
        "median_days": rt["median_days"],
        "same_pct": rt["same_pct"],
    }])


def main():
    print("Cargando muestra (una sola vez) con prep.load_sample()…")
    df = prep.load_sample()
    print(f"  eventos: {len(df):,} · RAM df: {df.memory_usage(deep=True).sum()/1e6:.1f} MB")

    user_segment = _user_segment(df)

    units = build_units(df, user_segment)
    occ = build_occasions(df, user_segment)
    hourly = build_hourly(df, user_segment)
    price_cat = build_price_cat(df)
    anchors = build_anchors(df)

    outputs = {
        AGG_UNITS: units,
        AGG_OCCASIONS: occ,
        AGG_HOURLY: hourly,
        AGG_PRICE_CAT: price_cat,
        AGG_ANCHORS: anchors,
    }
    print("\nGuardando agregados:")
    total_disk = 0
    for path, tab in outputs.items():
        tab.to_parquet(path, index=False)
        disk = path.stat().st_size
        total_disk += disk
        ram = tab.memory_usage(deep=True).sum()
        print(f"  {path.name:<24} {len(tab):>8,} filas · disco {disk/1e6:6.2f} MB · RAM {ram/1e6:6.2f} MB")
    print(f"\nTotal en disco: {total_disk/1e6:.2f} MB (vs muestra_usuarios.parquet 28 MB)")
    print("Listo. El dashboard ahora carga estos agregados, no el clickstream crudo.")


if __name__ == "__main__":
    main()
