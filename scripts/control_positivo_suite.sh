#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# CONTROL POSITIVO DE LA SUITE (W-01: un instrumento que no puede dar rojo no
# sirve para auditar).
#
# Inyecta defectos reales de una linea, uno por vez, y verifica que la suite los
# CAZE. Si alguna mutacion sobrevive, la suite es decorativa en esa propiedad.
#
# HISTORIA DE ESTE SCRIPT, QUE ES LA PARTE QUE HAY QUE LEER:
#
# 1. Su primera corrida (2026-09-06) encontro un hueco real: la mutacion que mete
#    la fecha en el content_hash paso en VERDE porque habia un test contra la
#    fecha de FIN y ninguno contra la de INICIO.
#
# 2. B1, hallazgo del auditor externo (2026-09-07): el script tomaba como
#    [CAZADO] cualquier exit != 0 de unittest, INCLUIDO UN ERROR DE IMPORT. O sea
#    que una mutacion que rompia el modulo se reportaba como detectada sin que
#    ninguna propiedad se hubiera medido. Es el mismo defecto que el script fue
#    escrito para denunciar: el guard daba el color esperado sin medir la
#    propiedad. Medido: con un import de un modulo inexistente en schemas.py la
#    suite daba exit 1 con 5 ModuleNotFoundError y cero tests ejecutados.
#
#    Correccion, dos condiciones NUEVAS y necesarias para declarar [CAZADA]:
#      a) el archivo mutado tiene que COMPILAR (py_compile). Una mutacion que no
#         compila no prueba nada sobre la suite.
#      b) el NOMBRE DEL TEST ESPERADO tiene que aparecer en la salida de unittest
#         como fallido. Que la suite falle no alcanza: tiene que fallar POR ESTO.
#
# 3. Y la condicion (b) encontro el DEFECTO 12 en la primera corrida: la mutacion
#    de `angulo` devolvio [ROJO AJENO], porque el test que el informe citaba como
#    prueba de la contencion estructural pasaba en VERDE con la taxonomia abierta.
#
# 4. DEFECTO 17 (2026-09-07): este script quedo divergiendo entre el arbol de
#    trabajo y git, junto con otros cinco archivos, porque los edite DESPUES de
#    pushearlos. Lo cazo el CI, no yo.
#
# 5. DEFECTO 18, y es la causa raiz del 17 en este archivo: el ancla de la
#    mutacion 1 contenia una secuencia de escape Unicode, y eso hacia el archivo
#    NO TRANSPORTABLE. Al viajar en un payload JSON la secuencia se convertia en
#    el caracter real, el ancla dejaba de matchear en el runner y el CI daba
#    [ERROR]. Siete intentos de reproducir el delta a mano antes de mirar el
#    mecanismo. Regla que sale de esto: **un instrumento que se transporta no
#    puede contener secuencias de escape en sus datos.**
#
# 6. D3, hallazgo del auditor externo (2026-09-07): este script MUTA EL ARBOL REAL
#    y la restauracion dependia de un unico `trap ... EXIT`. Ya dejo un mutante
#    vivo en report.py una vez (commit df23b88), y no habia chequeo de arbol limpio
#    antes de arrancar: si el arbol ya tenia cambios sin commitear, la restauracion
#    por copia los pisaba o los mezclaba con el mutante, sin que nadie lo notara.
#
#    Tres correcciones, y ninguna es "tener mas cuidado":
#      a) ARRANQUE BLOQUEADO SI EL ARBOL ESTA SUCIO en los archivos que se mutan.
#         Con esto el defecto 17 tambien habria dado rojo LOCAL, no solo en el CI.
#      b) La restauracion es DOBLE: copia del respaldo Y `git checkout --` de los
#         archivos mutables. La copia cubre el caso sin git; git cubre el caso en
#         que la copia se hizo sobre un arbol ya contaminado.
#      c) El trap atrapa EXIT, INT y TERM y llama a la restauracion, no solo al
#         borrado del temporal. Una interrupcion con Ctrl-C ahora restaura.
#
#    LIMITACION QUE SIGUE EN PIE Y SE DECLARA: un `kill -9` o la muerte del
#    sandbox no ejecutan ningun trap. Si eso pasa, el arbol queda con un mutante.
#    Lo que cambia con (a) es que la PROXIMA corrida se niega a arrancar en vez de
#    trabajar sobre un arbol contaminado, y el CI da rojo en el diff de custodia.
#    Verificacion manual: `git status --porcelain fase0` o `grep -rn "# MUTANTE" fase0`.
#
# Uso: bash scripts/control_positivo_suite.sh
# Exit 0 = todas las mutaciones detectadas por el test correcto.
# Exit 2 = el script se niega a correr (arbol sucio): no se midio nada.
# ---------------------------------------------------------------------------
set -uo pipefail
cd "$(dirname "$0")/.."

