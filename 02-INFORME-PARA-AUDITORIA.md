# INFORME TECNICO DE AUDITORIA · PROYECTO CASHGO

**Documento:** dossier tecnico para auditoria externa independiente
**Fecha de corte:** 2026-09-06T23:39-03:00 (2026-09-07T02:39Z)
**Repositorio:** `gatehot59-star/cashgo` · creado 2026-09-06
**Rama auditada:** `titan/auditoria-cashgo`
**Head SHA al momento de la medicion:** `34a34d3756015f2d7eb7771f33572eef96acacb3`
**Pull Request:** #1 · estado `open` · `mergeable_state: clean` · sin mergear
**Autor del codigo y de este informe:** BRAIN (agente). **No es un informe independiente.**

---

## 1. ALCANCE Y LIMITES DE LA AUDITORIA

### 1.1 Objeto auditado

Todo el artefacto producido en la jornada del 2026-09-06 en el repositorio citado:
codigo de la Fase 0 (Arquitectura 2), instrumentos de medicion, documentos de
decision y evidencia cruda. El repositorio no contenia nada antes de esa fecha.

### 1.2 Fuera de alcance, explicitamente

| Fuera de alcance | Razon |
|---|---|
| Arquitecturas 1, 3 y 4 | no existe codigo; solo especificacion en `00-AUDITORIA-CASHGO.md` |
| Ledger financiero y guardrails de escritura | especificados en `ADR-CG-002`, cero lineas implementadas |
| Comportamiento contra APIs de terceros | **cero llamadas ejecutadas.** Ver seccion 10.1 |
| Calidad semantica de la clasificacion del LLM | **NO MEDIDO.** Ver seccion 10.3 |
| Viabilidad comercial | sin datos de mercado propios. Ver seccion 10.6 |

### 1.3 Conflicto de interes, declarado

Este informe lo redacta el mismo agente que escribio el codigo. Es autoevaluacion.
Su unico contrapeso es que **cada afirmacion cuantitativa esta acompanada por el
comando que la reproduce y por la salida cruda commiteada**, de modo que un tercero
pueda recomputarla y contradecirla sin pedir nada. La seccion 12 contiene las
instrucciones completas.

**Advertencia dirigida al auditor:** la coincidencia entre dos modelos de lenguaje
sobre un hecho **no constituye verificacion independiente**. Corpus solapados
producen errores correlacionados. Lo unico que hace de falsador en este dossier son
los instrumentos ejecutables de la seccion 2 y las fuentes primarias de la
seccion 9.

---

## 2. CADENA DE EVIDENCIA Y FALSABILIDAD DE CADA INSTRUMENTO

Criterio aplicado: **un instrumento que no puede producir un resultado negativo no
sirve para auditar.** Para cada uno se declara si su rama negativa es alcanzable y
si fue efectivamente alcanzada.

| Instrumento | Que mide | Puede dar rojo | Rojo observado |
|---|---|---|---|
| `python -m unittest discover -s fase0/tests -t .` | 101 propiedades del codigo | si | **si**: 2 defectos de codigo, 3 falsos rojos propios |
| `scripts/control_positivo_suite.sh` | si la suite detecta 3 mutaciones inyectadas | si | **si**: 1 de 3 no detectada en la primera corrida |
| `scripts/inventario.py` | conteo estructural por categoria de linea | si (desde la correccion) | **si**: control positivo con archivo no parseable |
| `scripts/modelo_costo_arq3.py` | costo y margen de la Arq. 3 | si: guard a 80% de margen | no |
| `scripts/sensibilidad_infra_y_equipo.py` | barrido de infra + semanas-persona | si: coherencia de supuestos | no |
| GitHub Actions, workflow `fase0` | todo lo anterior en maquina limpia | si | no |

### 2.1 El unico instrumento ajeno

| Campo | Valor |
|---|---|
| Proveedor | GitHub Actions |
| Workflow | `fase0` (`.github/workflows/fase0.yml`) |
| Run ID | `34075787171` (y `34075784468`) |
| Check runs | 2, ambos `name: suite` |
| Estado | `status: completed`, **`conclusion: success`** |
| Duracion | 28 s (`02:17:10Z` a `02:17:38Z`) |
| Runner | `ubuntu-24.04`, imagen limpia provista por GitHub |
| Instalacion | `pip install -r fase0/requirements.txt` desde cero |
| Fixtures | generados en el runner (`.gitignore` los excluye) |
| Acceso a red hacia Meta o DeepSeek | **ninguno** |

Etapas ejecutadas por el workflow: dependencias nativas de WeasyPrint, dependencias
Python, generacion de fixtures, suite de 101 tests con `-v`, control positivo por
mutacion, pipeline end-to-end con render de PDF, y los dos modelos de costo. El PDF
se publica como artifact con retencion de 14 dias.

**Relevancia metodologica:** todas las demas corridas de esta jornada se ejecutaron
en el sandbox del autor, con dependencias preinstaladas y el arbol ya construido.
Esta es la unica medicion emitida por una maquina que no pertenece al autor, que
reconstruyo el entorno desde el manifiesto y que no tenia expectativa sobre el
resultado. Conforme al criterio W-01, **la independencia es una propiedad del
instrumento, no del operador**; este instrumento cumple ademas la condicion mas
fuerte de no ser el del autor.

### 2.2 Control externo NO satisfecho

