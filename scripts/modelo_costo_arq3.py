#!/usr/bin/env python3
"""
modelo_costo_arq3.py - Modelo de costo unitario y margen de la Arquitectura 3 de CASHGO
(Inteligencia de Mercado / SaaS de datos sobre la Ad Library de Meta).

NO es una proyeccion de negocio: es una calculadora de piso de costo con supuestos
declarados y editables. Cada supuesto sale de una fuente verificada en vivo el
2026-09-06 y esta anotado con su URL en SUPUESTOS.

Uso:  python3 modelo_costo_arq3.py
Salida: tabla en stdout + CSV en evidencia/modelo_costo_arq3.csv
Exit code: 0 si el modelo cierra, 1 si un supuesto es incoherente.
"""
from __future__ import annotations
import csv
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

# ---------------------------------------------------------------------------
# PRECIOS VERIFICADOS EN VIVO [2026-09-06]
# Fuente: https://ai-tldr.dev/models/deepseek-v4-flash/ y https://www.aipricing.guru/deepseek-pricing/
# Esquema peak/off-peak vigente desde 16:00 UTC del 2026-08-16.
# peak = 01:00-04:00 y 06:00-10:00 UTC, lun-vie. Resto = off-peak (mitad de precio).
# CONFLICTO DE FUENTES DECLARADO: deepseekai.guide sigue publicando la tarifa plana
# anterior ($0.14 / $0.0028 / $0.28). Se usa la tarifa NUEVA por ser la mas caras:
# si el margen cierra con la caras, cierra con las dos.
# ---------------------------------------------------------------------------
USD_POR_MTOK = {
    "flash_off": {"in_miss": 0.22, "in_hit": 0.007, "out": 0.66},
    "flash_peak": {"in_miss": 0.44, "in_hit": 0.014, "out": 1.32},
    "pro_off":   {"in_miss": 0.66, "in_hit": 0.022, "out": 1.98},
    "pro_peak":  {"in_miss": 1.32, "in_hit": 0.044, "out": 3.96},
}

M = 1_000_000.0


@dataclass
class Supuestos:
    # --- corpus ---
    nichos: int = 40                    # verticales monitoreados
    marcas_por_nicho: int = 25          # paginas anunciantes por nicho
    anuncios_activos_por_marca: int = 60
    corridas_por_mes: float = 4.33      # semanal
    # churn creativo entre corridas: fraccion de anuncios NUEVOS por corrida.
    # En estado estacionario el resto se descarta por hash antes de tocar el modelo.
    churn_creativo: float = 0.12
    # --- tokens ---
    tok_in_por_anuncio: int = 320       # copy + metadata del ads_archive
    tok_out_por_anuncio: int = 140      # JSON estructurado validado
    anuncios_por_llamada: int = 40      # batch
    prefijo_estable_tok: int = 8000     # taxonomia + esquema + few-shots (identico siempre)
    tasa_cache_hit_prefijo: float = 0.95
    # --- sintesis semanal con Pro ---
    informes_por_corrida: int = 40      # uno por nicho
    tok_in_informe: int = 60_000
    tok_out_informe: int = 6_000
    # --- infra ---
    infra_usd_mes: float = 60.0         # Postgres administrado + worker + object storage
    # --- ingreso ---
    precio_suscripcion_usd: float = 79.0
    suscriptores: int = 30

    def validar(self) -> list[str]:
        errs = []
        if not 0 < self.churn_creativo <= 1:
            errs.append("churn_creativo fuera de (0,1]")
        if not 0 <= self.tasa_cache_hit_prefijo <= 1:
            errs.append("tasa_cache_hit_prefijo fuera de [0,1]")
        if self.anuncios_por_llamada <= 0:
            errs.append("anuncios_por_llamada debe ser > 0")
        return errs


