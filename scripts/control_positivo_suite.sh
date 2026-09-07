#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# CONTROL POSITIVO DE LA SUITE (W-01: un instrumento que no puede dar rojo no
# sirve para auditar).
#
# Inyecta tres defectos reales, uno por vez, y verifica que la suite los CAZA.
# Si alguna mutacion pasa en verde, la suite es decorativa y el script falla.
#
# La primera corrida de este script (2026-09-06) encontro un hueco real: la
# mutacion 1 paso en VERDE porque yo tenia un test contra la fecha de FIN en el
# content_hash y ninguno contra la de INICIO. El test que faltaba esta ahora en
# fase0/tests/test_schemas_y_dedup.py::test_ignora_la_fecha_de_inicio.
#
# Uso: bash scripts/control_positivo_suite.sh
# Exit 0 = las tres mutaciones fueron detectadas.
# ---------------------------------------------------------------------------
set -uo pipefail
cd "$(dirname "$0")/.."

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cp -r fase0 "$TMP/respaldo"

restaurar() { rm -rf fase0; cp -r "$TMP/respaldo" fase0; }

fallos=0
probar_mutacion() {
    local nombre="$1" archivo="$2" desde="$3" hasta="$4"
    python3 - "$archivo" "$desde" "$hasta" <<'PY'
import sys, pathlib
ruta, desde, hasta = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path(ruta); t = p.read_text()
if desde not in t:
    print(f"ANCLA NO ENCONTRADA en {ruta}: {desde!r}", file=sys.stderr); sys.exit(3)
p.write_text(t.replace(desde, hasta, 1))
PY
    if [ $? -ne 0 ]; then
        echo "  [ERROR] no se pudo aplicar la mutacion: $nombre"
        fallos=$((fallos + 1)); restaurar; return
    fi
    if python3 -m unittest discover -s fase0/tests -t . >/dev/null 2>&1; then
        echo "  [ROJO ESPERADO / VERDE OBTENIDO]  $nombre  <-- LA SUITE NO LO CAZA"
        fallos=$((fallos + 1))
    else
        echo "  [CAZADO]  $nombre"
    fi
    restaurar
}

echo "=============================================================="
echo "CONTROL POSITIVO: la suite tiene que dar ROJO ante estos 3 bugs"
echo "=============================================================="

# 1. Meter la fecha en el content_hash mata el 88% de ahorro del dedup.
probar_mutacion "content_hash incluye la fecha de entrega -> se rompe el dedup" \
  "fase0/schemas.py" \
  '        payload = "\u241f".join([
            self.page_id,' \
  '        payload = "\u241f".join([
            self.page_id,
            self.inicio.isoformat(),'

# 2. Aceptar cualquier string como angulo abre la puerta a la inyeccion.
probar_mutacion "angulo pasa de Literal cerrado a str -> se cae el guard de inyeccion" \
  "fase0/schemas.py" \
  "    angulo: Angulo" \
  "    angulo: str  # MUTANTE"

# 3. Dejar de escapar el HTML del informe.
probar_mutacion "el informe deja de escapar HTML -> XSS en el entregable" \
  "fase0/report.py" \
  '    return html.escape(str(valor), quote=True)' \
  '    return str(valor)  # MUTANTE'

echo "--------------------------------------------------------------"
if [ "$fallos" -eq 0 ]; then
    echo "VERDE: las 3 mutaciones fueron detectadas. La suite puede dar rojo."
    python3 -m unittest discover -s fase0/tests -t . >/dev/null 2>&1 \
      && echo "Y el arbol restaurado sigue en verde." \
      || { echo "ROJO: el arbol NO quedo restaurado."; exit 1; }
    exit 0
fi
echo "ROJO: $fallos mutacion(es) no detectada(s). La suite es decorativa ahi."
exit 1
