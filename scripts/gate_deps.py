#!/usr/bin/env python3
"""
gate_deps.py - Gate de dependencias que SI puede decir por que esta rojo.

ORIGEN: hallazgo estructural de la auditoria independiente de Tao (2026-09-07).
El exit code de `pip-audit` vale 1 para tres cosas distintas: un advisory real, un
error del servicio y un crash no capturado. Un porton BLOQUEANTE que no distingue
"esto es vulnerable" de "no pude contestar" **entrena al equipo a ignorarlo**, y eso
es el peor resultado posible para un control: peor que no tenerlo, porque parece que
lo tenes.

Por que el diagnostico apunta al instrumento y no a los pines, medido: los tres
pines de `fase0/requirements.txt` estan limpios en tres bases de advisories
independientes (OSV, GHSA, Snyk), y `weasyprint==69.0` y `pypdf==6.14.2` son
justamente LAS VERSIONES QUE ARREGLAN CVE-2026-49452 y CVE-2026-59935. Ademas el
job `suite` corre `pip install -r fase0/requirements.txt` y esta VERDE sobre el
mismo head, asi que los tres existen en PyPI y resuelven. Con eso, un rojo de
`deps-pins` es casi con seguridad infraestructura, y el gate viejo no podia decirlo.

Tres estados, y el tercero es el aporte:

  0  VERDE            corrio, contesto, y no hay advisories aplicables
  1  ROJO SEGURIDAD   corrio, contesto, y hay al menos un advisory
  2  ROJO INSTRUMENTO no pudo contestar: sin archivo, JSON invalido, sin deps, o
                      con dependencias saltadas (respuesta parcial)

Los tres estados son los mismos tres de todo este repo: bien, mal y NO MEDIDO. Un
`2` no dice "estas seguro" ni "estas en riesgo": dice que la pregunta no se contesto,
que es una tercera cosa y hay que poder nombrarla.

Uso:  pip-audit -r req.txt --no-deps --timeout 60 --format json -o a.json || true
      python3 scripts/gate_deps.py a.json

El `|| true` va sobre pip-audit y NO sobre este gate: se descarta a proposito el
exit code que no distingue, y quien decide el color del job es este archivo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

VERDE, ROJO_SEGURIDAD, ROJO_INSTRUMENTO = 0, 1, 2

ETIQUETA = {
    VERDE: "VERDE",
    ROJO_SEGURIDAD: "ROJO SEGURIDAD",
    ROJO_INSTRUMENTO: "ROJO INSTRUMENTO",
}


def evaluar(ruta: Path) -> tuple[int, str]:
    """Devuelve (codigo, mensaje). No lanza: el codigo ES el veredicto."""
    if not ruta.is_file():
        return ROJO_INSTRUMENTO, f"pip-audit no dejo {ruta}: no llego a contestar"

    crudo = ruta.read_text(encoding="utf-8").strip()
    if not crudo:
        return ROJO_INSTRUMENTO, f"{ruta} esta vacio: pip-audit murio antes de escribir"

    try:
        datos = json.loads(crudo)
    except json.JSONDecodeError as e:
        # Firma tipica de un ReadTimeout contra pypi.org: la salida queda truncada
        # o trae un traceback. Hoy eso se ve IGUAL que un CVE.
        return ROJO_INSTRUMENTO, (
            f"{ruta} no es JSON valido ({e}): salida truncada o traceback")

    deps = datos.get("dependencies") if isinstance(datos, dict) else None
    if not isinstance(deps, list) or not deps:
        return ROJO_INSTRUMENTO, "el informe no trae ninguna dependencia: no se audito nada"

    saltadas = [d for d in deps if d.get("skip_reason")]
    hallazgos = [
        {
            "paquete": d.get("name"),
            "version": d.get("version"),
            "id": v.get("id"),
            "arregla_en": v.get("fix_versions") or [],
        }
        for d in deps
        for v in (d.get("vulns") or [])
    ]

    if hallazgos:
        lineas = [
            f"  - {h['paquete']} {h['version']}: {h['id']} "
            + (f"-> subir a {', '.join(h['arregla_en'])}" if h["arregla_en"]
               else "-> SIN version que lo arregle")
            for h in hallazgos
        ]
        return ROJO_SEGURIDAD, (
            f"{len(hallazgos)} advisory(s) sobre {len(deps)} dependencias:\n"
            + "\n".join(lineas))

    if saltadas:
        # Reemplaza a `--strict` con mas informacion: dice CUAL se salto y por que.
        nombres = ", ".join(
            f"{d.get('name')} ({d.get('skip_reason')})" for d in saltadas)
        return ROJO_INSTRUMENTO, (
            f"pip-audit SALTO dependencias, asi que la respuesta es parcial: {nombres}")

    return VERDE, f"{len(deps)} dependencias auditadas, cero advisories aplicables"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("uso: gate_deps.py <informe-de-pip-audit.json>", file=sys.stderr)
        return ROJO_INSTRUMENTO
    codigo, mensaje = evaluar(Path(argv[1]))
    salida = sys.stdout if codigo == VERDE else sys.stderr
    print(f"[{ETIQUETA[codigo]}] {mensaje}", file=salida)
    return codigo


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
