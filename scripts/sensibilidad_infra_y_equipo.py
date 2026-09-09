#!/usr/bin/env python3
"""
sensibilidad_infra_y_equipo.py

Contrasta el blueprint recibido (stack de ~14 componentes + 12 semanas con 2-3 devs)
contra el modelo de costo medido de la Arquitectura 3.

Dos preguntas que el blueprint afirma sin medir:
  A) "margen positivo desde el dia 1" -> ?a que costo de infra se rompe?
  B) "12 semanas" -> ?cuantas semanas son si el equipo es UNA persona?

Uso:  python3 scripts/sensibilidad_infra_y_equipo.py
Exit: 0 si el barrido corre, 1 si un supuesto es incoherente.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from modelo_costo_arq3 import Supuestos, modelo  # noqa: E402

# ---------------------------------------------------------------------------
# Costo de infra por componente. Precios de referencia de tiers de arranque
# (Railway/Fly/Render/gestionados) a 2026-09. NO son cotizaciones: son ordenes
# de magnitud, y estan explicitos para que se puedan discutir uno por uno.
# ---------------------------------------------------------------------------
STACK_MIO = {
    "Postgres administrado": 25.0,
    "1 worker + scheduler": 20.0,
    "Object storage + egress": 15.0,
}

STACK_BLUEPRINT = {
    "Postgres administrado": 25.0,
    "Redis administrado": 15.0,
    "API Gateway (Kong/Traefik gestionado)": 40.0,
    "Auth gestionado (Clerk/Auth0) tier pago": 25.0,
    "NATS JetStream (nodo)": 20.0,
    "Pool de Playwright (contenedores + CPU)": 60.0,
    "Proxies residenciales rotativos": 75.0,
    "Servicio orquestador IA": 20.0,
    "Servicio guardrail/finanzas": 15.0,
    "Servicio MCP gateway": 15.0,
    "Watchdog (proceso aislado)": 10.0,
    "Sentry (tier pago)": 26.0,
    "Grafana Cloud + Prometheus": 29.0,
    "Web app Next.js": 20.0,
}

SPRINTS = [
    ("S1-2  Fundaciones (infra, esquema, auth, scraper aislado)", 2),
    ("S3-4  Arquitectura 2 (lead magnet)", 2),
    ("S5-6  Middleware de guardrails + tests", 2),
    ("S7-8  MCP gateway + integracion Meta + FSM", 2),
    ("S9-10 Arquitectura 1 en modo interno", 2),
    ("S11-12 Hardening + piloto cliente externo", 2),
]
DEVS_BLUEPRINT = 2.5  # "2-3 devs full-stack + tu como product"


def barrido_infra() -> list[dict]:
    filas = []
    s_base = Supuestos()
    for infra in [0, 30, 60, 90, 120, 200, 300, 400, 500, 800, 1200, 2000, 2400]:
        s = Supuestos(**{**s_base.__dict__, "infra_usd_mes": float(infra)})
        m = modelo(s, "peak")
        filas.append({
            "infra": infra,
            "total": m["usd_total_mes"],
            "modelo_pct": m["usd_modelo_mes"] / m["usd_total_mes"] * 100,
            "margen_pct": m["margen_bruto_pct"],
            "breakeven": m["breakeven_suscriptores"],
        })
    return filas


def punto_de_quiebre(objetivo_pct: float) -> float:
    """Costo de infra (USD/mes) al que el margen peak cae al objetivo."""
    s = Supuestos()
    ingreso = s.precio_suscripcion_usd * s.suscriptores
    modelo_mes = modelo(s, "peak")["usd_modelo_mes"]
    # margen = (ingreso - modelo - infra) / ingreso = objetivo/100
    return ingreso * (1 - objetivo_pct / 100) - modelo_mes


def main() -> int:
    s = Supuestos()
    ingreso = s.precio_suscripcion_usd * s.suscriptores
    infra_mio = sum(STACK_MIO.values())
    infra_bp = sum(STACK_BLUEPRINT.values())

    if infra_bp <= infra_mio:
        print("SUPUESTO INCOHERENTE: el stack del blueprint deberia costar mas", file=sys.stderr)
        return 1

    print("=" * 78)
    print("A) COSTO DE INFRA: MI STACK vs EL STACK DEL BLUEPRINT")
    print("=" * 78)
    print(f"\n  Mi stack ({len(STACK_MIO)} componentes):")
    for k, v in STACK_MIO.items():
        print(f"    {k:.<52} USD {v:>7.2f}")
    print(f"    {'TOTAL':.<52} USD {infra_mio:>7.2f}")

    print(f"\n  Stack del blueprint ({len(STACK_BLUEPRINT)} componentes):")
    for k, v in STACK_BLUEPRINT.items():
        print(f"    {k:.<52} USD {v:>7.2f}")
    print(f"    {'TOTAL':.<52} USD {infra_bp:>7.2f}")
    print(f"\n  Factor: el blueprint cuesta {infra_bp / infra_mio:.1f}x mi stack en infra.")
    print("  (K8s NO esta contado: el blueprint lo pone como destino, no como MVP.)")

    print("\n" + "=" * 78)
    print("B) BARRIDO: A QUE COSTO DE INFRA SE ROMPE 'RENTABLE DESDE EL DIA 1'")
    print(f"   Ingreso fijo del modelo: USD {ingreso:.2f}/mes (30 x USD 79). Ventana PEAK.")
    print("=" * 78)
    print(f"\n  {'infra USD/mes':>14} {'total USD/mes':>14} {'% del total':>12} {'margen':>9} {'breakeven':>10}")
    print("  " + "-" * 64)
    for f in barrido_infra():
        marca = ""
        if abs(f["infra"] - infra_mio) < 1:
            marca = "  <- MI STACK"
        elif abs(f["infra"] - 400) < 1:
            marca = "  <- ~STACK BLUEPRINT"
        print(f"  {f['infra']:>14,} {f['total']:>14.2f} {f['modelo_pct']:>11.1f}% "
              f"{f['margen_pct']:>8.2f}% {f['breakeven']:>10,}{marca}")

    print(f"\n  Costo de infra al que el margen cae a 80%: USD {punto_de_quiebre(80):>9.2f}/mes")
    print(f"  Costo de infra al que el margen cae a 50%: USD {punto_de_quiebre(50):>9.2f}/mes")
    print(f"  Costo de infra al que el margen cae a  0%: USD {punto_de_quiebre(0):>9.2f}/mes")
    m_bp = modelo(Supuestos(**{**s.__dict__, "infra_usd_mes": infra_bp}), "peak")
    m_mio = modelo(s, "peak")
    print("\n  VEREDICTO A: el blueprint NO rompe el margen. Con su stack de "
          f"USD {infra_bp:.0f}\n  el margen peak sigue en {m_bp['margen_bruto_pct']:.2f}%.")
    print("  Lo que cambia es el BREAKEVEN y a que se parece el gasto: el modelo")
    print(f"  pasa de ser el {m_mio['usd_modelo_mes'] / m_mio['usd_total_mes'] * 100:.0f}% "
          f"de la factura al {m_bp['usd_modelo_mes'] / m_bp['usd_total_mes'] * 100:.0f}%.")
    print("  O sea: los dos coincidimos en que DeepSeek no es el problema, y el")
    print("  blueprint gasta su optimizacion de tokens en el lado chico de la factura.")

    print("\n" + "=" * 78)
    print("C) EL COSTO QUE EL BLUEPRINT NO PONE EN NINGUNA TABLA: SEMANAS-PERSONA")
    print("=" * 78)
    total_sem = sum(w for _, w in SPRINTS)
    print(f"\n  {'sprint':<58} {'sem':>4} {'sem-persona':>12}")
    print("  " + "-" * 76)
    for nombre, semanas in SPRINTS:
        print(f"  {nombre:<58} {semanas:>4} {semanas * DEVS_BLUEPRINT:>12.1f}")
    print("  " + "-" * 76)
    sp = total_sem * DEVS_BLUEPRINT
    print(f"  {'TOTAL':<58} {total_sem:>4} {sp:>12.1f}")
    print(f"\n  El plan declara {total_sem} semanas asumiendo {DEVS_BLUEPRINT} devs.")
    print(f"  Eso son {sp:.0f} semanas-persona de trabajo.")
    print(f"  Con UNA persona a tiempo completo: {sp:.0f} semanas = {sp / 4.33:.1f} MESES.")
    print(f"  Con UNA persona al 50% (hay otros proyectos vivos): {sp / 4.33 * 2:.1f} MESES.")
    print("\n  VEREDICTO C: el numero '12 semanas' no es del plan, es del EQUIPO que")
    print(f"  el plan supone. Si el equipo es uno, el mismo plan es de {sp / 4.33:.1f} a "
          f"{sp / 4.33 * 2:.1f} meses,")
    print("  y las Fases 3-4 quedan del otro lado de un ano.")
    print("  Esto NO refuta el blueprint: refuta leerlo como un cronograma.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