# Los unicos archivos que este script tiene permitido tocar. La lista es cerrada
# a proposito: el guard de arbol limpio y la restauracion por git se aplican
# EXACTAMENTE a estos, para no pisar trabajo en curso en el resto del arbol.
ARCHIVOS_MUTABLES=(fase0/schemas.py fase0/report.py fase0/cognitive.py)

HAY_GIT=0
if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
    HAY_GIT=1
fi

# (a) Guard de arranque. Tres estados: limpio, sucio, y NO MEDIDO si no hay git.
if [ "$HAY_GIT" -eq 1 ]; then
    SUCIO="$(git status --porcelain -- "${ARCHIVOS_MUTABLES[@]}")"
    if [ -n "$SUCIO" ]; then
        echo "ABORTA: el arbol tiene cambios sin commitear en los archivos que este"
        echo "script muta. Correr asi mezcla tus cambios con los mutantes y la"
        echo "restauracion no puede distinguirlos."
        echo "$SUCIO"
        echo
        echo "Commitea o guarda esos cambios y volve a correr. No se midio nada."
        exit 2
    fi
    echo "arbol limpio en los archivos mutables: verificado con git status."
else
    echo "AVISO: no hay repo git accesible. El guard de arbol limpio queda NO MEDIDO"
    echo "y la restauracion depende solo de la copia de respaldo."
fi

TMP="$(mktemp -d)"
cp -r fase0 "$TMP/respaldo"

restaurar() {
    rm -rf fase0
    cp -r "$TMP/respaldo" fase0
    # (b) segunda via: git manda sobre la copia para los archivos mutables.
    if [ "$HAY_GIT" -eq 1 ]; then
        git checkout -- "${ARCHIVOS_MUTABLES[@]}" 2>/dev/null || true
    fi
}

# (c) el trap restaura y despues limpia. Antes solo limpiaba el temporal, asi que
# una interrupcion dejaba el mutante vivo en el arbol.
trap 'restaurar; rm -rf "$TMP"' EXIT INT TERM

fallos=0
cazadas=0

# probar_mutacion <nombre> <archivo> <desde> <hasta> <test_esperado>
probar_mutacion() {
    local nombre="$1" archivo="$2" desde="$3" hasta="$4" esperado="$5"

    if ! python3 - "$archivo" "$desde" "$hasta" <<'PY'
import sys, pathlib
ruta, desde, hasta = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path(ruta); t = p.read_text()
if desde not in t:
    print(f"ANCLA NO ENCONTRADA en {ruta}: {desde!r}", file=sys.stderr); sys.exit(3)
p.write_text(t.replace(desde, hasta, 1))
PY
    then
        echo "  [ERROR ]  $nombre  <-- no se pudo aplicar la mutacion"
        fallos=$((fallos + 1)); restaurar; return
    fi

    # (a) el mutante tiene que compilar. Si no, no se midio ninguna propiedad.
    if ! python3 -m py_compile "$archivo" 2>/dev/null; then
        echo "  [INVALIDA]  $nombre  <-- el mutante no compila: no prueba nada"
        fallos=$((fallos + 1)); restaurar; return
    fi

    local salida
    salida="$(python3 -m unittest discover -s fase0/tests -t . 2>&1)"
    local codigo=$?

    if [ "$codigo" -eq 0 ]; then
        echo "  [SOBREVIVE]  $nombre  <-- LA SUITE NO LO CAZA"
        fallos=$((fallos + 1)); restaurar; return
    fi

    # (b) tiene que fallar POR EL TEST ESPERADO, no por cualquier motivo.
    if ! grep -q "$esperado" <<<"$salida"; then
        echo "  [ROJO AJENO]  $nombre"
        echo "               la suite fallo pero '$esperado' no aparece en la salida:"
        echo "               fallo por otro motivo, asi que la propiedad NO se midio"
        fallos=$((fallos + 1)); restaurar; return
    fi

    echo "  [CAZADA]  $nombre"
    echo "            por: $esperado"
    cazadas=$((cazadas + 1))
    restaurar
}