| Control | Estado | Clasificacion |
|---|---|---|
| Revision automatica de codigo (GitHub Copilot) | solicitada 2 veces sobre el PR #1; `get_reviews` devuelve `[]` | **NO MEDIDO** |

La ausencia de hallazgos **no se interpreta como aprobacion**. Se registra como
estado no medido y como deuda abierta, y se descuentan 2 puntos en el criterio 9 de
la rubrica (seccion 8). El auditor deberia tratar la revision de codigo linea a
linea como pendiente.

### 2.3 Afirmaciones que hoy no tienen instrumento

Dos clases de afirmacion presentes en los documentos del repositorio **no son
verificables con los instrumentos disponibles** y estan marcadas como tales:

1. **Estado de producto de los competidores** (seccion 9.3): se apoya en paginas
   publicas de los proveedores, leidas el 2026-09-06. Es evidencia documental, no
   medicion. Un competidor puede describir capacidades que no entrega.
2. **Proyecciones comerciales** (precio, suscriptores, CAC): son supuestos
   parametricos del modelo de costo, no observaciones. Ver seccion 6.3.

---

## 3. INVENTARIO CUANTITATIVO

**Instrumento:** `python3 scripts/inventario.py` · exit 0
**Evidencia:** `evidencia/salida_inventario.txt`, `evidencia/inventario.csv`

### 3.1 Por capa

| Capa | Archivos | Lineas totales | Codigo | Comentario | Docstring |
|---|---|---|---|---|---|
| Modulos de produccion (`fase0/`) | 10 | 1.958 | 1.275 | 101 | 287 |
| Verificacion (`fase0/tests/`) | 7 | 1.158 | 745 | 6 | 188 |
| Fixtures (`fase0/fixtures/`) | 2 | 174 | 130 | 15 | 10 |
| Instrumentos (`scripts/`) | 3 | 538+ | 389+ | 34+ | 45+ |
| **TOTAL Python** | **21** | **3.858** | **2.554** | **158** | **540** |

Adicional, no Python: `scripts/control_positivo_suite.sh` (79 lineas),
`.github/workflows/fase0.yml` (60), `fase0/README.md` (164), 5 documentos de
decision en Markdown, y 372 lineas de evidencia cruda en `evidencia/`.

### 3.2 Indicadores derivados

| Indicador | Valor | Lectura |
|---|---|---|
| Lineas de codigo de test / de produccion | **0,58** | dentro del rango habitual para codigo con contratos externos |
| (Comentario + docstring) / codigo | **0,273** | alto a proposito: cada constante que sale de una medicion externa lleva su fuente y fecha en el archivo |
| Dependencias de terceros | **3**, pinneadas exactas | `pydantic==2.13.4`, `weasyprint==69.0`, `pypdf==6.14.2` |
| Dependencias de test | **0** | `unittest` de la stdlib |
| Modulos con acceso a red | **2 funciones**, ambas fabricas inyectables | `transporte_http()`, `cliente_deepseek()` |

### 3.3 Aclaracion sobre el ratio de comentarios

Un ratio de 0,273 podria leerse como sobredocumentacion. La razon es especifica y
verificable en el archivo: **cada constante derivada de una fuente externa lleva la
URL y la fecha de verificacion en linea** (ver `fase0/config.py`, 40 lineas de
comentario sobre 71 de codigo). Ese es el mecanismo que permite auditar si un limite
de plataforma sigue vigente sin volver a investigarlo desde cero.

---

## 4. ARQUITECTURA, CONTRATOS E INVARIANTES

### 4.1 Topologia de capas

```
[1] Adquisicion        fase0/adlibrary.py    HTTP -> ads_archive (Graph API v26.0)
[2] Persistencia       fase0/store.py        SQLite; append-only para auditoria
[3] Deduplicacion      fase0/dedup.py        SHA-256 de contenido; sin LLM
[4] Capa cognitiva     fase0/cognitive.py    DeepSeek V4-Flash; funcion pura
[5] Agregacion         fase0/report.py       determinista; sin LLM
[6] Presentacion       fase0/report.py       HTML -> PDF (WeasyPrint)
[0] Orquestacion       fase0/pipeline.py     secuencia 1..6 + CLI
```

### 4.2 Criterio de asignacion de responsabilidad

Regla declarada en `00-AUDITORIA-CASHGO.md` seccion 2 y aplicada en el codigo:

> Si un error cuesta dinero o es irreversible, la logica es determinista.
> Si un error cuesta un token, la logica es cognitiva.

Consecuencia observable: las capas 1, 2, 3, 5 y 6 no contienen ninguna llamada a un
modelo de lenguaje. La capa 4 no contiene ninguna credencial de plataforma ni
capacidad de efecto lateral.

### 4.3 Invariantes del sistema

