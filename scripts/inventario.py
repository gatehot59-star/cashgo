#!/usr/bin/env python3
"""
inventario.py - Conteo estructural del arbol de codigo, por categoria de linea.

Clasifica CADA linea de cada modulo Python en exactamente una de cuatro
categorias: blanco, comentario, docstring, codigo. La suma por archivo es
identica al total de lineas del archivo, y eso se verifica con un assert: un
inventario cuya suma no cierra es un inventario que no sirve para auditar.

DEFECTO PROPIO QUE ORIGINO ESTE SCRIPT (2026-09-06): la primera version de este
conteo lo hice inline con `ast.get_docstring(...).count("\n")+1`, que cuenta las
lineas del TEXTO del docstring y no las que ocupa en el archivo (ignora las
comillas de apertura y cierre). Resultado: fase0/__init__.py reporto -1 lineas
de codigo. Un negativo es imposible por construccion, asi que el instrumento
estaba mal, no el archivo. Ahora se usan las posiciones reales del nodo
(lineno/end_lineno) y la identidad se verifica con assert.

SEGUNDO DEFECTO PROPIO, ENCONTRADO PROBANDO EL GUARD (2026-09-06): la primera
version tenia como unico guard "la suma cierra". Ese guard es INALCANZABLE: cada
linea se clasifica en exactamente una de cuatro categorias con un if/elif/else,
asi que la suma cierra SIEMPRE, por construccion. Lo comprobe inyectando un error
de sintaxis en fase0/dedup.py: el archivo no parseaba, los docstrings se contaban
como codigo, y el script daba VERDE igual. Un guard que no puede dar rojo es la
simulacion de una verificacion.

El guard corregido mide algo falsable: que TODOS los archivos parseen. Si uno no
parsea, su conteo de docstrings es invalido, se marca NO MEDIDO y el exit es 1.

Uso:  python3 scripts/inventario.py [--csv]
Exit: 0 si todos los archivos parsean y todas las sumas cierran.
      1 si algun archivo no parsea (conteo NO MEDIDO) o alguna suma no cierra.
"""
from __future__ import annotations

import argparse
import ast
import io
import sys
import tokenize
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
OBJETIVOS = ("fase0", "scripts")


@dataclass
class Conteo:
    total: int = 0
    codigo: int = 0
    comentario: int = 0
    docstring: int = 0
    blanco: int = 0
    parseo_ok: bool = True

    def cierra(self) -> bool:
        return self.total == self.codigo + self.comentario + self.docstring + self.blanco

    def __iadd__(self, otro: "Conteo") -> "Conteo":
        for c in ("total", "codigo", "comentario", "docstring", "blanco"):
            setattr(self, c, getattr(self, c) + getattr(otro, c))
        self.parseo_ok = self.parseo_ok and otro.parseo_ok
        return self


def lineas_de_docstring(arbol: ast.AST) -> set[int]:
    """
    Numeros de linea (1-indexados) ocupados por docstrings EN EL ARCHIVO.

    Usa lineno/end_lineno del nodo Constant, o sea las posiciones reales
    incluyendo las comillas. Contar los "\n" del texto del docstring subestima
    por 1 o 2 lineas segun el estilo de cierre, que es el bug que este script
    documenta en su encabezado.
    """
    lineas: set[int] = set()
    contenedores = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, contenedores):
            continue
        cuerpo = getattr(nodo, "body", None)
        if not cuerpo:
            continue
        primero = cuerpo[0]
        if not isinstance(primero, ast.Expr):
            continue
        valor = primero.value
        if not (isinstance(valor, ast.Constant) and isinstance(valor.value, str)):
            continue
        fin = valor.end_lineno or valor.lineno
        lineas.update(range(valor.lineno, fin + 1))
    return lineas


def lineas_de_comentario(src: str) -> set[int]:
    """Lineas cuyo unico contenido es un comentario, o que lo tienen al final."""
    lineas: set[int] = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                lineas.add(tok.start[0])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return lineas


def contar(ruta: Path) -> Conteo:
    src = ruta.read_text(encoding="utf-8")
    lineas = src.splitlines()
    c = Conteo(total=len(lineas))
    if not lineas:
        return c

    try:
        docs = lineas_de_docstring(ast.parse(src))
    except SyntaxError:
        # NO se traga el error: sin AST, las lineas de docstring se contarian como
        # codigo y el conteo del archivo seria falso con apariencia de correcto.
        docs = set()
        c.parseo_ok = False
    coments = lineas_de_comentario(src)

    for i, texto in enumerate(lineas, start=1):
        if not texto.strip():
            c.blanco += 1
        elif i in docs:
            # Precedencia: docstring gana sobre comentario. Un `#` adentro de un
            # docstring es prosa, no un comentario del lenguaje.
            c.docstring += 1
        elif i in coments and texto.strip().startswith("#"):
            c.comentario += 1
        else:
            # Incluye lineas con codigo + comentario al final: se cuentan como
            # codigo, porque la linea existe por el codigo.
            c.codigo += 1
    return c


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Inventario estructural del arbol.")
    p.add_argument("--csv", action="store_true", help="salida CSV en vez de tabla")
    args = p.parse_args(argv)

    archivos = sorted(
        f for d in OBJETIVOS for f in (RAIZ / d).rglob("*.py")
        if "__pycache__" not in f.parts
    )

    filas: list[tuple[str, Conteo]] = []
    total = Conteo()
    incoherentes: list[str] = []
    sin_parsear: list[str] = []
    for f in archivos:
        c = contar(f)
        rel = str(f.relative_to(RAIZ))
        if not c.cierra():
            incoherentes.append(rel)
        if not c.parseo_ok:
            sin_parsear.append(rel)
        filas.append((rel, c))
        total += c

    if args.csv:
        print("archivo,total,codigo,comentario,docstring,blanco")
        for rel, c in filas:
            print(f"{rel},{c.total},{c.codigo},{c.comentario},{c.docstring},{c.blanco}")
        print(f"TOTAL,{total.total},{total.codigo},{total.comentario},"
              f"{total.docstring},{total.blanco}")
    else:
        enc = f"{'archivo':<40}{'total':>7}{'codigo':>8}{'coment':>8}{'docstr':>8}{'blanco':>8}"
        print(enc)
        print("-" * len(enc))
        for rel, c in filas:
            print(f"{rel:<40}{c.total:>7}{c.codigo:>8}{c.comentario:>8}"
                  f"{c.docstring:>8}{c.blanco:>8}")
        print("-" * len(enc))
        print(f"{'TOTAL':<40}{total.total:>7}{total.codigo:>8}{total.comentario:>8}"
              f"{total.docstring:>8}{total.blanco:>8}")
        if total.codigo:
            ratio = (total.comentario + total.docstring) / total.codigo
            print(f"\nratio (comentario + docstring) / codigo = {ratio:.3f}")

    rojo = False
    if sin_parsear:
        rojo = True
        print("\nGUARD ROJO - archivos que NO parsean; su conteo de docstring y",
              "codigo es NO MEDIDO:", file=sys.stderr)
        for x in sin_parsear:
            print(f"  {x}", file=sys.stderr)
    if incoherentes:
        rojo = True
        print("\nGUARD ROJO - la suma no cierra en:", file=sys.stderr)
        for x in incoherentes:
            print(f"  {x}", file=sys.stderr)
    if rojo:
        return 1

    print(f"\nGUARD VERDE: los {len(filas)} archivos parsean y en todos "
          f"total = codigo + comentario + docstring + blanco.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
