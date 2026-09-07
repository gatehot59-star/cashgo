#!/usr/bin/env python3
"""
manifiesto.py - Manifiesto criptografico de la evidencia y los documentos.

Cierra A1 de raiz (hallazgo del auditor externo, 2026-09-07): habia dos versiones
del informe con cifras distintas, y la palabra "canonizado" era una declaracion sin
verificacion. Con este manifiesto, "canonizado" pasa a ser comprobable: si el
informe que circula no tiene el hash del manifiesto, no es el informe auditado.

Modos:
  --escribir    genera evidencia/MANIFEST.sha256
  --verificar   compara el arbol contra el manifiesto. Exit 1 si algo difiere.

El guard de --verificar es falsable por construccion: cualquier edicion de un byte
en cualquier archivo cubierto lo pone en rojo. Es lo contrario del defecto 10.

DEFECTO 13, ENCONTRADO CORRIENDO SU PROPIO CONTROL POSITIVO (2026-09-07): la
primera version cubria tambien `evidencia/salida_manifiesto.txt`, que es el recibo
de este mismo script. Escribir ese recibo cambia su hash, asi que el guard daba
ROJO SIEMPRE y `exit restaurado` era 1: un guard que grita siempre es un guard que
nadie mira. La exclusion por autorreferencia esta declarada abajo con su motivo.

Uso:  python3 scripts/manifiesto.py --escribir | --verificar
Exit: 0 si coincide todo; 1 si hay diferencias, faltantes o sobrantes.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "evidencia" / "MANIFEST.sha256"

# EXCLUSION DECLARADA, con su motivo. `salida_manifiesto.txt` es el recibo de
# ESTE script: escribirlo cambia su hash, asi que si estuviera cubierto el
# manifiesto nunca podria verificarse a si mismo. Es un problema de
# autorreferencia, no una excepcion de conveniencia, y se detecto corriendo el
# control positivo: daba "2 distinto(s)" y "exit restaurado = 1" siempre.
EXCLUIDOS = frozenset({"evidencia/salida_manifiesto.txt"})

# ALCANCE DECLARADO, y por que es este y no "todos los .md".
# El manifiesto existe para cerrar UN modo de falla concreto: que el informe de
# auditoria que circula no sea el que esta en el repo, con cifras distintas (A1).
# Por eso ata el dossier, su evidencia y los instrumentos que la producen.
# Los demas documentos de decision (00-, 01-, ADR-*, CONTEXTO-) quedan atados por
# el propio git, que direcciona por contenido, y por el head SHA que el informe
# declara. Extender el patron a "*.md" hacia que el guard diera rojo en CI por
# archivos legitimos sin firmar, o sea un falso positivo: un guard que grita
# siempre es un guard que nadie mira.
PATRONES = (
    "evidencia/*.txt",
    "evidencia/*.csv",
    "02-INFORME-PARA-AUDITORIA.md",
    "scripts/*.py",
    "scripts/*.sh",
    ".github/workflows/*.yml",
)


def archivos() -> list[Path]:
    vistos: set[Path] = set()
    for patron in PATRONES:
        for f in RAIZ.glob(patron):
            if not f.is_file() or f == DESTINO:
                continue
            if str(f.relative_to(RAIZ)) in EXCLUIDOS:
                continue
            vistos.add(f)
    return sorted(vistos)


def sha256(f: Path) -> str:
    h = hashlib.sha256()
    with f.open("rb") as fh:
        for bloque in iter(lambda: fh.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def escribir() -> int:
    lineas = [f"{sha256(f)}  {f.relative_to(RAIZ)}" for f in archivos()]
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escritas {len(lineas)} entradas en {DESTINO.relative_to(RAIZ)}")
    return 0


def verificar() -> int:
    if not DESTINO.exists():
        print(f"GUARD ROJO: no existe {DESTINO.relative_to(RAIZ)}", file=sys.stderr)
        return 1

    esperado: dict[str, str] = {}
    for linea in DESTINO.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        h, _, ruta = linea.partition("  ")
        esperado[ruta.strip()] = h.strip()

    actual = {str(f.relative_to(RAIZ)): sha256(f) for f in archivos()}

    difieren = sorted(r for r in esperado.keys() & actual.keys() if esperado[r] != actual[r])
    faltan = sorted(esperado.keys() - actual.keys())
    sobran = sorted(actual.keys() - esperado.keys())

    for r in difieren:
        print(f"  DIFIERE   {r}")
    for r in faltan:
        print(f"  FALTA     {r}")
    for r in sobran:
        print(f"  SIN FIRMA {r}")

    if difieren or faltan or sobran:
        print(f"\nGUARD ROJO: {len(difieren)} distinto(s), {len(faltan)} faltante(s), "
              f"{len(sobran)} sin firma. El manifiesto no describe este arbol.",
              file=sys.stderr)
        return 1

    print(f"GUARD VERDE: las {len(actual)} entradas del manifiesto coinciden con el arbol.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Manifiesto sha256 de evidencia y documentos.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--escribir", action="store_true")
    g.add_argument("--verificar", action="store_true")
    args = p.parse_args(argv)
    return escribir() if args.escribir else verificar()


if __name__ == "__main__":
    sys.exit(main())
