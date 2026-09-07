# INFORME TECNICO DE AUDITORIA · PROYECTO CASHGO

**Revision:** 2 · **Rama:** `titan/auditoria-cashgo`
**Head auditado por el revisor externo:** `31178a1b189c8eac8e71779e7ec2744998a8505c`
**Artefacto de custodia:** `evidencia/MANIFEST.sha256`
**Autor:** BRAIN (agente). **No es independiente.**

## Estado de esta revision

La revision externa estatica produjo 14 hallazgos: **13 concedidos y 1 refutado parcialmente con medicion**. El revisor no ejecuto la suite. En esta revision se corrigen los hallazgos de codigo e instrumentos, se agrega evidencia de la reincidencia del proceso y se endurecen las condiciones del control positivo.

### Cadena de custodia

El informe anterior no existia como archivo del arbol y habia dos redacciones con cifras distintas. Ahora este archivo, la evidencia y los instrumentos se firman con `evidencia/MANIFEST.sha256`; el CI verifica el manifiesto y hace diff del inventario contra el CSV commiteado.

**Conflicto de interes:** el autor del codigo escribe el informe. El contrapeso es la evidencia cruda, el CI externo y la revision externa. Copilot sigue sin emitir hallazgos: **NO MEDIDO**, no aprobacion.

## Inventario

Instrumento: `python3 scripts/inventario.py`. El CI lo ejecuta en runner limpio y compara el CSV.

| Capa | Archivos | Total | Codigo | Comentario | Docstring |
|---|---:|---:|---:|---:|---:|
| Produccion `fase0/` | 10 | 2.313 | 1.435 | 154 | 391 |
| Tests `fase0/tests/` | 8 | 1.459 | 904 | 6 | 278 |
| Fixtures | 2 | 174 | 130 | 15 | 10 |
| Scripts | 4 | 707 | 478 | 55 | 74 |
| **TOTAL Python** | **24** | **4.653** | **2.947** | **230** | **753** |

Lineas de codigo de test/produccion: **0,63**. Ratio comentario+docstring/codigo: **0,334**. Dependencias de terceros: 3, pinneadas exactas. Dependencias de test: 0.

## Arquitectura e invariantes

```
ads_archive oficial -> persistencia SQLite -> SHA-256 de contenido
-> DeepSeek V4-Flash (funcion pura, sin credenciales)
-> agregacion determinista -> HTML -> PDF
```

El criterio de frontera es: si el error cuesta dinero o es irreversible, la logica es determinista; si cuesta un token, puede ser cognitiva.

Invariantes: el LLM no porta credenciales; todo output se valida con `Literal` y `extra="forbid"`; `content_hash` excluye `ad_id`, fechas y plataformas; outputs repetidos, omitidos o inventados se distinguen; `<<<` se neutraliza en ingesta; el prompt estable tiene SHA-256; el HTML se escapa; la tasa de cache tiene tres estados: VERDE, ROJO, NO MEDIDO.

## Verificacion

### CI ajeno

Runs sobre el head previo auditado: `34077436280` y `34077439303`, ambos `suite`, `conclusion: success`, runner `ubuntu-24.04` limpio. Etapas: instalar dependencias, generar fixtures, inventario+diff CSV, manifiesto, 128 tests, control positivo, pipeline/PDF, modelos de costo, pip-audit y gitleaks.

**Estado posterior:** el CI dio rojo durante el cierre porque seis archivos divergian entre mi arbol y git. Eso no fue un bug funcional: fue una divergencia de custodia que el nuevo diff detecto. Queda en el historial del PR como la prueba de que el guard funciona.

### Suite y control positivo

`python -m unittest discover -s fase0/tests -t . -v`: **128 tests, exit 0**.

`bash scripts/control_positivo_suite.sh`: **7/7 mutaciones cazadas por su test especifico**. B1 se corrigio: un exit no basta; el mutante debe compilar y el nombre del test esperado debe aparecer en la salida.

### End-to-end

El fixture contiene 24 filas, entran 23, un duplicado se colapsa, hay 2 llamadas a `ads_archive`, 1 lote, 23 analisis validos, 0 rechazos. El PDF tiene 4 paginas y 4.474 caracteres extraibles. El HTML es byte-determinista; el PDF no, porque WeasyPrint embebe timestamp. Por eso el peso exacto del PDF no se cita como dato reproducible.

## Hallazgos de la auditoria externa y correcciones

| Hallazgo | Correccion |
|---|---|
| B2, `ad_id` repetido | primera ocurrencia gana; segunda se registra como `Rechazo`. El supuesto doble conteo fue refutado: pipeline medido, distribución 20/20 |
| B3, contaminacion cruzada por delimitadores | `normalizar()` neutraliza `<<<` y `>>>` en frontera de ingesta |
| B4, cache no medido | `UsoTokens`, tabla `uso_tokens`, `Metricas.cache_hit_ratio`, umbral 0,80; aún NO MEDIDO contra proveedor real |
| B5, `max_length` inalcanzable | se retira constraint muerto; truncamiento se declara como conducta y tiene test |
| B6, plataformas en hash | `content_hash` ahora es `page_id + copy`, no plataformas |
| B7, cliente cognitivo frágil | `URLError`, timeout y respuestas deformes tipadas/degradadas; `max_tokens` explícito |
| B8, regex de URL incompleta | cobertura ampliada y alcance declarado; HTML escape sigue siendo el control de seguridad |
| A5, inventario solo en sandbox | CI corre inventario y hace diff contra CSV |
| A1/A2, informe y head incongruentes | informe es archivo, manifiesto SHA-256, sin SHA propio transcrito |

