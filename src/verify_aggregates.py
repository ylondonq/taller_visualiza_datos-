"""
src/verify_aggregates.py — comprueba que las métricas derivadas de los AGREGADOS coinciden
EXACTAMENTE (sin filtros) con las de src/metrics.py sobre el clickstream completo, que a su
vez son las del notebook. Si algo no cuadra, lo imprime; no aproxima.

Ejecutar:  $env:PYTHONUTF8=1; .venv\\Scripts\\python.exe -m src.verify_aggregates
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src import prep, metrics, agg_metrics  # noqa: E402

TOL = 1e-6
results = []


def chk(name, a, b, tol=TOL):
    if a is None or b is None or (isinstance(a, float) and np.isnan(a)) or (isinstance(b, float) and np.isnan(b)):
        ok = (a is None and b is None) or (np.isnan(a) and np.isnan(b))
    else:
        ok = abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
    results.append((name, ok, a, b))


def chk_series(name, sa, sb, tol=1e-4):
    sa = sa.sort_index().astype(float)
    sb = sb.sort_index().astype(float)
    ok = sa.index.equals(sb.index) and np.allclose(sa.values, sb.values, atol=tol, rtol=tol, equal_nan=True)
    results.append((name, ok, "serie", "serie"))


def main():
    print("Cargando clickstream completo (verdad de tierra)…")
    df = prep.load_sample()

    u = agg_metrics.load_units()
    occ = agg_metrics.load_occasions()
    hourly = agg_metrics.load_hourly()
    price_cat = agg_metrics.load_price_cat()
    anchors = agg_metrics.load_anchors()

    # ── Funnel / abandono ──
    ab0, ab1 = metrics.abandonment(df), agg_metrics.abandonment(u)
    chk("funnel.conv_rate", ab1["gf"]["conv_rate"], ab0["gf"]["conv_rate"])
    chk("funnel.cart_rate", ab1["gf"]["cart_rate"], ab0["gf"]["cart_rate"])
    chk("funnel.n_units", ab1["gf"]["n_units"], ab0["gf"]["n_units"])
    chk("funnel.reached_cart", ab1["gf"]["reached_cart"], ab0["gf"]["reached_cart"])
    chk("funnel.reached_purchase", ab1["gf"]["reached_purchase"], ab0["gf"]["reached_purchase"])
    chk("abandono_global", ab1["abandono_global"], ab0["abandono_global"])
    chk_series("aband_cat.abandono", ab1["aband_cat"]["abandono"], ab0["aband_cat"]["abandono"])
    chk_series("aband_cat.abandonados", ab1["aband_cat"]["abandonados"], ab0["aband_cat"]["abandonados"])

    # ── Recurrencia ──
    r0, r1 = metrics.recurrence(df), agg_metrics.recurrence(occ)
    for k in ["one_time", "repeat", "n_buyers", "pct_repeat", "pct_rev_repeat",
              "ticket_one_time", "ticket_repeat", "rev_repeat", "rev_total"]:
        chk(f"recurrence.{k}", r1[k], r0[k])

    # ── Revenue en juego ──
    ras0, ras1 = metrics.revenue_at_stake(df), agg_metrics.revenue_at_stake(u)
    chk("ras.total_en_juego", ras1["total_en_juego"], ras0["total_en_juego"])
    chk("ras.n_carritos", ras1["n_carritos"], ras0["n_carritos"])
    chk_series("ras.prize.revenue", ras1["prize"]["revenue_en_juego"], ras0["prize"]["revenue_en_juego"])
    chk_series("ras.prize.carritos", ras1["prize"]["carritos"], ras0["prize"]["carritos"])

    # ── Timing de recompra ──
    rt0, rt1 = metrics.repurchase_timing(df), agg_metrics.repurchase_timing(occ)
    chk("timing.median_days", rt1["median_days"], rt0["median_days"])
    chk("timing.same_pct", rt1["same_pct"], rt0["same_pct"])
    chk("timing.n_recurrent", rt1["n_recurrent"], rt0["n_recurrent"])

    # ── Marca en electronics ──
    bm0, bm1 = metrics.brand_mix(df), agg_metrics.brand_mix(u)
    chk("brand.n_total", bm1["n_total"], bm0["n_total"])
    chk("brand.n_nulos", bm1["n_nulos"], bm0["n_nulos"])
    chk_series("brand.abandonados", bm1["g"]["abandonados"], bm0["g"]["abandonados"])
    chk_series("brand.comprados", bm1["g"]["comprados"], bm0["g"]["comprados"])

    # ── Velocidad de decisión ──
    ds0, ds1 = metrics.decision_speed(df), agg_metrics.decision_speed(u)
    chk("speed.median_min", ds1["median_min"], ds0["median_min"])
    chk("speed.pct_lt5", ds1["pct_lt5"], ds0["pct_lt5"])
    chk("speed.pct_lt10", ds1["pct_lt10"], ds0["pct_lt10"])
    chk("speed.n_units", ds1["n_units"], ds0["n_units"])
    chk("speed.n_neg", ds1["n_neg"], ds0["n_neg"])

    # ── Intensidad horaria ──
    hi0, hi1 = metrics.hourly_intensity(df), agg_metrics.hourly_intensity(hourly)
    chk_series("hourly.%_compras", hi1["%_compras"], hi0["%_compras"])
    chk_series("hourly.%_vistas", hi1["%_vistas"], hi0["%_vistas"])
    chk_series("hourly.compras_x100_vistas", hi1["compras_x100_vistas"], hi0["compras_x100_vistas"])

    # ── Precio vs conversión ──
    pc0 = metrics.price_vs_conversion(df)
    pc1 = agg_metrics.price_vs_conversion(u, price_cat)
    chk_series("price.conv_rate", pc1["conv_rate"], pc0["conv_rate"])
    chk_series("price.precio_mediana", pc1["precio_mediana"], pc0["precio_mediana"])

    # ── Anclas (titular) vs metrics directo ──
    chk("anchor.abandono_global", anchors["abandono_global"], ab0["abandono_global"])
    chk("anchor.conv_global", anchors["conv_global"], ab0["gf"]["conv_rate"])
    chk("anchor.rev_en_juego_foco", anchors["rev_en_juego_foco"], float(ras0["prize"].loc["electronics", "revenue_en_juego"]))
    chk("anchor.pct_repeat", anchors["pct_repeat"], r0["pct_repeat"])
    chk("anchor.median_min", anchors["median_min"], ds0["median_min"])
    chk("anchor.median_days", anchors["median_days"], rt0["median_days"])
    chk("anchor.same_pct", anchors["same_pct"], rt0["same_pct"])

    # ── Reporte ──
    n_ok = sum(1 for _, ok, *_ in results if ok)
    print(f"\n{'MÉTRICA':<32} {'AGG':>16} {'GROUND TRUTH':>16}  OK")
    print("-" * 86)
    for name, ok, a, b in results:
        av = f"{a:.6g}" if isinstance(a, (int, float)) else str(a)
        bv = f"{b:.6g}" if isinstance(b, (int, float)) else str(b)
        print(f"{name:<32} {av:>16} {bv:>16}  {'✓' if ok else '✗ FALLA'}")
    print("-" * 86)
    print(f"{n_ok}/{len(results)} verificaciones OK")
    if n_ok != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
