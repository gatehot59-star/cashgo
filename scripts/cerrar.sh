#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# cerrar.sh - El cierre de turno como INSTRUMENTO, no como disciplina.
#
# POR QUE EXISTE (hallazgo D5 del auditor externo, 2026-09-07): de los 22 commits
# del PR, 8 eran `fix(ci)` de convergencia dentro de 70 minutos. El registro de
# defectos lo documentaba con honestidad (15, 17, 18) y esa honestidad no arreglo
# nada: los recibos se seguian generando a mano, uno por uno, y la tabla del
# informe se seguia tipeando. A1 reincidio SEIS veces, y la sexta fue mientras se
# corregia la quinta. La conclusion del propio defecto 17 era "reemplazar
# disciplina por instrumento". Este script es ese instrumento.
#
# DOS MODOS, Y LA DIFERENCIA IMPORTA:
#
#   bash scripts/cerrar.sh                VERIFICAR. No escribe ningun recibo.
#                                         Corre los instrumentos, compara contra
#                                         lo commiteado y exige `git status`
#                                         limpio. Es el modo del hook pre-push.
#
#   bash scripts/cerrar.sh --regenerar    REGENERAR. Reescribe los recibos desde
#                                         este arbol. Se usa una vez, antes del
#                                         commit de convergencia.
#
# POR QUE NO ES UN SOLO MODO QUE REGENERA SIEMPRE (defecto 22, encontrado por este
# mismo script en su primera corrida): `unittest -v` imprime el tiempo transcurrido
# ("Ran 128 tests in 1.356s"), asi que su recibo cambia de bytes en cada corrida
# aunque el arbol sea identico. Con un unico modo que regenera, el chequeo de
# custodia daba ROJO SIEMPRE por una razon que no era un defecto. Es exactamente el
# defecto 13 otra vez (guard autorreferente que grita siempre y por eso nadie mira),
# y aparecio en el instrumento escrito para no volver a cometerlo.
#
#   Consecuencia declarada: un recibo de corrida es una FOTO de una corrida, con su
#   duracion adentro, y no un artefacto reproducible. Lo reproducible es el
#   inventario, el manifiesto y el veredicto. La custodia se verifica sobre esos.
#
# Instalacion como hook (cierra el ciclo del lado del autor):
#   printf '#!/bin/sh\nexec bash scripts/cerrar.sh\n' > .git/hooks/pre-push
#   chmod +x .git/hooks/pre-push
#
# Exit 0 = el arbol, sus recibos y el informe son consistentes y todo da verde.
# Exit 1 = algo no cierra. El mensaje dice exactamente que.
# ---------------------------------------------------------------------------
set -uo pipefail
cd "$(dirname "$0")/.."

REGENERAR=0
RAPIDO=0
for arg in "$@"; do
    case "$arg" in
        --regenerar) REGENERAR=1 ;;
        --rapido)    RAPIDO=1 ;;
        *) echo "opcion desconocida: $arg"; exit 1 ;;
    esac
done

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fallos=0
paso() { echo; echo "=== $* ==="; }
mal() { echo "ROJO: $*"; fallos=$((fallos + 1)); }

# Cabecera de procedencia de cada recibo. Es la convencion que ya usaba
# evidencia/salida_reconciliacion_prefijo.txt y que los recibos generados a mano
# habian perdido: sin ella, un archivo de evidencia no dice QUIEN lo corrio, CON
# QUE COMANDO ni CUANDO, y entonces no se puede contradecir (W-01).
cabecera() {
    local destino="$1" comando="$2"
    {
        echo "# EVIDENCIA CRUDA - VERBATIM (W-01)"
        echo "# Instrumento: $comando"
        echo "# Corrido por: BRAIN en su sandbox ($(python3 -V 2>&1))"
        echo "# Dependencias: $(grep -v '^#' fase0/requirements.txt | tr '\n' ' ')"
        echo "# Generado por: bash scripts/cerrar.sh --regenerar"
        echo "#"
    } > "$destino"
}

if [ "$REGENERAR" -eq 1 ]; then
    echo "MODO REGENERAR: se reescriben los recibos desde este arbol."
else
    echo "MODO VERIFICAR: no se escribe ningun recibo (usar --regenerar para eso)."
fi

paso "0/6  fixtures (datos de prueba como codigo)"
python3 -m fase0.fixtures.generar || mal "no se pudieron generar los fixtures"

paso "1/6  inventario: stdout es CSV puro, el guard va a stderr (D1)"
if [ "$REGENERAR" -eq 1 ]; then
    python3 scripts/inventario.py --csv > evidencia/inventario.csv || mal "inventario en rojo"
    cabecera evidencia/salida_inventario.txt "python3 scripts/inventario.py"
    python3 scripts/inventario.py >> evidencia/salida_inventario.txt 2>&1 || mal "inventario (tabla) en rojo"
    tail -1 evidencia/inventario.csv
else
    python3 scripts/inventario.py --csv > "$TMP/inv.csv" || mal "inventario en rojo"
    if diff -u evidencia/inventario.csv "$TMP/inv.csv"; then
        echo "VERDE: el CSV commiteado describe este arbol."
    else
        mal "evidencia/inventario.csv NO describe este arbol (A1). Correr --regenerar."
    fi