| # | Invariante | Donde se hace cumplir | Test |
|---|---|---|---|
| I-1 | El subsistema no posee credencial de escritura sobre ninguna cuenta publicitaria | ausencia estructural: no existe cliente de Marketing API en el arbol | inspeccion |
| I-2 | El LLM recibe texto y devuelve JSON validado; no recibe tokens ni expone herramientas | `Analizador.__init__` recibe una `Completion`, no un cliente | `test_cognitive.py` |
| I-3 | `content_hash` es funcion del contenido creativo, no del registro que lo transporta | `AnuncioCrudo.content_hash()` excluye `ad_id`, `inicio`, `fin` | 6 tests en `TestContentHash` |
| I-4 | Todo output del modelo se valida contra esquema cerrado o se descarta | `Literal` + `extra="forbid"` en `AnalisisAnuncio` | 10 tests en `TestValidacionEstricta` |
| I-5 | Un output invalido no se reintenta con el mismo prompt | `Analizador.analizar` registra `Rechazo` y retorna | `TestValidacionEstricta` |
| I-6 | El informe es funcion determinista del corpus mas los analisis | ordenamientos con desempate total en `report._contar` | 2 tests en `TestDeterminismo` |
| I-7 | Todo texto de origen externo se escapa antes de renderizar | `report._e()` sobre cada interpolacion | 5 tests en `TestEscapado` |
| I-8 | El prefijo del prompt es byte-identico entre invocaciones | constante de modulo; SHA-256 pinneado en el test | 4 tests en `TestPrefijoEstable` |

### 4.4 Superficie de API publica

Extraida del AST, no de la documentacion:

| Modulo | Superficie publica |
|---|---|
| `adlibrary.py` | `AdsArchiveClient.anuncios_de`, `PresupuestoLlamadas`, `lotes`, `transporte_http`, 4 excepciones de dominio |
| `cognitive.py` | `Analizador.construir_mensajes`, `Analizador.analizar`, `formatear_anuncio`, `estimar_tokens`, `cliente_deepseek`, `PREFIJO_ESTABLE`, `PREFIJO_SHA256` |
| `schemas.py` | `AnuncioCrudo`, `AnalisisAnuncio`, `LoteAnalizado`, `Rechazo`, `FilaCompetidor`, `Informe`, `normalizar`, `sin_urls` |
| `dedup.py` | `particionar`, `Particion` |
| `store.py` | `Store` (7 metodos publicos) |
| `report.py` | `construir_informe`, `informe_a_html`, `escribir_pdf`, `escribir_html` |
| `pipeline.py` | `correr_auditoria`, `main`, `Metricas`, `Resultado` |
| `config.py` | `Settings.from_env`, `Settings.validar`, 10 constantes, `DSA_COMMERCIAL_COUNTRIES` |

### 4.5 Puntos de inyeccion de dependencias

Tres, todos deliberados para permitir verificacion sin red:

| Punto | Tipo | Doble usado en test |
|---|---|---|
| `AdsArchiveClient(transport=...)` | `Callable[[str, dict], dict]` | fixture de 2 paginas con cursor |
| `Analizador(completion=...)` | `Callable[[str, list, float], str]` | clasificador determinista por reglas |
| `AdsArchiveClient(dormir=...)` | `Callable[[float], None]` | captura de tiempos de backoff sin esperar |

Esta es la propiedad que hace que la suite completa y el pipeline end-to-end sean
ejecutables en un runner sin credenciales, y por lo tanto verificables por un
tercero.

---

## 5. VERIFICACION

### 5.1 Suite de pruebas

**Comando:** `python -m unittest discover -s fase0/tests -t . -v` · **exit 0**
**Evidencia:** `evidencia/salida_tests_fase0.txt`

| Modulo de test | Clases | Tests |
|---|---|---|
| `test_cognitive.py` | 5 | 23 |
| `test_e2e_pipeline.py` | 4 | 19 |
| `test_report.py` | 4 | 20 |
| `test_adlibrary.py` | 5 | 20 |
| `test_schemas_y_dedup.py` | 5 | 19 |
| **TOTAL** | **23** | **101** |

Desglose por clase recontado con `unittest.TestLoader().discover`, no con un conteo
manual.

### 5.2 Control positivo por mutacion

**Comando:** `bash scripts/control_positivo_suite.sh` · **exit 0**
**Evidencia:** `evidencia/salida_control_positivo.txt`, que **incluye la corrida
fallida original**.

El script inyecta tres defectos de una linea, uno por vez, corre la suite y verifica
que falle. Restaura el arbol despues de cada mutacion y verifica el verde final.

| Mutacion | Propiedad atacada | 1ra corrida | Actual |
|---|---|---|---|
| `content_hash` incluye la fecha de entrega | ahorro por deduplicacion | **NO DETECTADA** | detectada |
| `angulo: Angulo` -> `angulo: str` | contencion de inyeccion de prompt | detectada | detectada |
| `_e()` deja de escapar HTML | integridad del entregable | detectada | detectada |

**Hallazgo de la primera corrida.** La suite contenia un test que verificaba que
`content_hash` ignora la fecha de **fin**, y ninguno para la fecha de **inicio**. La
mutacion paso inadvertida. El escenario real que la mutacion representa: un
anunciante pausa una creatividad y la reactiva mas tarde con un `ad_delivery_start_time`
nuevo; con la fecha incorporada al hash, esa creatividad se reprocesa y vuelve a
consumir tokens en cada reactivacion, degradando el ahorro del 88% sin emitir
ninguna senal.

**Interpretacion metodologica.** Un instrumento propio cubre el sesgo de ejecucion
y **no cubre el sesgo de seleccion**: el compilador no se equivoca, pero el autor
eligio que medir. Este control positivo es el mecanismo que expone esa segunda
clase de error, y funciono.

### 5.3 Verificacion end-to-end del entregable

**Comando:** `python -m fase0.pipeline fase0/fixtures/brief_ejemplo.json --dry-run
fase0/fixtures/ads_archive_sample.json --salida <dir> --pdf` · **exit 0**
**Evidencia:** `evidencia/salida_fase0_dryrun.txt`