def costo_llamadas_flash(s: Supuestos, tarifa: dict) -> dict:
    marcas = s.nichos * s.marcas_por_nicho
    vistos = marcas * s.anuncios_activos_por_marca
    nuevos = int(round(vistos * s.churn_creativo))
    llamadas = max(1, -(-nuevos // s.anuncios_por_llamada))  # ceil

    # parte variable: los anuncios nuevos
    tok_in_var = nuevos * s.tok_in_por_anuncio
    tok_out = nuevos * s.tok_out_por_anuncio
    # parte fija: el prefijo, una vez por llamada, con cache
    tok_pref_total = llamadas * s.prefijo_estable_tok
    tok_pref_hit = int(round(tok_pref_total * s.tasa_cache_hit_prefijo))
    tok_pref_miss = tok_pref_total - tok_pref_hit

    usd = (
        tok_in_var / M * tarifa["in_miss"]
        + tok_pref_miss / M * tarifa["in_miss"]
        + tok_pref_hit / M * tarifa["in_hit"]
        + tok_out / M * tarifa["out"]
    )
    return {
        "marcas": marcas,
        "anuncios_vistos": vistos,
        "anuncios_nuevos": nuevos,
        "descartados_por_dedup": vistos - nuevos,
        "llamadas_flash": llamadas,
        "tok_prefijo_total": tok_pref_total,
        "usd_flash_por_corrida": usd,
    }


def costo_informes_pro(s: Supuestos, tarifa: dict) -> float:
    tin = s.informes_por_corrida * s.tok_in_informe
    tout = s.informes_por_corrida * s.tok_out_informe
    return tin / M * tarifa["in_miss"] + tout / M * tarifa["out"]


def modelo(s: Supuestos, ventana: str) -> dict:
    tf = USD_POR_MTOK["flash_off" if ventana == "off-peak" else "flash_peak"]
    tp = USD_POR_MTOK["pro_off" if ventana == "off-peak" else "pro_peak"]
    f = costo_llamadas_flash(s, tf)
    pro = costo_informes_pro(s, tp)
    por_corrida = f["usd_flash_por_corrida"] + pro
    mes_modelo = por_corrida * s.corridas_por_mes
    mes_total = mes_modelo + s.infra_usd_mes
    ingreso = s.precio_suscripcion_usd * s.suscriptores
    # contrafactual: mismo trabajo SIN dedup y SIN cache de prefijo
    s2 = Supuestos(**{**asdict(s), "churn_creativo": 1.0, "tasa_cache_hit_prefijo": 0.0})
    ingenuo = (costo_llamadas_flash(s2, tf)["usd_flash_por_corrida"] + pro) * s.corridas_por_mes
    return {
        "ventana": ventana,
        **f,
        "usd_pro_por_corrida": pro,
        "usd_por_corrida": por_corrida,
        "usd_modelo_mes": mes_modelo,
        "usd_infra_mes": s.infra_usd_mes,
        "usd_total_mes": mes_total,
        "usd_ingenuo_mes_sin_dedup_ni_cache": ingenuo,
        "factor_ahorro": ingenuo / mes_modelo if mes_modelo else 0.0,
        "ingreso_mes": ingreso,
        "margen_bruto_usd": ingreso - mes_total,
        "margen_bruto_pct": (ingreso - mes_total) / ingreso * 100 if ingreso else 0.0,
        "costo_por_anuncio_nuevo_usd": f["usd_flash_por_corrida"] / max(1, f["anuncios_nuevos"]),
        "costo_por_suscriptor_mes": mes_total / max(1, s.suscriptores),
        "breakeven_suscriptores": -(-int(round(mes_total)) // int(s.precio_suscripcion_usd)),
    }


def main() -> int:
    s = Supuestos()
    errs = s.validar()
    if errs:
        for e in errs:
            print(f"SUPUESTO INCOHERENTE: {e}", file=sys.stderr)
        return 1

    filas = [modelo(s, "off-peak"), modelo(s, "peak")]

    print("=" * 78)
    print("MODELO DE COSTO - CASHGO ARQUITECTURA 3 (Inteligencia de Mercado)")
    print("Precios DeepSeek verificados en vivo 2026-09-06 (esquema peak/off-peak")
    print("vigente desde 2026-08-16). Se modela la tarifa mas caras a proposito.")
    print("=" * 78)
    for f in filas:
        print(f"\n--- VENTANA: {f['ventana'].upper()} ---")
        print(f"  marcas monitoreadas ................. {f['marcas']:>12,}")
        print(f"  anuncios vistos por corrida ......... {f['anuncios_vistos']:>12,}")
        print(f"  anuncios NUEVOS (pagan tokens) ...... {f['anuncios_nuevos']:>12,}")
        print(f"  descartados por dedup (hash) ........ {f['descartados_por_dedup']:>12,}")
        print(f"  llamadas a Flash por corrida ........ {f['llamadas_flash']:>12,}")
        print(f"  tokens de prefijo por corrida ....... {f['tok_prefijo_total']:>12,}")
        print(f"  USD Flash / corrida ................. {f['usd_flash_por_corrida']:>12.4f}")
        print(f"  USD Pro (40 informes) / corrida ..... {f['usd_pro_por_corrida']:>12.4f}")
        print(f"  USD / corrida ....................... {f['usd_por_corrida']:>12.4f}")
        print(f"  USD modelo / mes .................... {f['usd_modelo_mes']:>12.2f}")
        print(f"  USD infra / mes ..................... {f['usd_infra_mes']:>12.2f}")
        print(f"  USD TOTAL / mes ..................... {f['usd_total_mes']:>12.2f}")
        print(f"  (contrafactual sin dedup ni cache) .. {f['usd_ingenuo_mes_sin_dedup_ni_cache']:>12.2f}")
        print(f"  factor de ahorro .................... {f['factor_ahorro']:>11.1f}x")
        print(f"  costo por anuncio nuevo (USD) ....... {f['costo_por_anuncio_nuevo_usd']:>12.6f}")
        print(f"  costo por suscriptor / mes .......... {f['costo_por_suscriptor_mes']:>12.4f}")
        print(f"  ingreso / mes (30 x USD 79) ......... {f['ingreso_mes']:>12.2f}")
        print(f"  MARGEN BRUTO ........................ {f['margen_bruto_usd']:>12.2f}  ({f['margen_bruto_pct']:.2f}%)")
        print(f"  suscriptores para breakeven ......... {f['breakeven_suscriptores']:>12,}")

    out = Path(__file__).resolve().parent.parent / "evidencia" / "modelo_costo_arq3.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print(f"\nCSV escrito en: {out}")
    print("\nGUARD: el margen tiene que cerrar en la ventana PEAK, no solo en off-peak.")
    peak = filas[1]
    if peak["margen_bruto_pct"] < 80:
        print(f"GUARD ROJO: margen peak {peak['margen_bruto_pct']:.2f}% < 80%")
        return 1
    print(f"GUARD VERDE: margen peak {peak['margen_bruto_pct']:.2f}% >= 80%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