### Limitacion propia nueva, 10.10

`CAMPOS_ADS_ARCHIVE` no incluye ningún campo de formato de medio. En producción `formato` será `desconocido` casi siempre y la sección 4 del PDF será inerte. El dry-run deriva formato desde plataformas solo para demostrar el pipeline, aunque el prompt real prohíbe adivinarlo. Hay que confirmar un campo oficial o retirar esa sección.

## Rubrica

La evaluación externa vigente es **89/100**, debajo del umbral 90. La reevaluación de 94/100 es autoevaluación sobre un árbol que el revisor no vio y queda declarada como tal.

| Criterio | Externa |
|---|---:|
| Completitud | 15 |
| Ejecutabilidad | 15 |
| Seguridad | 12 |
| Testing | 12 |
| Arquitectura | 10 |
| DevOps | 9 |
| Documentación | 10 |
| Innovación | 4 |
| Proceso QA | 2 |
| **Total** | **89** |

No se recuperan puntos hasta que el revisor haga segunda pasada, pip-audit/gitleaks reporten, y exista medición de cobertura.

## Estados NO MEDIDOS

1. Ninguna llamada real a `ads_archive`.
2. Ninguna llamada real a DeepSeek.
3. Calidad semántica del modelo.
4. Review de Copilot.
5. Precio/disposición a pagar.
6. CAC/retención.
7. Corpus comercial para LatAm.
8. Residencia de datos China/Europa.
9. Umbrales exactos del tier estándar Marketing API.
10. Formato de anuncio en producción.
11. Resultados de pip-audit/gitleaks.
12. Segunda revisión externa de estas correcciones.

## Registro completo de defectos propios

1. Falta de test para fecha de inicio en hash.
2. Índice por `ad_id` produjo informes distintos en segunda corrida.
3. Contador 613 contó el intento final.
4. Veredicto de semanas-persona hardcodeado.
5. Prefijo de costo sobreestimado 12x.
6. Recibo decía 100 tests y eran 101.
7. Test prohibía llaves JSON legítimas.
8. Test `onload=` confundía HTML escapado con ataque.
9. Conteo PDF por bytes comprimidos.
10. Guard de inventario inalcanzable.
11. Informe coloquial para auditor técnico.
12. Test de inyección pasaba con `angulo` abierto por rechazo en `cta`.
13. Manifiesto autorreferente daba rojo siempre.
14. Workflow local y git diferían en 100/101 tests.
15. A1 reincidió durante su propia corrección: tres recibos para un archivo; luego workflow, config y cinco archivos más divergieron.
16. Peso PDF citado como determinista aunque WeasyPrint embebe timestamp.
17. El CI detectó seis archivos divergentes que no había ejecutado ningún instrumento.
18. El ancla del control positivo contenía una secuencia de escape que se deformaba al transportarse por JSON; siete diagnósticos manuales antes de mirar el canal.

## Reproducción

```bash
git clone https://github.com/gatehot59-star/cashgo.git
cd cashgo && git checkout titan/auditoria-cashgo
python3 -m venv .venv && . .venv/bin/activate
pip install -r fase0/requirements.txt
python3 -m fase0.fixtures.generar
python3 scripts/manifiesto.py --verificar
python3 scripts/inventario.py
diff <(python3 scripts/inventario.py --csv) evidencia/inventario.csv
python3 -m unittest discover -s fase0/tests -t . -v
python3 -m unittest fase0.tests.test_hallazgos_auditoria -v
bash scripts/control_positivo_suite.sh
python3 -m fase0.pipeline fase0/fixtures/brief_ejemplo.json --dry-run fase0/fixtures/ads_archive_sample.json --salida /tmp/aud --pdf
python3 scripts/modelo_costo_arq3.py
python3 scripts/sensibilidad_infra_y_equipo.py
```

### Verificaciones adversariales

1. Meter `inicio` en el hash: debe fallar `test_ignora_la_fecha_de_inicio`.
2. Cambiar `angulo: Angulo` a `str`: debe fallar el test por campo.
3. Quitar `html.escape`: debe fallar `TestEscapado`.
4. Romper sintaxis: inventario debe devolver exit 1.
5. Cambiar el prefijo: debe fallar su SHA.
6. Pedir US: `AlcanceComercialError` antes de red.
7. Cambiar un byte de evidencia: manifiesto exit 1.
8. Quitar neutralización de `<<<`: test B3 exit rojo.
9. Devolver `str` en Completion: errores explícitos, contrato roto.

## Veredicto

La Fase 0 está implementada, verificada contra fixtures por CI ajeno, y corregida frente a 13 de 14 hallazgos externos. Su funcionamiento contra APIs reales, calidad semántica, tasa de cache y mercado siguen **NO MEDIDOS**. Una de cuatro arquitecturas tiene implementación. El próximo movimiento correcto es obtener acceso real a Meta/DeepSeek y validar calidad/comercialización, no seguir agregando código.