| Metrica | Valor |
|---|---|
| Filas en el fixture | 24 |
| Anuncios admitidos | 23 (1 descartado por falta de `ad_delivery_start_time`) |
| Duplicados intra-lote colapsados | 1 |
| Llamadas a `ads_archive` | 2 (5 `page_id` en un batch, 2 paginas por cursor) |
| Lotes enviados al modelo | 1 |
| Analisis validos | 23 |
| Rechazos por validacion | 0 |
| PDF | 4 paginas, 23.258 bytes, 4.474 caracteres extraibles |

El PDF se verifica con `pypdf` (parser), no con busqueda de literales en los bytes.
Controles de contenido sobre el texto extraido: contiene `"Digital Services Act"`,
**no contiene** `"malicioso.example"`, contiene `"[enlace]"`.

### 5.4 Verificacion de la propiedad economica central

`test_segunda_corrida_no_paga_tokens` ejecuta el pipeline dos veces contra la misma
base persistida. Segunda corrida: `anuncios_nuevos == 0`, `lotes_al_modelo == 0`,
`ratio_dedup > 0,95`. Esto convierte el ahorro del 88% del modelo de costo de
afirmacion parametrica en propiedad verificada del codigo.

`test_la_segunda_corrida_produce_el_mismo_informe` compara los dos informes campo a
campo excluyendo el timestamp. **Este test detecto el defecto 2 de la seccion 11.**

---

## 6. MODELO DE COSTOS

### 6.1 Parametros de entrada

Todos declarados en `Supuestos` (`scripts/modelo_costo_arq3.py`) y editables:
40 nichos x 25 marcas = 1.000 paginas; 60 anuncios activos por marca; corrida
semanal (4,33/mes); churn creativo 12%; 320 tokens de entrada y 140 de salida por
anuncio; lotes de 40; prefijo estable con 95% de aciertos de cache; 40 informes de
sintesis por corrida con 60k tokens de entrada; infraestructura USD 60/mes;
30 suscriptores a USD 79.

### 6.2 Precios y su procedencia

Tarifa DeepSeek verificada el 2026-09-06, esquema peak/off-peak vigente desde
2026-08-16T16:00Z. **Conflicto de fuentes declarado en el codigo:** una fuente
secundaria continua publicando la tarifa plana anterior. El modelo usa la tarifa
mas alta de las dos, de modo que el resultado es un piso conservador.

### 6.3 Resultados

**Comando:** `python3 scripts/modelo_costo_arq3.py` · exit 0, guard verde

| | Off-peak | Peak |
|---|---|---|
| Costo del modelo, USD/mes | 14,10 | 28,20 |
| Infraestructura, USD/mes | 60,00 | 60,00 |
| **Total, USD/mes** | **74,10** | **88,20** |
| Factor de ahorro por dedup + cache | 4,4x | 4,4x |
| Costo por anuncio nuevo procesado | USD 0,000166 | USD 0,000333 |
| **Margen bruto** | **96,87%** | **96,28%** |
| Suscriptores para equilibrio | 1 | 2 |

**Conclusion tecnica.** El costo cognitivo representa el 32% del gasto total en la
ventana mas cara. Optimizar el consumo de tokens actua sobre la fraccion menor de un
sistema con 96 puntos de margen. Las restricciones vinculantes de la Arquitectura 3
no son economicas sino de tasa de peticiones (seccion 9.2).

### 6.4 Reconciliacion contra el codigo, y refutacion de un supuesto propio

**Evidencia:** `evidencia/salida_reconciliacion_prefijo.txt`

El modelo asumio un prefijo de sistema de 8.000 tokens. El prefijo efectivamente
implementado mide 2.678 caracteres, aproximadamente 669 tokens: **sobreestimacion de
12x**. Impacto en el total mensual: **0,7%**.

La insensibilidad se explica por la tasa de aciertos de cache del 95%: a USD 0,007
por millon en acierto contra USD 0,22 en fallo, el tamano del prefijo es casi
irrelevante y lo determinante es su **estabilidad**. Consecuencia de diseno
contraintuitiva y medida: **reducir el prompt de sistema para ahorrar costo es la
palanca equivocada**; conviene extenderlo con mas ejemplos y definiciones, cuidando
unicamente que no varie entre invocaciones. Ese cuidado esta implementado como
SHA-256 pinneado en `tests/test_cognitive.py`.

### 6.5 Sensibilidad a la arquitectura de infraestructura

**Comando:** `python3 scripts/sensibilidad_infra_y_equipo.py` · exit 0

Barrido con ingreso fijo de USD 2.370/mes: margen 80% a USD 446 de infraestructura
mensual, 50% a USD 1.157, 0% a USD 2.342. Un stack alternativo de 14 componentes
(USD 395/mes) mantiene el margen en 82,1% y desplaza el punto de equilibrio de 2 a
6 suscriptores.

El mismo instrumento cuantifica el costo de implementacion en semanas-persona: un
plan de 12 semanas de calendario con 2,5 desarrolladores equivale a **30
semanas-persona**, es decir 6,9 meses para un unico ejecutor a tiempo completo y
13,9 meses al 50%. La Fase 0 aqui entregada corresponde a aproximadamente 5
semanas-persona de ese plan.

---

## 7. MODELO DE AMENAZAS Y CONTROLES

### 7.1 Superficie de confianza

