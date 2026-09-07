#!/usr/bin/env python3
"""
informe_vs_csv.py - Ata la tabla de inventario del informe al CSV commiteado.

POR QUE EXISTE (hallazgo B del auditor externo, 2026-09-07, sexta reincidencia de
A1): en el head `de13b9a6` habia TRES cifras distintas para el mismo arbol en el
mismo commit.

    la tabla del informe .....  24 archivos / 4.653 / 2.947 / 230 / 753
    evidencia/inventario.csv .  23 archivos / 4.665 / 2.946 / 228 / 766 / 725
    el arbol recomputado .....  23 archivos / 4.666 / 2.946 / 228 / 767 / 725

El informe declaraba "el CI compara el CSV" y era cierto, pero su propia tabla no
salia del CSV: estaba TIPEADA. Un dossier cuya propuesta de valor es "cada cifra
se puede recomputar" no puede tener una tabla escrita a mano, porque la primera
recomputacion ajena la desmiente y con razon.

Este script cierra ese modo de falla POR CONSTRUCCION, no por disciplina: si la
fila TOTAL del informe no coincide con el CSV, exit 1 y el CI da rojo. Es el
mismo principio que el manifiesto, aplicado a la unica tabla del dossier que
duplica un dato que ya vive en otro archivo.

Alcance declarado: verifica UNA fila, la de totales, mas la cantidad de archivos.
No valida el desglose por capa (produccion / tests / fixtures / scripts) porque
esa agrupacion es editorial y no esta en el CSV. Ese desglose sigue siendo
tipeado y por lo tanto sigue siendo falible: se declara asi en el informe en vez
de fingir que esta cubierto.

Uso:  python3 scripts/informe_vs_csv.py
Exit: 0 si coinciden; 1 si difieren, si falta la fila, o si falta un archivo.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CSV = RAIZ / "evidencia" / "inventario.csv"
INFORME = RAIZ / "02-INFORME-PARA-AUDITORIA.md"
ETIQUETA = "**TOTAL Python**"
CAMPOS = ("archivos", "total", "codigo", "comentario", "docstring", "blanco")


def numeros(texto: str) -> list[int]:
    """
    Extrae los enteros de una fila de markdown, tolerando negrita y el separador
    de miles con punto (4.665 -> 4665). No tolera nada mas: un valor que no sea
    entero es un error del informe y tiene que dar rojo, no interpretarse.
    """
    celdas = [c.strip() for c in texto.strip().strip("|").split("|")]
    salida: list[int] = []
    for c in celdas[1:]:                      # la primera celda es la etiqueta
        limpia = c.replace("*", "").replace(".", "").replace(" ", "")
        if not limpia:
            continue
        if not re.fullmatch(r"\d+", limpia):
            print(f"GUARD ROJO: la celda {c!r} de la fila TOTAL del informe no es "
                  f"un entero.", file=sys.stderr)
            sys.exit(1)
        salida.append(int(limpia))
    return salida


def del_csv() -> list[int]:
    if not CSV.exists():
        print(f"GUARD ROJO: no existe {CSV.relative_to(RAIZ)}", file=sys.stderr)
        sys.exit(1)
    lineas = [x for x in CSV.read_text(encoding="utf-8").splitlines() if x.strip()]
    if not lineas or not lineas[0].startswith("archivo,"):
        print("GUARD ROJO: el CSV no arranca con su encabezado. Si arriba hay una "
              "linea de GUARD, el CSV esta contaminado (D1).", file=sys.stderr)
        sys.exit(1)
    filas_total = [x for x in lineas if x.startswith("TOTAL,")]
    if len(filas_total) != 1:
        print(f"GUARD ROJO: el CSV tiene {len(filas_total)} filas TOTAL, "
              f"tiene que tener exactamente 1.", file=sys.stderr)
        sys.exit(1)
    # datos = todo menos encabezado y la fila TOTAL
    archivos = len(lineas) - 2
    partes = filas_total[0].split(",")[1:]
    return [archivos, *[int(p) for p in partes]]


def del_informe() -> list[int]:
    if not INFORME.exists():
        print(f"GUARD ROJO: no existe {INFORME.relative_to(RAIZ)}", file=sys.stderr)
        sys.exit(1)
    filas = [x for x in INFORME.read_text(encoding="utf-8").splitlines()
             if ETIQUETA in x]
    if len(filas) != 1:
        print(f"GUARD ROJO: el informe tiene {len(filas)} filas con {ETIQUETA!r}; "
              f"tiene que tener exactamente 1 para poder atarse al CSV.",
              file=sys.stderr)
        sys.exit(1)
    return numeros(filas[0])


def main() -> int:
    csv = del_csv()
    inf = del_informe()

    if len(inf) != len(CAMPOS):
        print(f"GUARD ROJO: la fila TOTAL del informe trae {len(inf)} numeros y "
              f"tienen que ser {len(CAMPOS)} ({', '.join(CAMPOS)}).", file=sys.stderr)
        return 1

    diferencias = [(c, a, b) for c, a, b in zip(CAMPOS, inf, csv) if a != b]
    if diferencias:
        print("GUARD ROJO: la tabla del informe NO sale del CSV.", file=sys.stderr)
        for campo, en_informe, en_csv in diferencias:
            print(f"  {campo:<11} informe={en_informe:<8} csv={en_csv}", file=sys.stderr)
        print("\nRegenerar con: python3 scripts/inventario.py --csv > "
              "evidencia/inventario.csv  y copiar la fila TOTAL al informe.",
              file=sys.stderr)
        return 1

    print("GUARD VERDE: la fila TOTAL del informe coincide con evidencia/inventario.csv")
    for campo, valor in zip(CAMPOS, csv):
        print(f"  {campo:<11} {valor}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