fi

paso "2/6  el informe tiene que citar los numeros del CSV, no otros"
python3 scripts/informe_vs_csv.py || mal "la tabla del informe no sale del CSV"

paso "3/6  suite completa"
DEST_TESTS="$TMP/tests.txt"
[ "$REGENERAR" -eq 1 ] && DEST_TESTS="evidencia/salida_tests_fase0.txt"
[ "$REGENERAR" -eq 1 ] && cabecera "$DEST_TESTS" "python3 -m unittest discover -s fase0/tests -t . -v"
if python3 -m unittest discover -s fase0/tests -t . -v >> "$DEST_TESTS" 2>&1; then
    tail -3 "$DEST_TESTS"
else
    mal "la suite no pasa"; tail -20 "$DEST_TESTS"
fi

paso "4/6  control positivo (cada mutacion por su test)"
DEST_CP="$TMP/cp.txt"
[ "$REGENERAR" -eq 1 ] && DEST_CP="evidencia/salida_control_positivo.txt"
if [ "$RAPIDO" -eq 1 ]; then
    echo "SALTADO por --rapido. Su resultado queda NO MEDIDO en este cierre."
elif { [ "$REGENERAR" -eq 1 ] && cabecera "$DEST_CP" "bash scripts/control_positivo_suite.sh"; true; } && \
     bash scripts/control_positivo_suite.sh >> "$DEST_CP" 2>&1; then
    tail -3 "$DEST_CP"
else
    mal "el control positivo no da verde"; tail -20 "$DEST_CP"
fi

paso "5/6  pipeline end to end, PDF y modelos de costo"
DEST_DRY="$TMP/dry.txt"; DEST_MC="$TMP/mc.txt"; DEST_SENS="$TMP/sens.txt"
if [ "$REGENERAR" -eq 1 ]; then
    DEST_DRY="evidencia/salida_fase0_dryrun.txt"
    DEST_MC="evidencia/salida_modelo_costo_arq3.txt"
    DEST_SENS="evidencia/salida_sensibilidad_infra_y_equipo.txt"
    cabecera "$DEST_DRY" "python3 -m fase0.pipeline ... --dry-run ... --pdf"
    cabecera "$DEST_MC" "python3 scripts/modelo_costo_arq3.py"
    cabecera "$DEST_SENS" "python3 scripts/sensibilidad_infra_y_equipo.py"
else
    : > "$DEST_DRY"; : > "$DEST_MC"; : > "$DEST_SENS"
fi
python3 -m fase0.pipeline fase0/fixtures/brief_ejemplo.json \
    --dry-run fase0/fixtures/ads_archive_sample.json \
    --salida artefactos --pdf >> "$DEST_DRY" 2>&1 \
    || mal "el pipeline end to end no corre"
# Ojo: este escribe evidencia/modelo_costo_arq3.csv en los dos modos. Es
# determinista y con lineterminator LF explicito, asi que no ensucia el arbol.
python3 scripts/modelo_costo_arq3.py >> "$DEST_MC" 2>&1 || mal "el modelo de costo da rojo"
python3 scripts/sensibilidad_infra_y_equipo.py >> "$DEST_SENS" 2>&1 || mal "la sensibilidad da rojo"
grep -E "GUARD (VERDE|ROJO)" "$DEST_MC" || true

paso "6/6  manifiesto: se toca DESPUES de todo lo anterior"
if [ "$REGENERAR" -eq 1 ]; then
    cabecera evidencia/salida_manifiesto.txt "python3 scripts/manifiesto.py --escribir"
    python3 scripts/manifiesto.py --escribir >> evidencia/salida_manifiesto.txt 2>&1 \
        || mal "no se pudo escribir el manifiesto"
    cat evidencia/salida_manifiesto.txt
fi
python3 scripts/manifiesto.py --verificar || mal "el manifiesto no describe este arbol"

# --- EL CHEQUEO QUE NO EXISTIA -------------------------------------------------
paso "custodia: nada puede quedar sin commitear"
if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
    PENDIENTE="$(git status --porcelain)"
    if [ -n "$PENDIENTE" ]; then
        echo "$PENDIENTE"
        echo
        if [ "$REGENERAR" -eq 1 ]; then
            echo "ESPERADO en modo --regenerar: commitea esto en UN commit de"
            echo "convergencia y despues corre 'bash scripts/cerrar.sh' sin flags."
        else
            mal "hay cambios sin commitear: lo que esta en git NO describe este arbol."
            echo "     Esto es A1, cazado antes del push en vez de despues."
        fi
    else
        echo "VERDE: git status limpio."
    fi
else
    echo "NO MEDIDO: sin repo git no se puede verificar la custodia."
fi

echo
echo "=============================================================================="
if [ "$fallos" -eq 0 ]; then
    echo "CIERRE VERDE: los 6 chequeos pasan y el arbol coincide con sus recibos."
    exit 0
fi
echo "CIERRE ROJO: $fallos problema(s). NO pushear hasta que cierren."
exit 1