echo "=============================================================================="
echo "CONTROL POSITIVO: cada mutacion tiene que ser cazada POR SU TEST, no por azar"
echo "=============================================================================="

# 1. La fecha en el content_hash mata el ahorro por deduplicacion.
#
# El ancla apunta al CIERRE del payload del hash y no a su apertura, porque la
# linea de apertura contiene una secuencia de escape Unicode y eso hacia el
# archivo no transportable (defecto 18). Esta es equivalente y no tiene backslashes.
probar_mutacion "content_hash incluye la fecha de inicio -> se rompe el dedup" \
  "fase0/schemas.py" \
  '            *self.descripciones,
        ])' \
  '            *self.descripciones,
            self.inicio.isoformat(),
        ])' \
  "test_ignora_la_fecha_de_inicio"

# 2. Abrir la taxonomia desarma la contencion de inyeccion de prompt.
probar_mutacion "angulo pasa de Literal cerrado a str -> se cae el guard de inyeccion" \
  "fase0/schemas.py" \
  "    angulo: Angulo" \
  "    angulo: str  # MUTANTE" \
  "test_cada_campo_cerrado_contiene_por_si_solo"

# 3. Dejar de escapar HTML compromete el entregable.
probar_mutacion "el informe deja de escapar HTML -> XSS en el entregable" \
  "fase0/report.py" \
  '    return html.escape(str(valor), quote=True)' \
  '    return str(valor)  # MUTANTE' \
  "test_no_queda_ningun_script_en_todo_el_documento"

# 4. (D1) Quitar el filtro de ad_id inventados deja pasar alucinaciones.
probar_mutacion "se deja de filtrar ad_id alucinados -> el informe cita anuncios inexistentes" \
  "fase0/cognitive.py" \
  '            if a.ad_id not in pedidos:' \
  '            if False:  # MUTANTE' \
  "test_saca_ad_ids_alucinados"

# 5. (D1) Vaciar sin_urls mete dominios de terceros en el PDF del cliente.
probar_mutacion "sin_urls deja de sustituir -> URLs ajenas en el entregable" \
  "fase0/schemas.py" \
  '    return _ESPACIOS.sub(" ", _URL.sub("[enlace]", texto)).strip()' \
  '    return texto  # MUTANTE' \
  "test_se_aplica_en_el_esquema_del_analisis"

# 6. (B3) Dejar de neutralizar el delimitador reabre la contaminacion intra-lote.
probar_mutacion "normalizar deja de neutralizar el delimitador -> contaminacion intra-lote" \
  "fase0/schemas.py" \
  '    limpio = _SECUENCIA_DELIMITADOR.sub(lambda m: m.group(0)[0] * 2, limpio)' \
  '    pass  # MUTANTE' \
  "test_el_copy_no_puede_fabricar_un_bloque"

# 7. (B2) Volver a usar sets deja pasar el ad_id repetido.
probar_mutacion "se deja de detectar el ad_id repetido -> una clasificacion se pierde sin registro" \
  "fase0/cognitive.py" \
  '            if a.ad_id in ya_visto:' \
  '            if False:  # MUTANTE' \
  "test_gana_la_primera_ocurrencia_y_la_segunda_se_registra"

echo "------------------------------------------------------------------------------"
if [ "$fallos" -eq 0 ]; then
    echo "VERDE: $cazadas/$cazadas mutaciones cazadas por su test especifico."
    if python3 -m unittest discover -s fase0/tests -t . >/dev/null 2>&1; then
        echo "Y el arbol restaurado sigue en verde."
        exit 0
    fi
    echo "ROJO: el arbol NO quedo restaurado."
    exit 1
fi
echo "ROJO: $fallos mutacion(es) no cazada(s) correctamente de $((cazadas + fallos))."
exit 1