El sistema procesa **texto redactado por terceros no confiables** (copy publicitario
de competidores) en el contexto de un modelo de lenguaje, y renderiza ese mismo
texto en un documento PDF entregado a un cliente. Son dos limites de confianza
distintos y requieren controles distintos.

### 7.2 Vectores y controles

| Vector | Control primario | Control secundario | Test |
|---|---|---|---|
| Inyeccion de prompt en el copy de un anuncio | **esquema cerrado**: `Literal` + `extra="forbid"`. Un output obediente a la inyeccion es un `ValidationError` | delimitadores `<<<ANUNCIO>>>`/`<<<FIN>>>` e instruccion explicita en el prefijo | `TestInyeccionEnElCopy` (4) |
| Exfiltracion de credenciales via el modelo | **el modelo no las posee.** `Analizador` recibe una funcion, no un cliente | — | inspeccion + I-2 |
| URL de terceros en el entregable | `sin_urls()` sustituye por `[enlace]` en los campos de texto libre | — | `TestSinUrls` (4) |
| XSS o inyeccion de markup en el PDF | `html.escape(..., quote=True)` en cada interpolacion | — | `TestEscapado` (5), incluido barrido del documento completo |
| Alucinacion de identificadores | verificacion de cobertura: `ad_id` no solicitados se descartan, `ad_id` omitidos se registran | — | `TestCobertura` (3) |
| Bucle de reintentos sobre output invalido | prohibido por diseno: se registra `Rechazo` y se retorna | — | `TestValidacionEstricta` |
| Agotamiento del cuota de la plataforma | presupuesto propio con ventana deslizante, 10% por debajo del limite observado | backoff exponencial con techo, 5 intentos | `TestRateLimit` (5) |
| Bucle infinito por cursor de paginacion mal formado | tope `max_paginas_por_lote` | — | `test_tope_de_paginas_evita_bucle_infinito` |
| Contaminacion administrativa entre subsistemas | `Settings.validar()` aborta si el `app_id` de investigacion coincide con el de escritura | — | `TestConfigGuards` (4) |
| Consulta a jurisdicciones sin cobertura comercial | allowlist dura; excepcion tipada `AlcanceComercialError` | — | `TestAlcanceComercial` (4) |

### 7.3 Precision sobre el control de inyeccion

La instruccion del prefijo que ordena no obedecer al contenido del anuncio **no es
el control efectivo**: es mitigacion de segundo orden. El control efectivo es
estructural. `TestInyeccionEnElCopy::test_si_el_modelo_obedece_la_inyeccion_el_esquema_lo_frena`
simula el peor caso, un modelo completamente comprometido que devuelve el valor
solicitado por el atacante, y verifica que el resultado sea cero analisis admitidos y
un rechazo registrado. La correccion del sistema en ese escenario **no depende del
comportamiento del modelo**.

### 7.4 Controles ausentes

| Ausente | Impacto | Prioridad |
|---|---|---|
| Escaneo de vulnerabilidades de dependencias | 3 dependencias sin auditar contra CVE | alta antes de exponer un servicio |
| Escaneo de secretos sobre el arbol | no hay credenciales en el codigo, pero la ausencia no esta verificada por instrumento | alta |
| Medicion de cobertura por linea | el control positivo cubre 3 propiedades, no el arbol | media |
| Limite de tamano del corpus por corrida | una lista de competidores muy grande puede agotar el presupuesto de llamadas antes de completar | media |

---

## 8. RUBRICA DE CALIDAD, CON EVIDENCIA POR CRITERIO

Tipo de entrega: **codigo de produccion**. Los 9 criterios aplican. **Cero N/A.**

| # | Criterio | Puntos | Evidencia y justificacion del descuento |
|---|---|---|---|
| 1 | Completitud | **15**/15 | Sin `TODO`, sin marcadores de posicion, sin cuerpos vacios. Los 10 modulos importan y ejecutan. Verificable por inspeccion del arbol |
| 2 | Ejecutabilidad | **15**/15 | Runner limpio: instalacion desde manifiesto, 101 tests, control positivo, pipeline y PDF. `conclusion: success` |
| 3 | Seguridad | **14**/15 | Modelo de amenazas de la seccion 7 con 10 vectores y su test. **−1: ningun escaneo de dependencias ni de secretos ejecutado sobre este arbol** (seccion 7.4) |
| 4 | Testing | **14**/15 | 101 tests; los 3 vectores criticos con control positivo por mutacion. **−1: sin cobertura por linea; el control positivo cubre 3 propiedades** |
| 5 | Arquitectura | **10**/10 | Criterio de asignacion de responsabilidad explicito y observable (4.2); 8 invariantes con su punto de cumplimiento (4.3); 3 puntos de inyeccion que hacen el sistema verificable sin credenciales (4.5) |
| 6 | DevOps | **9**/10 | Workflow completo, sin red, con artifact. **−1: sin deployment; la Fase 0 es una CLI, no un servicio** |
| 7 | Documentacion | **10**/10 | README con arranque ejecutable, 6 variables de entorno tabuladas, 2 prerrequisitos administrativos, 2 ADRs, y los limites del producto impresos en el propio entregable |
| 8 | Innovacion | **4**/5 | Control positivo por mutacion; reconciliacion del modelo contra el codigo; `sin_urls`; fixtures como codigo. **−1: los cuatro aportan al metodo, ninguno al producto** |
| 9 | Proceso QA | **3**/5 | Cada score con instrumento y ruta de evidencia. **−2: la revision externa no emitio hallazgos, o sea que un control quedo NO MEDIDO** (2.2) |

