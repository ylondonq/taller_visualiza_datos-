"""
src/agg_metrics.py — FASE III (refactor de memoria): métricas sobre AGREGADOS precomputados.

Reimplementa las funciones de src/metrics.py pero leyendo de los parquets pequeños que crea
src/build_aggregates.py (no del clickstream crudo). Cada función DEVUELVE LA MISMA ESTRUCTURA
(dict / DataFrame con las mismas claves, columnas e índices) que su gemela en metrics.py, de
modo que app/charts.py NO cambia. Las fórmulas son las mismas: aquí solo cambia la FUENTE
(tabla ya colapsada a unidad/ocasión/hora) y se elimina el copiado del frame de 980k filas.

Mapa agregado → métricas que reproduce:
  agg_units      → global_funnel, category_funnel, abandonment, revenue_at_stake,
                   brand_mix, decision_speed, (conv de) price_vs_conversion
  agg_occasions  → recurrence, repurchase_timing
  agg_hourly     → hourly_intensity
  agg_price_cat  → (precio de) price_vs_conversion
  agg_anchors    → cifras ancla fijas del titular

No importa streamlit (el caché se aplica en app/app.py, igual que prep.py).
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

AGG_UNITS = config.DATA_PROCESSED / "agg_units.parquet"
AGG_OCCASIONS = config.DATA_PROCESSED / "agg_occasions.parquet"
AGG_HOURLY = config.DATA_PROCESSED / "agg_hourly.parquet"
AGG_PRICE_CAT = config.DATA_PROCESSED / "agg_price_cat.parquet"
AGG_REVENUE_CAT = config.DATA_PROCESSED / "agg_revenue_cat.parquet"
AGG_ANCHORS = config.DATA_PROCESSED / "agg_anchors.parquet"


# ── Cargadores (el caché se aplica en app.py) ─────────────────────────────────
def load_units():
    return pd.read_parquet(AGG_UNITS)


def load_occasions():
    return pd.read_parquet(AGG_OCCASIONS)


def load_hourly():
    return pd.read_parquet(AGG_HOURLY)


def load_price_cat():
    return pd.read_parquet(AGG_PRICE_CAT)


def load_revenue_cat():
    return pd.read_parquet(AGG_REVENUE_CAT)


def load_anchors():
    return pd.read_parquet(AGG_ANCHORS).iloc[0].to_dict()


# ── Funnel (= src/funnel.global_funnel / category_funnel, pero desde unidades) ─
def global_funnel(u):
    n = len(u)
    reached_cart = int((u["has_cart"] | u["has_purchase"]).sum())
    reached_purchase = int(u["has_purchase"].sum())
    cart_only = int((u["has_cart"] & ~u["has_purchase"]).sum())
    view_only = int((u["has_view"] & ~u["has_cart"] & ~u["has_purchase"]).sum())
    return {
        "n_units": n,
        "reached_view": int(u["has_view"].sum()),
        "reached_cart": reached_cart,
        "reached_purchase": reached_purchase,
        "view_only": view_only,
        "cart_only": cart_only,
        "purchased": reached_purchase,
        "cart_rate": reached_cart / n * 100 if n else float("nan"),
        "conv_rate": reached_purchase / n * 100 if n else float("nan"),
        "cart_to_purchase": (reached_purchase / reached_cart * 100) if reached_cart else float("nan"),
    }


def category_funnel(u, min_units=500):
    d = u[u["category_main"].notna()].copy()
    d["reached_cart"] = d["has_cart"] | d["has_purchase"]
    out = d.groupby("category_main", observed=True).agg(
        units=("has_purchase", "size"),
        reached_cart=("reached_cart", "sum"),
        purchased=("has_purchase", "sum"),
    )
    out["cart_rate"] = out["reached_cart"] / out["units"] * 100
    out["conv_rate"] = out["purchased"] / out["units"] * 100
    out["cart_to_purchase"] = out["purchased"] / out["reached_cart"] * 100
    return out[out["units"] >= min_units].sort_values("conv_rate", ascending=False)


# ── 4.5 Abandono (= metrics.abandonment) ──────────────────────────────────────
def abandonment(u, min_units=500):
    gf = global_funnel(u)
    cat_funnel = category_funnel(u, min_units=min_units)
    abandono_global = 100 - gf["cart_to_purchase"]
    aband_cat = cat_funnel.assign(
        abandonados=(cat_funnel["reached_cart"] - cat_funnel["purchased"]),
        abandono=100 - cat_funnel["cart_to_purchase"],
    ).sort_values("abandono", ascending=False)
    return {"gf": gf, "cat_funnel": cat_funnel, "abandono_global": abandono_global, "aband_cat": aband_cat}


# ── 4.8a Revenue en juego (= metrics.revenue_at_stake) ────────────────────────
def revenue_at_stake(u, recovery_rates=(0.05, 0.10, 0.20)):
    aband = u[u["has_cart"] & ~u["has_purchase"]]
    prize = (
        aband.groupby("category_main", observed=True)["price"]
        .agg(carritos="size", revenue_en_juego="sum")
    )
    prize["ticket_medio"] = prize["revenue_en_juego"] / prize["carritos"]
    prize = prize.sort_values("revenue_en_juego", ascending=False)

    top_cat = prize.index[0] if len(prize) else None
    scenarios = (
        {r: float(prize.loc[top_cat, "revenue_en_juego"] * r) for r in recovery_rates}
        if top_cat is not None else {}
    )
    return {
        "aband": aband,
        "prize": prize,
        "total_en_juego": float(aband["price"].sum()),
        "n_carritos": int(len(aband)),
        "top_cat": top_cat,
        "scenarios": scenarios,
    }


# ── 4.8c Marca dentro de electronics (= metrics.brand_mix) ────────────────────
def brand_mix(u, foco="electronics", min_carritos=100):
    evf = u[u["category_main"] == foco]
    carted = evf[evf["has_cart"] | evf["has_purchase"]]
    n_total = int(len(carted))
    n_nulos = int(carted["brand"].isna().sum())
    g = (
        carted.dropna(subset=["brand"])
        .groupby("brand", observed=True)
        .agg(carritos=("has_purchase", "size"), comprados=("has_purchase", "sum"), ticket=("price", "median"))
    )
    g["abandonados"] = g["carritos"] - g["comprados"]
    g["abandono_%"] = (g["abandonados"] / g["carritos"] * 100).round(1)
    g = g[g["carritos"] >= min_carritos].sort_values("abandonados", ascending=False)
    return {"g": g, "n_total": n_total, "n_nulos": n_nulos, "foco": foco}


# ── 4.7 Velocidad de decisión (= metrics.decision_speed) ──────────────────────
def decision_speed(u):
    dt = u["decision_min"].dropna()          # unidades con view Y purchase (= dropna del orig)
    n_units = int(len(dt))
    n_neg = int((dt < 0).sum())
    dt = dt[dt >= 0].astype(float)
    has = len(dt) > 0
    return {
        "decision_time": dt,
        "n_neg": n_neg,
        "n_units": n_units,
        "median_min": float(dt.median()) if has else float("nan"),
        "pct_lt5": float((dt < 5).mean() * 100) if has else float("nan"),
        "pct_lt10": float((dt < 10).mean() * 100) if has else float("nan"),
        "pct_lt30": float((dt < 30).mean() * 100) if has else float("nan"),
    }


# ── 4.6 Recurrencia (= metrics.recurrence, desde ocasiones) ───────────────────
def recurrence(occ):
    user_buys = occ.groupby("user_id", observed=True).agg(
        ocasiones=("user_session", "nunique"),
        items=("items", "sum"),
        revenue=("revenue", "sum"),
    )
    one_time = int((user_buys["ocasiones"] == 1).sum())
    repeat = int((user_buys["ocasiones"] >= 2).sum())
    n_buyers = one_time + repeat
    rev_one_time = float(user_buys.loc[user_buys["ocasiones"] == 1, "revenue"].sum())
    rev_repeat = float(user_buys.loc[user_buys["ocasiones"] >= 2, "revenue"].sum())
    rev_total = float(user_buys["revenue"].sum())
    return {
        "user_buys": user_buys,
        "one_time": one_time,
        "repeat": repeat,
        "n_buyers": n_buyers,
        "rev_one_time": rev_one_time,
        "rev_repeat": rev_repeat,
        "rev_total": rev_total,
        "pct_repeat": repeat / n_buyers * 100 if n_buyers else float("nan"),
        "pct_rev_repeat": rev_repeat / rev_total * 100 if rev_total else float("nan"),
        "ticket_one_time": rev_one_time / one_time if one_time else float("nan"),
        "ticket_repeat": rev_repeat / repeat if repeat else float("nan"),
    }


# ── 4.8b Timing de recompra (= metrics.repurchase_timing, desde ocasiones) ────
def repurchase_timing(occ):
    o = occ.sort_values(["user_id", "t"]).copy()
    o["rank"] = o.groupby("user_id", observed=True).cumcount() + 1
    first = o[o["rank"] == 1].set_index("user_id")[["t", "category"]]
    second = o[o["rank"] == 2].set_index("user_id")[["t", "category"]]
    pair = first.join(second, lsuffix="_1", rsuffix="_2", how="inner")
    days = (pair["t_2"] - pair["t_1"]).dt.total_seconds() / 86400

    cat_pair = pair.dropna(subset=["category_1", "category_2"])
    same = (
        float((cat_pair["category_1"].astype(object) == cat_pair["category_2"].astype(object)).mean() * 100)
        if len(cat_pair) else float("nan")
    )
    return {
        "pair": pair,
        "days": days,
        "same_pct": same,
        "median_days": float(days.median()) if len(days) else float("nan"),
        "n_recurrent": int(len(pair)),
        "n_cat_pairs": int(len(cat_pair)),
    }


# ── 4.3 Intensidad horaria (= metrics.hourly_intensity, desde el conteo horario) ─
def hourly_intensity(h):
    hora_tab = (
        h.groupby(["hour", "event_type"], observed=True)["n"].sum()
        .unstack(fill_value=0)
        .reindex(columns=["view", "cart", "purchase"], fill_value=0)
    )
    hora_tab.columns = ["views", "carts", "purchases"]
    hora_tab = hora_tab.sort_index()
    hora_tab["%_vistas"] = (hora_tab["views"] / hora_tab["views"].sum() * 100).round(2)
    hora_tab["%_carritos"] = (hora_tab["carts"] / hora_tab["carts"].sum() * 100).round(2)
    hora_tab["%_compras"] = (hora_tab["purchases"] / hora_tab["purchases"].sum() * 100).round(2)
    hora_tab["compras_x100_vistas"] = (hora_tab["purchases"] / hora_tab["views"] * 100).round(2)
    return hora_tab


# ── 4.2 Precio vs conversión (= metrics.price_vs_conversion) ──────────────────
def price_vs_conversion(u, price_cat, min_units=500):
    cat_funnel = category_funnel(u, min_units=min_units)
    pc = price_cat.set_index("category_main")
    precio_conv = (
        cat_funnel[["units", "purchased", "cart_rate", "conv_rate"]]
        .join(pc[["precio_promedio", "precio_mediana"]], how="inner")
        .sort_values("conv_rate", ascending=False)
    )
    return precio_conv