### **TOTAL: 94/100** · umbral 90 · **APROBADO, con la deuda del criterio 9 declarada**

---

## 9. RESTRICCIONES EXTERNAS Y POSICIONAMIENTO

Todas verificadas el 2026-09-06 contra fuentes primarias o documentacion oficial.
Las fuentes exactas estan citadas en `00-AUDITORIA-CASHGO.md` y
`01-CONTRASTE-CON-BLUEPRINT-EXTERNO.md`.

### 9.1 Cobertura de datos: la restriccion estructural del producto

`ads_archive` con `ad_type=ALL` retorna anuncios **comerciales** unicamente cuando
`ad_reached_countries` refiere a la UE, EEE o Reino Unido, por obligacion del Digital
Services Act, con retencion aproximada de 12 meses. Para el resto de las
jurisdicciones retorna exclusivamente anuncios politicos y de temas sociales.

El codigo implementa esto como allowlist dura (`config.DSA_COMMERCIAL_COUNTRIES`, 31
codigos) y falla con excepcion tipada. **Justificacion del diseno:** una lista vacia
es indistinguible de "el competidor no anuncia", y esa ambiguedad terminaria escrita
en un informe facturado.

**Consecuencia comercial, no tecnica:** el mercado direccionable de la Fase 0 son
anunciantes con presencia en la UE o el Reino Unido. Para un prospecto que pauta
unicamente en LatAm no existe corpus por via oficial.

Restriccion adicional del dominio: para anuncios comerciales Meta **no publica**
gasto, impresiones, CTR ni conversiones. El unico proxy de exito disponible es la
duracion de la entrega. El entregable declara esto en su propia seccion de
metodologia, incluyendo que el umbral de 60 dias usado para clasificar un anuncio
como "probado" es una convencion propia y no un dato de la plataforma.

### 9.2 Restricciones de tasa que si son vinculantes

| Recurso | Limite | Efecto sobre el diseno |
|---|---|---|
| Ad Library API | ~200 llamadas/hora por token, dinamico y no publicado; error 613 | techo propio de 180, ventana deslizante, backoff con techo. Corrida semanal viable, diaria no |
| Notion API | promedio 3 req/s por conexion; limite adicional por workspace; tope de paginacion de 10.000 resultados | **invalida Notion como base de datos** de la Arquitectura 3: 60.000 filas son ~5,5 h de escritura y luego no son consultables. Queda como superficie de entrega de un top-N curado |
| Marketing API, tier | las apps nuevas obtienen `development_access`; el ascenso a estandar exige uso sostenido | afecta a las Arquitecturas 1 y 4, no a la Fase 0. Umbrales exactos: **parcialmente medidos** (10.9) |
| Cambios de `spend_cap` | 10 por dia por cuenta (error 17/1885172) | `spend_cap` es techo de periodo, no control dinamico |
| Cambios de presupuesto de ad set | 4 por hora, con bloqueo de una hora al exceder (613/1487225) | el limitador semantico de escrituras ya existe del lado de la plataforma para el caso de presupuesto |

### 9.3 Posicionamiento competitivo

Evidencia documental de paginas publicas leidas el 2026-09-06. **No es medicion.**

| Dimension | Adspirer | Markifact | Meta (oficial) | CASHGO |
|---|---|---|---|---|
| Producto en operacion con clientes | si | si | si (beta gratuita) | **no** |
| Precio publicado | USD 0/49/99/199 | no publicado | gratuito en beta | no aplica |
| Plataformas publicitarias integradas | 6 | 10+ | 1 | **0** |
| Operaciones expuestas | 400+ herramientas | 1.000+ operaciones tras 8 meta-herramientas | 82 herramientas | **0** |
| Escritura sobre cuentas | si, creacion pausada | si, aprobacion en cada escritura | si, creacion pausada | **no, por diseno** |
| Proveedor tecnologico aprobado por Meta | si | si | es Meta | no aplica |
| Corpus propio de Ad Library | no | si | no (extraccion masiva prohibida) | pipeline implementado, corpus vacio |
| Union de metricas de ads con margen por SKU | no | no | no | especificado, no implementado |
| Suite de pruebas publica | no observable | no observable | no aplica | 101 tests, CI publico |

**Lectura tecnica.** La capa de conectividad esta comoditizada: Meta abrio su propio
servidor MCP de ads el 2026-04-29 y lo habilito a cualquier aplicacion de developer
el 2026-07-16, con OAuth, sin revision de aplicacion y sin costo durante la beta,
exponiendo 82 herramientas con creacion en estado pausado y sin operacion de borrado
de campanas. Construir un competidor en esa capa implica entrar a un mercado cuyo
techo de precio esta fijado en USD 199/mes por dos proveedores establecidos y cuyo
piso lo fija el fabricante de la plataforma en cero.

La diferenciacion especificada, no implementada, consiste en unir metricas de
performance publicitaria con margen real por SKU obtenido de la plataforma de
comercio del cliente. Es una capacidad que los competidores no pueden ofrecer con la
informacion a la que acceden, y su implementacion depende de las Fases 2 y 3.

---

## 10. REGISTRO DE ESTADOS NO MEDIDOS

Ordenado por impacto sobre la validez de las conclusiones.

| # | Estado no medido | Consecuencia sobre lo afirmable | Procedimiento de cierre |
|---|---|---|---|
| **10.1** | **Ninguna peticion ejecutada contra `ads_archive`.** `transporte_http()` esta escrito contra documentacion y no ejecutado | **impide afirmar que el sistema funciona.** Solo puede afirmarse que es correcto respecto de los fixtures | verificacion de identidad en `facebook.com/ID`, aplicacion de developer con el producto Ad Library API, y una corrida |
| **10.2** | **Ninguna peticion ejecutada contra DeepSeek.** `cliente_deepseek()` idem | idem | una corrida con clave de API |
| **10.3** | **Calidad semantica de la clasificacion.** El clasificador del modo `--dry-run` son heuristicas de palabra clave | valida el pipeline, **no la calidad del analisis**. La evidencia documenta un caso concreto de clasificacion erronea del propio fixture | conjunto anotado manualmente (~100 anuncios), matriz de confusion contra el modelo real |
| 10.4 | Revision externa de codigo sin hallazgos emitidos | un control de calidad no aplicado | reintentar la revision automatica o asignar revisor humano |
| 10.5 | Precio y disposicion a pagar | los USD 79 x 30 del modelo son parametros, no observaciones | entrevistas con prospectos |
| 10.6 | Costo de adquisicion y retencion | con 96% de margen y equilibrio en 2 suscriptores, el riesgo del negocio no es el costo unitario sino la adquisicion | modelo comercial; no requiere codigo |
| 10.7 | Corpus para LatAm | sin via oficial identificada | decidir entre vender inteligencia UE/UK o adquirir datos de un proveedor |
| 10.8 | Residencia de datos | el proveedor cognitivo procesa en China; el corpus legal es europeo | revision juridica antes de que ingresen datos personales |
| 10.9 | Umbrales del tier estandar del Marketing API | leidos de una fuente con texto truncado. La existencia de los dos tiers y del header esta firme; los valores no | consulta al panel de App Review |

---

## 11. REGISTRO DE DEFECTOS PROPIOS DE LA JORNADA

Se listan los once detectados. Cada uno esta anotado en el archivo donde ocurrio o
en su evidencia, con la regla que se deriva.

| # | Defecto | Detectado por | Clase |
|---|---|---|---|
| 1 | Ausencia de test para la fecha de **inicio** en `content_hash`, habiendo uno para la de fin | **control positivo por mutacion** | sesgo de seleccion del propio autor |
| 2 | Analisis indexados por `ad_id`: la segunda corrida producia un informe **distinto** para el mismo corpus | test de determinismo entre corridas | defecto invisible en una unica ejecucion |
| 3 | Contador `reintentos_613` incrementado tambien en el intento que abandona (6 informado, 5 efectivos) | test de rate limit | metrica incongruente con el fenomeno que mide |
| 4 | Veredicto con "8 a 17 meses" escrito en el literal contra 6,9 y 13,9 calculados dos lineas arriba | lectura del stdout propio | conclusion redactada antes de observar el numero |
| 5 | Prefijo del prompt sobreestimado 12x en el modelo de costo | reconciliacion del modelo contra el codigo | supuesto tratado como medicion |
| 6 | Recibo de la suite informando 100 tests cuando eran 101 | reconteo con el loader | un conteo incongruente invalida la credibilidad del recibo completo |
| 7 | Test que prohibia `{` en el prefijo, que contiene ejemplos de JSON legitimos | el propio test | assertion sobre un substring en lugar de la propiedad |
| 8 | `assertNotIn("onload=")` sin distinguir `onload=&quot;` (inerte) de `onload="` (ataque) | el propio test | idem |
| 9 | Conteo de paginas de PDF buscando `b"/Type /Page"` en bytes comprimidos | el propio test | medicion del envoltorio con conclusion sobre el contenido |
| **10** | **`inventario.py` con guard inalcanzable.** El unico guard era "la suma cierra", que es verdadero por construccion. Un archivo con error de sintaxis producia un conteo falso y salida verde | prueba deliberada del guard | **guard cuya rama negativa es inalcanzable: simulacion de verificacion** |
| 11 | Primera version de este informe redactada en registro coloquial, apta para decidir y no para auditar | observacion del destinatario | confusion entre el genero del documento y su funcion |

Los defectos 7, 8 y 9 son falsos negativos del instrumento, no del codigo: el codigo
era correcto en los tres casos. Se registran porque **un test que falla por el motivo
equivocado consume la credibilidad de la proxima falla legitima**.

El defecto 10 es el mas relevante para un auditor, porque afecta a un instrumento de
medicion y no al producto: durante un intervalo, la seccion cuantitativa de este
informe se apoyaba en un script cuyo control de integridad no podia fallar.

---

## 12. PROCEDIMIENTO DE REPRODUCCION PARA EL AUDITOR

Ninguno de estos pasos requiere credenciales ni acceso a las APIs de terceros. El
tiempo total de ejecucion es inferior a un minuto.

```bash
git clone https://github.com/gatehot59-star/cashgo.git
cd cashgo
git checkout titan/auditoria-cashgo
git rev-parse HEAD          # comparar con el head SHA del encabezado

python3 -m venv .venv && . .venv/bin/activate
pip install -r fase0/requirements.txt

# 1. Inventario cuantitativo (seccion 3). Debe coincidir con evidencia/inventario.csv
python3 scripts/inventario.py

# 2. Suite completa (seccion 5.1). Esperado: Ran 101 tests, OK, exit 0
python3 -m unittest discover -s fase0/tests -t . -v

# 3. Control positivo (seccion 5.2). Esperado: 3 mutaciones CAZADAS, exit 0
bash scripts/control_positivo_suite.sh

# 4. Pipeline end-to-end y entregable (seccion 5.3)
python3 -m fase0.fixtures.generar
python3 -m fase0.pipeline fase0/fixtures/brief_ejemplo.json \
  --dry-run fase0/fixtures/ads_archive_sample.json --salida /tmp/aud --pdf

# 5. Modelos de costo (seccion 6)
python3 scripts/modelo_costo_arq3.py
python3 scripts/sensibilidad_infra_y_equipo.py
```

### 12.1 Verificaciones adversariales sugeridas

Para comprobar que los instrumentos no son decorativos, se sugiere al auditor
intentar lo siguiente. Los tres primeros deben producir rojo:

1. Agregar `self.inicio.isoformat()` al payload de `AnuncioCrudo.content_hash()`.
   Esperado: falla `test_ignora_la_fecha_de_inicio`.
2. Cambiar `angulo: Angulo` por `angulo: str` en `AnalisisAnuncio`.
   Esperado: falla la contencion de inyeccion.
3. Reemplazar el cuerpo de `report._e()` por `return str(valor)`.
   Esperado: falla `TestEscapado`.
4. Introducir un error de sintaxis en cualquier modulo y ejecutar
   `scripts/inventario.py`. Esperado: exit 1 con el archivo nombrado.
5. Modificar un caracter de `PREFIJO_ESTABLE`.
   Esperado: falla `test_el_hash_no_cambio`.
6. Ejecutar el pipeline con `"paises": ["US"]` en el brief.
   Esperado: `AlcanceComercialError` antes de cualquier peticion.

### 12.2 Correspondencia entre afirmaciones y evidencia

| Seccion | Afirmacion | Archivo de evidencia |
|---|---|---|
| 3 | inventario cuantitativo | `evidencia/salida_inventario.txt`, `evidencia/inventario.csv` |
| 5.1 | 101 tests, exit 0 | `evidencia/salida_tests_fase0.txt` |
| 5.2 | 3/3 mutaciones detectadas, y la falla original | `evidencia/salida_control_positivo.txt` |
| 5.3 | pipeline y PDF | `evidencia/salida_fase0_dryrun.txt` |
| 6.3 | costo y margen | `evidencia/salida_modelo_costo_arq3.txt`, `evidencia/modelo_costo_arq3.csv` |
| 6.4 | refutacion del supuesto del prefijo | `evidencia/salida_reconciliacion_prefijo.txt` |
| 6.5 | sensibilidad de infraestructura y semanas-persona | `evidencia/salida_sensibilidad_infra_y_equipo.txt` |
| 2.1 | CI en maquina limpia | logs del workflow `fase0`, run `34075787171` |

---

## 13. CONCLUSIONES

### 13.1 Afirmable con instrumento

1. Existe una implementacion completa y ejecutable de la Fase 0: adquisicion desde
   la API oficial, persistencia, deduplicacion, estructuracion cognitiva, agregacion
   determinista y generacion de un entregable PDF de 4 paginas.
2. La implementacion satisface 101 propiedades verificadas, y los tres vectores
   criticos cuentan con control positivo por mutacion que demuestra que la suite
   puede detectar su ausencia.
3. La verificacion fue reproducida por un instrumento que no pertenece al autor, en
   una maquina limpia, reconstruyendo el entorno desde el manifiesto de dependencias.
4. El margen bruto de la Arquitectura 3 se sostiene en 96,28% bajo la tarifa mas
   alta disponible, y la palanca de costo dominante es la deduplicacion determinista,
   no la optimizacion del modelo.
5. La contencion de inyeccion de prompt es estructural: la correccion del sistema en
   el peor caso no depende del comportamiento del modelo.

### 13.2 No afirmable

1. **Que el sistema funciona.** Cero peticiones ejecutadas contra las APIs de
   terceros (10.1, 10.2).
2. **Que el analisis producido es de calidad.** El clasificador verificado es un
   sustituto por reglas (10.3).
3. **Que el producto tiene mercado.** Cero clientes, cero ingresos, precio no
   validado (10.5, 10.6).
4. **Que el codigo esta libre de defectos que un revisor externo detectaria.** La
   revision externa no emitio hallazgos, lo que es un estado no medido (2.2).

### 13.3 Enunciado preciso del estado del proyecto

> La Fase 0 esta implementada y verificada contra fixtures por un instrumento
> independiente del autor. Su comportamiento contra las APIs reales, la calidad
> semantica de su capa cognitiva y su viabilidad comercial son estados **NO MEDIDOS**.
> Una de las cuatro arquitecturas especificadas tiene implementacion; las otras tres
> existen unicamente como especificacion.

### 13.4 Observacion sobre la naturaleza del proximo obstaculo

Los tres estados no medidos que impiden afirmar que el sistema funciona (10.1, 10.2,
10.3) no se resuelven escribiendo codigo. Requieren dos tramites administrativos con
latencia de dias de calendario y la construccion de un conjunto anotado. Toda linea
de codigo adicional producida antes de cerrarlos incrementa el volumen de trabajo
verificado sobre una hipotesis no validada, lo que constituye el riesgo de
priorizacion mas caro identificado en este dossier.
