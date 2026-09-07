# INFORME TECNICO DE AUDITORIA · PROYECTO CASHGO

**Revision:** 5 · **Rama:** `titan/auditoria-cashgo`
**Artefacto de custodia:** `evidencia/MANIFEST.sha256`
**Autor:** BRAIN (agente). **No es independiente.**

Este archivo no transcribe su propio head SHA: lo ata el manifiesto. Si el informe
que circula no aparece con su hash en `evidencia/MANIFEST.sha256`, y ese manifiesto
no verifica contra el arbol, **no es el informe auditado**. Verificacion en un
comando: `python3 scripts/manifiesto.py --verificar`.

## 0. LO PRIMERO: hubo una auditoria INDEPENDIENTE y encontro un vector abierto

Las revisiones 1 a 4 de este informe las escribio **el autor del codigo**, y la
primera pagina lo decia. La revision 5 existe porque por primera vez audito el repo
**alguien que no toco una linea**: TITAN Tao, sobre el head `c8c399d`, leyendo el
arbol real y no los Docs.

Trajo **tres hallazgos que no estaban** en las cuatro pasadas previas ni en los 32
defectos propios ya registrados. **Los tres se re-midieron aca sobre el arbol real
antes de aceptarlos**, incluida la verificacion adversarial que el propio auditor
pidio para poder caerse. Los tres CONFIRMAN, y uno **es mas grave de lo que reporto**.

| Hallazgo | Severidad | Estado |
|---|---|---|
| **H-01** el escape de delimitadores cubria el copy y no `ad_id` ni `plataformas` | ALTO | confirmado, **agravado**, y cerrado con test |
| **H-02** rama inalcanzable en el parser de JSON | BAJO | confirmado (0 de 4) y retirada |
| **H-03** `sin_urls` no cubria la `narrativa` | MEDIO latente | confirmado y cerrado con test |
| **estructural** el exit code de `pip-audit` no distingue "vulnerable" de "no pude contestar" | ALTO de diseno | aceptado: `scripts/gate_deps.py` |

Y una regla que este dossier venia predicando y que la pasada independiente vuelve
concreta: **la coincidencia entre cuatro informes del mismo autor no es
verificacion.** Ninguno de los tres hallazgos requeria una herramienta que yo no
tuviera. Requeria no ser yo.

### 0.1 H-01 es peor de lo que el auditor midio, y eso lo medi yo

Tao midio **el parser**: el payload en `ad_id` produce 2 bloques donde deberia haber
1. Medi **el efecto**, que es lo que termina impreso en el PDF del cliente:

```
lote de 2 anuncios, payload en el ad_id del primero
  parser real del dry-run: 3 bloques para 2 anuncios
     ad_id parseado -> 111
     ad_id parseado -> ad_victima_legitimo     <- fabricado por el atacante
     ad_id parseado -> 222

  analisis validos: 1   rechazos: 3
     ad_victima_legitimo   angulo=otro   promesa='producto defectuoso, no compren nunca'
  la promesa de la VICTIMA la escribio el atacante: True
```

**El atacante escribe la promesa que se imprime atribuida a un competidor
legitimo.** Y hay un detalle que agrava el diagnostico: el bloque fabricado va
ANTES del legitimo, asi que **la regla de B2 "gana la primera ocurrencia" juega a
favor del atacante**. Un guard que se agrego para cerrar un hallazgo termino
ayudando a explotar otro. Con el parche: `promesa='Garantia de 30 dias'`, la suya.

### 0.2 Y un hallazgo sobre los parches del auditor, no sobre el codigo

Los tres parches venian corridos, pero al revertirlos uno por uno **la suite de 141
tests siguio en VERDE para M-02 y M-03**. O sea que dos de las tres correcciones
entraban **sin guard**: exactamente el patron que este repo persigue (un fix sin
control positivo es una hipotesis). Se agrego el test que faltaba para H-03, y el
control de mutacion ahora dice cual cae:

```
revierto M-01  -> FAILED (failures=5): ad_id, page_id, plataformas, lote, promesa-de-la-victima
                  y test_el_copy_esta_neutralizado queda VERDE  <- el control positivo
revierto M-03  -> FAILED (failures=2): narrativa_no_conserva_urls, mismo_trato_que_la_promesa
revierto M-02  -> OK, y va declarado: la rama era muerta, no tiene efecto funcional
                  medible, asi que ningun test puede discriminarla. Su justificacion
                  es higiene, no correccion, y decir otra cosa seria inventar un guard.
```

## 1. Estado de esta revision, dicho antes que cualquier numero

La segunda pasada externa (head `de13b9a6`) dio **88/100** y el veredicto correcto
fue demoledor en lo que importaba: *"la propuesta de valor del dossier (cada cifra
se puede recomputar) hoy se cumple EN CONTRA del informe: la recompute y no da"*.

Tres hechos de esa pasada, sin suavizar:

1. **El CI del head anterior estaba ROJO** y el rojo estaba en el paso 7 de un job
   secuencial, asi que la suite, el control positivo, el pipeline y los modelos
   quedaron `skipped`. Las ocho correcciones B1-B8 estaban **NO MEDIDAS por
   instrumento ajeno** mientras el informe hablaba de ellas.
2. **Habia tres cifras distintas del mismo arbol en el mismo commit**: la tabla
   del informe (24 / 4.653 / 2.947 / 230 / 753), el CSV (23 / 4.665 / ...) y el
   arbol recomputado (23 / 4.666 / ...). Sexta reincidencia de A1.
3. **El manifiesto no describia su propio arbol**: 7 de 16 hashes en rojo, y nadie
   lo vio porque su paso quedo detras del rojo del inventario.

Esta revision no discute nada de eso. Lo corrige con instrumentos y declara que la
**rubrica externa vigente sigue siendo 88/100** hasta que haya tercera pasada.

### 1.1 Estado del CI, por job y sin maquillar

Cinco jobs, uno por pregunta. **Tres verdes y dos rojos**, y los dos rojos no son
lo mismo que los tres verdes al reves: uno es un guard que funciona, el otro es un
diagnostico que no tengo.

| Job | Que pregunta | Resultado |
|---|---|---|
| `custodia` | los recibos describen este arbol? | **success** |
| `suite` | el codigo funciona? | **success** |
| `secretos` | hay credenciales en el historial? | **success** |
| `deps-pins` | hay CVEs en nuestros 3 pines? | **failure** |
| `deps-arbol` | hay CVEs en el arbol transitivo? | **failure** |

**Lo que se puede afirmar del verde.** `suite` verifica por instrumento ajeno los
144 tests, el control positivo 7/7, el pipeline, el PDF y los modelos de costo sobre
el arbol corregido, **y eso incluye los 16 tests que fijan el vector H-01**: o sea
que el arreglo de seguridad de esta revision no es una afirmacion propia.
`secretos` dio verde en **cuatro corridas seguidas** con `fetch-depth: 0`, o sea
sobre los **30 commits del historial** y no sobre el arbol: eso cierra un NO MEDIDO
real, porque mi escaneo propio cubria los 44 archivos del arbol y un secreto
commiteado y borrado despues no aparece ahi.

**Y una honestidad sobre el verde de `custodia`:** durante este turno estuvo rojo
tres veces por mi culpa, no por el codigo. Las tres fueron la misma falla, que esta
en los defectos 30, 31 y 36: pushear contenido escrito en el payload en vez de los
bytes de mi arbol. El guard tenia razon las tres veces.

**Lo que NO se puede afirmar del rojo:** los dos jobs de dependencias estan rojos.
Lo que SI esta medido es que **no es un CVE en nuestros tres pines**, y lo midio la
auditoria independiente sin necesitar el log (ver 5.5, paso 7). Lo que falta es la
causa exacta, y el gate nuevo la va a nombrar en la proxima corrida con su informe
JSON como artifact descargable.

## 2. Que cambio, y por que cada cambio es un instrumento y no una promesa

| Hallazgo | Correccion | Como se verifica que quedo cerrado |
|---|---|---|
| **B (informe ≠ CSV ≠ arbol)** | se decide `fase0/fixtures/__init__.py` (conserva su docstring, 1 linea) y se regenera TODO junto con `scripts/cerrar.sh` | `scripts/informe_vs_csv.py` da rojo si la fila TOTAL del informe no sale del CSV |
| **D1 (CSV contaminado)** | `inventario.py --csv` manda los mensajes de guard a **stderr**; stdout es CSV y nada mas | el CSV commiteado ya no tiene la linea `GUARD VERDE`; un parser lo lee entero |
| **D2 (un job secuencial ciega el codigo)** | el workflow se parte en **cinco jobs paralelos, uno por pregunta** | **medido tres veces**: cada particion volvio legible un rojo que antes obligaba a abrir el log (1.1 y 5.5) |
| **D3 (el control positivo muta el arbol real)** | aborta con exit 2 si `git status --porcelain` no esta limpio en los 3 archivos que muta; restauracion doble (copia + `git checkout --`); trap en EXIT, INT y TERM | probado en los dos sentidos: arbol limpio -> 7/7 cazadas; archivo sucio a proposito -> **exit 2, "No se midio nada"** |
| **D4 (descripcion del PR obsoleta)** | cuerpo del PR reescrito al alcance real | la pagina del PR ya no dice "cero codigo de producto" |
| **D5 (8 commits de convergencia a mano)** | `scripts/cerrar.sh`: regenera los recibos y **despues** exige `git status` limpio. Instalable como hook `pre-push` | A1 pasa a darse rojo antes del push en vez de despues (ver defecto 24) |
| **D5 bis (los controles de seguridad no eran controles)** | `pip-audit` y `gitleaks` **bloqueantes**, en tres jobs propios, con `fetch-depth: 0` | `secretos` VERDE ajeno 4 corridas; el rojo de deps queda NO MEDIDO y declarado (5.4 y 5.5) |
| **H-01 (la frontera de ingesta cubria un campo de tres)** | `ad_id`, `page_id` y `plataformas` pasan por `normalizar`, igual que el copy | 6 tests del vector + control positivo del copy; revertir tira 5 y deja verde el control |
| **H-02 (rama inalcanzable en el parser)** | un solo patron `_FENCE` en una operacion | 0 de 4 formas reales tocaban la rama; se declara que ningun test puede discriminarla |
| **H-03 (`narrativa` sin `sin_urls`)** | pasa por el mismo filtro que la promesa | 3 tests, uno de ellos control positivo por comparacion contra `promesa` |
| **estructural (el gate no discriminaba)** | `scripts/gate_deps.py`, tres estados | 6 controles, los 3 estados alcanzados (5.5) |
| **A1 preventivo** | `.gitattributes` con `* text=auto eol=lf` | ningun hash del manifiesto depende de la plataforma del clon (ver defecto 23) |

### 2.1 Lo que NO se hizo, y por que

El desglose por capa de la tabla de inventario (produccion / tests / fixtures /
scripts) **sigue siendo tipeado**: esa agrupacion es editorial y no existe en el
CSV, asi que `informe_vs_csv.py` **no la cubre**. Cubre la fila TOTAL y la cantidad
de archivos. Se declara aca en vez de dar la impresion de que todo el cuadro esta
atado. La suma de las cuatro capas contra la fila TOTAL se verifico a mano en esta
corrida y cierra, y eso es una verificacion de una vez, no un guard.

Y lo que **no se toco a proposito**, aunque el auditor lo puso sobre la mesa: el
`content_hash`, el prefijo estable y el esquema de la base. Son contratos
compartidos, ninguno de los tres hallazgos los necesitaba, y tocar un contrato para
arreglar un bug de frontera es la forma mas caras de arreglar barato.

## 3. Inventario

Instrumento: `python3 scripts/inventario.py`. La fila TOTAL sale de
`evidencia/inventario.csv` y el CI falla si este informe cita otra.

| Capa | Archivos | Total | Codigo | Comentario | Docstring | Blanco |
|---|---:|---:|---:|---:|---:|---:|
| Produccion `fase0/` | 9 | 2.364 | 1.433 | 191 | 404 | 336 |
| Tests `fase0/tests/` | 9 | 1.697 | 1.026 | 7 | 348 | 316 |
| Fixtures | 2 | 175 | 130 | 15 | 11 | 19 |
| Scripts | 6 | 969 | 613 | 71 | 139 | 146 |
| **TOTAL Python** | **26** | **5.205** | **3.202** | **284** | **902** | **817** |

Lineas de codigo test/produccion: **0,72**. Ratio comentario+docstring/codigo:
**0,370**. Dependencias de terceros: 3, pinneadas exactas. Dependencias de test: 0.

**Los dos archivos nuevos de esta revision** son `fase0/tests/test_frontera_de_ingesta.py`
(16 tests que fijan H-01 y H-03, con control positivo adentro) y
`scripts/gate_deps.py` (el gate de tres estados). El resto del delta son los
comentarios de los tres parches. El ratio test/produccion sube de 0,63 a 0,72 y no
lo persegui: es consecuencia de que los tres parches entraron con 16 tests y no con
una corrida.

## 4. Arquitectura e invariantes

```
ads_archive oficial -> persistencia SQLite -> SHA-256 de contenido
-> DeepSeek V4-Flash (funcion pura, sin credenciales)
-> agregacion determinista -> HTML -> PDF
```

Criterio de frontera: si el error cuesta dinero o es irreversible, la logica es
determinista; si cuesta un token, puede ser cognitiva.

Invariantes: el LLM no porta credenciales; todo output se valida con `Literal` y
`extra="forbid"`; `content_hash` excluye `ad_id`, fechas y plataformas; outputs
repetidos, omitidos e inventados se distinguen; **`<<<` se neutraliza en ingesta en
TODO campo que se interpole en el prompt, no solo en el copy** (H-01); el prompt
estable tiene SHA-256 pinneado; el HTML se escapa; los tres campos de texto libre
que se imprimen pasan por `sin_urls`; la tasa de cache tiene tres estados (VERDE,
ROJO, NO MEDIDO).

## 5. Verificacion

### 5.1 Estado del CI

El ultimo verde de job unico fue `31178a1`, **antes** de B1-B8. El head `de13b9a6`
dio `failure` en los runs `34084699103` y `34084702756`, con todo lo funcional en
`skipped`. Cualquier lectura de "verificado por CI ajeno" en la revision 2 valia
para `31178a1` y no para el arbol corregido: el auditor lo marco y es correcto.

Con el workflow partido la afirmacion es **por job**, y esa es la unica forma en que
este dossier puede hablar del CI sin mentir por agregacion: un veredicto unico sobre
cinco preguntas distintas obliga a elegir entre "todo verde" y "algo esta mal", y
ninguna de las dos describe el head. Los cinco resultados estan en 1.1.

### 5.2 Instrumento propio, con evidencia cruda (W-01)

Corrido por BRAIN en su sandbox, Python 3.12, con las **tres dependencias en su
version pinneada exacta** (pydantic 2.13.4, weasyprint 69.0, pypdf 6.14.2), sobre
un arbol reconstruido y **verificado blob a blob contra el repo**: los archivos de
codigo con SHA-1 de git identicos, o sea que lo que se midio es el arbol del repo y
no una copia parecida.

| Instrumento | Resultado | Recibo |
|---|---|---|
| `unittest discover` | **144 tests, exit 0** (128 + 16 de la frontera de ingesta) | `evidencia/salida_tests_fase0.txt` |
| conteo estatico de `def test_` | **144**, coincide con lo declarado | — |
| `control_positivo_suite.sh` | **7/7 cazadas por su test especifico**, arbol restaurado en verde | `evidencia/salida_control_positivo.txt` |
| guard D3 del control positivo | **exit 2 con archivo sucio**: el guard puede dar rojo, y dio | 5.3 |
| `inventario.py` | 26 archivos parsean, las sumas cierran | `evidencia/salida_inventario.txt` |
| `informe_vs_csv.py` | fila TOTAL del informe == CSV | — |
| `manifiesto.py --verificar` | 19 entradas coinciden con el arbol | `evidencia/salida_manifiesto.txt` |
| `gate_deps.py` | 6 controles, los 3 estados alcanzados | 5.5 |
| pipeline `--dry-run --pdf` | 23 filas de 24, 1 duplicado colapsado, 2 llamadas, 1 lote, 23 analisis, **0 rechazos**, PDF de 4 paginas y 4.474 caracteres | `evidencia/salida_fase0_dryrun.txt` |
| `modelo_costo_arq3.py` | GUARD VERDE margen peak **96,28%** | `evidencia/salida_modelo_costo_arq3.txt` |
| `sensibilidad_infra_y_equipo.py` | margen peak con el stack del blueprint (USD 395) **82,14%** | `evidencia/salida_sensibilidad_infra_y_equipo.txt` |

Cada recibo arranca con una cabecera de procedencia: instrumento, comando, version
de Python y las tres dependencias pinneadas. Sin eso un archivo de evidencia no
dice quien lo corrio ni con que, y entonces no se puede contradecir.

El HTML es byte-determinista; el PDF **no**, porque WeasyPrint embebe el timestamp
de creacion (medido: 23.259 / 23.251 / 23.254 bytes en tres corridas, tres SHA
distintos). Por eso el peso del PDF no se cita como dato reproducible y `*.pdf`
esta marcado `binary` en `.gitattributes`.

### 5.3 Control positivo del guard nuevo

Un guard que no puede dar rojo es un adorno (defecto 10 de este registro). El de D3
se probo en los dos sentidos, y despues **dio rojo solo, en produccion**: al
regenerar los recibos de esta revision con `fase0/cognitive.py` sin commitear, el
recibo del control positivo quedo con un `ABORTA` en vez de un 7/7. Eso no es un
bug: es el guard haciendo exactamente lo que se le pidio, y el recibo se regenero
despues de commitear.

```
arbol limpio    -> "arbol limpio en los archivos mutables: verificado con git status."
                   VERDE: 7/7 mutaciones cazadas por su test especifico.
arbol sucio     -> ABORTA: el arbol tiene cambios sin commitear ...
                    M fase0/cognitive.py
                   Commitea o guarda esos cambios y volve a correr. No se midio nada.
                   exit=2
```

**Limitacion declarada que sigue en pie:** un `kill -9` o la muerte del sandbox no
ejecutan ningun trap, asi que pueden dejar un mutante vivo. Lo que cambia es que la
proxima corrida **se niega a arrancar** en vez de medir sobre un arbol contaminado,
y `custodia` lo enrojece en el CI. Chequeo manual: `grep -rn "# MUTANTE" fase0`.

### 5.4 Los controles de seguridad pasan de aviso a porton

Hasta el head anterior, `pip-audit` y `gitleaks` corrian con `continue-on-error:
true`. La consecuencia, dicha completa y no como matiz: **podian haber estado
fallando desde el primer dia y el job igual daba verde**, y nadie lo hubiera sabido
porque nunca lei su salida. Un paso de CI que no puede hacer fallar el job es el
defecto 10 de este registro (guard con rama inalcanzable) disfrazado de una linea de
YAML.

Ahora son **tres jobs bloqueantes** y sin una sola excepcion en todo el workflow:
`deps-pins`, `deps-arbol` y `secretos`.

**Secretos: cerrado y verde por instrumento ajeno.** Antes de bloquear se corrio un
escaneo propio con 13 reglas de alta senal de gitleaks (PAT de GitHub clasico y
fine-grained, tokens de app y OAuth, AWS, OpenAI, Slack, Google, Stripe, bloques de
clave privada, JWT, token de Meta y asignacion generica de
`api_key`/`secret`/`token`/`password`) sobre los 44 archivos del arbol: **cero
hallazgos**, y con control positivo, porque un canario `sk-` de 32 caracteres fue
cazado por dos reglas. Sin ese canario, "cero hallazgos" no distingue un arbol
limpio de un escaneo roto.

Y el limite de esa medicion propia era real: cubria el **arbol**, no el
**historial**. Un secreto que entro en un commit y se borro en el siguiente no
aparece en el arbol y sigue vivo en los 30 commits. Eso solo lo ve `gitleaks` con
`fetch-depth: 0`, que es como quedo configurado, y **dio verde en cuatro corridas
seguidas**. Ese tramo pasa de NO MEDIDO a medido.

**Dependencias: el detalle completo esta en 5.5**, incluida una hipotesis mia que el
instrumento falso y el hallazgo estructural que la auditoria independiente aporto.

**Consecuencia de diseno que hay que declarar porque cambia el contrato del CI:**
`pip-audit` consulta una base de datos viva, asi que los dos jobs de dependencias
son **los unicos pasos no deterministas del CI**. Un CVE publicado manana pone el
repo en rojo sin que nadie toque una linea. Eso es exactamente lo que se le pide a
una auditoria de dependencias, y es la razon por la que su rojo vive en jobs
separados: no debe confundirse con "el codigo se rompio" ni con "alguien filtro una
credencial", que son tres emergencias con tres respuestas distintas.

### 5.5 El rojo de dependencias: lo que hice, lo que descarte y lo que NO se

Este es el unico tramo del dossier donde el proceso importa mas que el resultado,
porque el resultado sigue teniendo un no-medido y el camino explica por que eso es
un estado legitimo y no una excusa.

**Paso 1. Medir antes de bloquear.** Verificado en vivo contra OSV/GHSA/NVD:

| Dependencia | Estado |
|---|---|
| `pydantic==2.13.4` | sin vulnerabilidades conocidas |
| `weasyprint==69.0` | **es la version que ARREGLA** CVE-2026-49452 (inyeccion de CSS via presentational hints, afecta `<= 68.1`) |
| `pypdf==6.14.2` | **es la version que ARREGLA** CVE-2026-59935 (bucle infinito ASCII85/ASCIIHex al extraer texto, `< 6.14.2`, CVSS 8.7) |

Y las dos ultimas no son casualidad: son **las dos rutas que este codigo recorre**.
El pipeline renderiza HTML construido con texto de terceros (weasyprint) y los tests
extraen texto de un PDF (pypdf). Los pines exactos que estaban por disciplina de
reproducibilidad resultaron ser, medido, los que esquivan dos vulnerabilidades sobre
superficie real.

**Paso 2. Bloquear, y que de rojo.** Al quitar `continue-on-error` el job de
seguridad dio failure. Correcto: eso es lo que hace un porton.

**Paso 3. Partir el job para saber DONDE, en vez de adivinar.** El primer veredicto
decia `failure` sin decir si el CVE estaba en pip-audit o en gitleaks. Se partio en
`dependencias` y `secretos`: gitleaks verde, pip-audit rojo. Y despues se partio
otra vez en `deps-pins` (`--no-deps`, solo nuestros 3 pines) y `deps-arbol` (arbol
completo), porque su rojo **no se arregla igual**: uno se arregla subiendo un pin
nuestro, el otro obliga a decidir si se pinnea algo que hoy flota.

**Paso 4. El dato que la particion regalo.** Fallan **los dos**, incluido el que
solo mira los tres pines que acabo de verificar limpios. Eso descarta "hay un CVE en
un paquete nuestro" **sin leer un log**, y manda a buscar al entorno. Con el job
unico, el candidato obvio habria sido subir un pin que estaba bien.

**Paso 5. Una hipotesis, y el instrumento la FALSA.** `actions/setup-python@v6` no
instala el pip de PyPI: usa el que quedo horneado en el toolchain (pip 26.0.1 para
Python 3.12), y ese pip tiene CVE-2026-3219, arreglado en 26.1. pip-audit audita el
pip del entorno donde corre. La evidencia a favor estaba **en el propio workflow**:
el job `suite` hace `python -m pip install --upgrade pip` y pasa; los dos de
dependencias no lo hacian y fallan. Se agrego el upgrade a los dos.

**Resultado: siguen rojos.** La hipotesis queda **refutada por el instrumento**, no
por una relectura. El `--upgrade` se conserva porque es correcto igual, con su deuda
declarada en el workflow: es un parche por retraso de la imagen del runner y se saca
cuando setup-python traiga pip >= 26.1 nativo.

**Paso 6. Donde me quede sin instrumento.** Para leer el ID exacto del CVE hace
falta abrir el log del job y mis herramientas no pueden. Declare la causa como NO
MEDIDA y pedi el log.

**Paso 7. Y la auditoria independiente lo resolvio sin el log, con el hallazgo
estructural del turno.** No hacia falta el log para saber que **no es un CVE en
nuestros pines**:

- los tres pines estan limpios en **tres bases de advisories independientes** (OSV,
  GHSA, Snyk), y dos de ellos **son las versiones que arreglan** CVE-2026-49452 y
  CVE-2026-59935;
- y hay un cruce interno que cierra la hipotesis alternativa: **el job `suite` corre
  `pip install -r fase0/requirements.txt` y esta VERDE sobre el mismo head**, asi
  que los tres existen en PyPI y resuelven.

Con eso queda medido lo que importa: **el exit code de `pip-audit` vale 1 para tres
cosas distintas** (un advisory real, un error del servicio y un crash no capturado).
Un porton BLOQUEANTE que no distingue "esto es vulnerable" de "no pude contestar"
**entrena al equipo a ignorarlo**, y eso es peor que no tenerlo, porque parece que
lo tenes. Es el defecto 10 de este registro (guard que no discrimina) en la capa de
infraestructura, y yo lo estaba tratando como un problema de diagnostico cuando era
un problema de **diseno del gate**.

**Correccion aceptada e integrada:** `scripts/gate_deps.py` lee el informe JSON que
pip-audit ya sabe emitir y separa **tres estados**, que son los mismos tres de todo
este repo:

    0  VERDE            corrio, contesto, cero advisories aplicables
    1  ROJO SEGURIDAD   corrio, contesto, hay al menos un advisory
    2  ROJO INSTRUMENTO no pudo contestar: sin archivo, JSON invalido, sin deps,
                        o con dependencias saltadas (respuesta parcial)

Los seis controles, corridos, con los tres estados alcanzados:

```
limpio.json      exit=0  [VERDE] 3 dependencias auditadas, cero advisories aplicables
vulnerable.json  exit=1  [ROJO SEGURIDAD] 1 advisory(s) sobre 2 dependencias:
                           - pypdf 6.14.1: GHSA-g867-7843-wf8q -> subir a 6.14.2
saltada.json     exit=2  [ROJO INSTRUMENTO] pip-audit SALTO dependencias: privada (...)
traceback.json   exit=2  [ROJO INSTRUMENTO] no es JSON valido: salida truncada o traceback
vacio.json       exit=2  [ROJO INSTRUMENTO] esta vacio: murio antes de escribir
no-existe.json   exit=2  [ROJO INSTRUMENTO] no llego a contestar
estados alcanzados: [0, 1, 2] -> el gate es falsable en sus tres direcciones
```

**Y un defecto propio en la sonda que midio esto**, porque es el patron de siempre:
la primera corrida de esos seis controles reporto `exit=0` para todos. El bug no
estaba en el gate: estaba en mi sonda, que leia el `$?` del `head` del pipe y no el
del Python. Medi el sujeto equivocado en el instrumento que verificaba el
instrumento. Corregido y re-medido, y el numero de arriba es el de la segunda.

**Lo que sigue NO MEDIDO, mas preciso que antes:** la causa exacta del rojo actual.
El gate nuevo la va a nombrar en la proxima corrida, y su informe queda como
**artifact descargable**, que era el otro hueco del turno: nadie del equipo podia
abrir el log. Y el rojo de `deps-arbol` puede ser real y no se arregla con este
parche: el arbol transitivo **flota**.

**Esa ultima consecuencia si quedo medida, y es mia:** `requirements.txt` pinnea
tres paquetes; weasyprint arrastra Pillow, tinycss2, cssselect2, pyphen, fonttools,
pydyf y cffi, y pydantic arrastra pydantic-core, annotated-types y
typing-extensions. Ninguno esta pinneado. El informe decia "pins exactos, nada de
rangos" y eso vale para los tres DIRECTOS: verifique tres paquetes y hable como si
hubiera verificado el conjunto. Es E-01, medir el sujeto chico y concluir sobre el
grande, en la seccion que mas se jactaba de rigor. El procedimiento para cerrarlo
(`pip-compile --generate-hashes` a un `requirements.lock`, y auditar el lock con
`--require-hashes`) queda como deuda declarada: necesita red y no la tengo, y
**inventar versiones y hashes seria peor que un rango**, porque parece riguroso y no
lo es.

## 6. Rubrica

**Externa vigente: 88/100** (segunda pasada, head `de13b9a6`). No se sube un solo
punto por cuenta propia. La pasada independiente de Tao se autoevalua **93,3/100**
sobre 5 criterios aplicables con 55 puntos N/A declarados; no la promedio con la mia
porque no es mia y no la medi yo.

| Criterio | 1a pasada | 2a pasada (vigente) | Que se toco en esta revision |
|---|---:|---:|---|
| Ejecutabilidad | 15 | 13 | CI partido en cinco jobs; `suite` y `custodia` success. **Dos jobs bloqueantes en rojo sin diagnosticar**: por el estandar de este dossier, eso NO habilita subir este criterio |
| Seguridad | 12 | 13 | **se cerro un vector ALTO que cuatro pasadas propias no vieron**, con 16 tests y control positivo; los tres controles pasan de aviso a porton; `secretos` VERDE ajeno sobre el historial |
| Testing | 12 | 13 | 128 -> 144 tests; guard de arbol limpio; y el hallazgo de que dos parches ajenos entraban sin guard |
| Proceso QA | 2 | 1 | `informe_vs_csv.py`, `cerrar.sh`, `.gitattributes`, D1, cabeceras de procedencia, `gate_deps.py`. **Y en contra: tres rojos de custodia por mi culpa en este turno** |
| Resto | 48 | 48 | — |
| **Total** | **89** | **88** | **pendiente de tercera pasada** |

## 7. Estados NO MEDIDOS

1. Ninguna llamada real a `ads_archive`.
2. Ninguna llamada real a DeepSeek.
3. Calidad semantica del modelo (hace falta un golden set etiquetado a mano).
4. Review de Copilot: pedido en el PR el 2026-09-07; **sin hallazgos emitidos a los 12 minutos**, y eso **no es aprobacion** (K-02). Declarado deuda.
5. Precio y disposicion a pagar.
6. CAC y retencion.
7. Corpus comercial para LatAm: sin via legal identificada. **Y ahora tiene una consecuencia de seguridad medida:** H-01 sube de explotabilidad BAJA a MEDIA/ALTA el dia que el corpus deje de venir de Meta.
8. Residencia de datos (DeepSeek procesa en China, el corpus legal es europeo).
9. Umbrales exactos del tier estandar de Marketing API.
10. Formato de anuncio en produccion: ningun campo de `CAMPOS_ADS_ARCHIVE` lo informa, asi que la seccion 4 del PDF sera inerte. Hay que confirmar un campo oficial o retirar la seccion.
11. ~~gitleaks sobre el historial~~ **RESUELTO Y MEDIDO**: verde ajeno en cuatro
    corridas con `fetch-depth: 0` sobre los 30 commits. Era el tramo que mi escaneo
    propio no cubria (yo mire los 44 archivos del arbol, no el historial).
11 bis. **La CAUSA exacta del rojo de `deps-pins` y `deps-arbol`.** Lo que SI esta
    medido: no es un CVE en nuestros tres pines (5.5, paso 7). Lo que falta es el ID
    concreto, y el gate nuevo lo va a nombrar con su informe como artifact.
12. Tercera revision externa de estas correcciones.
13. Cobertura de lineas: no hay instrumento. 144 tests no son una medida de cobertura.
14. ~~El CI de este head~~ **RESUELTO Y MEDIDO**: ver 1.1. Se deja tachado en vez de borrado porque un NO MEDIDO que se resuelve es informacion, y borrarlo esconde que hubo un tramo del turno en que la afirmacion no tenia respaldo.
15. **`adlibrary.py`, `dedup.py` y `config.py` no fueron auditados en profundidad** por la pasada independiente, y su propio autor los declara. Los 128 tests originales tampoco se releyeron uno por uno.
16. **Pinneo del arbol transitivo de dependencias.** Diez paquetes flotan. Procedimiento en 5.5, requiere red.

## 8. Registro completo de defectos propios

1. Falta de test para fecha de inicio en el hash.
2. Indice por `ad_id` produjo informes distintos en la segunda corrida.
3. Contador 613 contaba el intento final.
4. Veredicto de semanas-persona hardcodeado.
5. Prefijo de costo sobreestimado 12x.
6. Recibo decia 100 tests y eran 101.
7. Test prohibia llaves JSON legitimas.
8. Test `onload=` confundia HTML escapado con ataque.
9. Conteo de paginas del PDF por bytes comprimidos.
10. Guard de inventario inalcanzable.
11. Informe coloquial para un auditor tecnico.
12. Test de inyeccion pasaba con `angulo` abierto, por rechazo en `cta`.
13. Manifiesto autorreferente daba rojo siempre.
14. Workflow local y git diferian en 100/101 tests.
15. A1 reincidio durante su propia correccion: tres recibos para un archivo.
16. Peso del PDF citado como determinista aunque WeasyPrint embebe timestamp.
17. El CI detecto seis archivos divergentes que no habia ejecutado ningun instrumento.
18. El ancla del control positivo contenia una secuencia de escape que se deformaba al transportarse por JSON: siete diagnosticos manuales antes de mirar el canal.
19. **El CSV de inventario no era un CSV** (D1). Peor que el bug: el `diff` del CI pasaba porque los dos lados tenian la misma linea de guard adentro. Un guard que compara dos copias del mismo error no mide nada, y lo escribi yo despues de haber documentado ese exacto patron en el defecto 10.
20. **La tabla del informe estaba tipeada** mientras el propio informe declaraba que el CI compara el CSV. Sexta reincidencia de A1, y la unica de las seis que un guard de diez lineas habria evitado desde el principio.
21. **Puse la custodia antes de la suite en un job secuencial.** Un defecto documental de una linea escondio durante horas si ocho correcciones de codigo funcionaban. El orden de los pasos de un CI es una decision de arquitectura y la trate como un detalle de redaccion.
22. **El primer `cerrar.sh` regeneraba recibos siempre, y por eso su chequeo de custodia daba ROJO SIEMPRE.** `unittest -v` imprime la duracion de la corrida, asi que ese recibo cambia de bytes en cada ejecucion aunque el arbol sea identico, el manifiesto cambia con el, y `git status` nunca queda limpio. Es el defecto 13 exacto cometido DENTRO del instrumento que escribi para no volver a cometerlo. Correccion: dos modos, y la declaracion de que un recibo de corrida es una foto con su duracion adentro y no un artefacto reproducible.
23. **Mi propio `.gitattributes` preventivo casi rompe el manifiesto en cualquier clon fresco.** `csv.DictWriter` escribe CRLF por default; con `* text=auto eol=lf` git guarda LF, y el manifiesto (que firma bytes crudos) habria dado rojo por una diferencia que no es de contenido. Lo cazo `git` con un warning que estuvo a un caracter de pasar desapercibido. Correccion: `lineterminator="\n"` explicito. Una medida preventiva sin control positivo es una hipotesis.
24. **El informe se me quedo viejo mientras corregia otra cosa, y esta vez lo cazo el instrumento y no un humano.** `informe_vs_csv.py` dio `GUARD ROJO: total informe=4805 csv=4811` antes de cualquier push. Es la septima aparicion de A1 y la primera que costo veinte segundos en vez de un ciclo de auditoria externa.
25. **Un recibo commiteado imprimia la ruta absoluta de mi sandbox.** No es reproducible en otro clon y filtra el layout de mi maquina a un archivo publico. Correccion: ruta relativa.
26. **Parti la convergencia en tres commits cuando la correccion pedida era UNO, y pushee un head sabiendo que su custodia iba a dar rojo.** El motivo del corte es real (limite de tamano del canal) y no alcanza como justificacion. **Aprendizaje:** anunciar un rojo no equivale a evitarlo.
27. **Mi script de edicion aborto en un `assert`** porque el archivo de mi sandbox no era el pusheado: habia aplicado las ediciones solo en el payload del push. Dos versiones del informe otra vez, dentro del turno que lo estaba corrigiendo. Regla: **editar el archivo local y pushear el archivo local; nunca construir el contenido en el payload.**
28. **Tuve `custodia` en rojo dos commits seguidos por no haber diagnosticado primero.** La accion correcta es **enumerar QUE archivo difiere** comparando blob SHA, uno por uno. Eso tomo una llamada; adivinar costo dos commits.
29. **Tuve dos controles de seguridad con `continue-on-error: true` durante todo el proyecto y los presente como parte del CI.** Dicho completo: podian haber estado fallando desde el primer dia y el job igual daba verde. Un paso de CI que no puede hacer fallar el job es el defecto 10 con otro disfraz, y el disfraz era una linea de YAML.
30. **Reincidencia EXACTA del 27, dos horas despues de escribirlo y en el mismo archivo.** Lo que agrega al registro: **escribir la regla no la instala.** Ninguna de las veces que anote A1 la detuvo; la detuvieron los guards que dan rojo.
31. **La misma falla otra vez, en el workflow, y rompio `custodia` en el CI.** La causa raiz es estructural: mi canal de escritura toma el contenido como texto, asi que **cada push es una re-transcripcion**, y transcribir 11 KB a mano falla. Correcciones: verificar el blob despues de cada push, y **acortar el archivo** (11.408 -> 5.285 bytes). Reducir la superficie de una falla que ya se repitio no es cosmetica.
32. **Escribi `scripts/vs_remoto.py`, lo probe en sus tres estados y NO lo entregue.** Lo saque del commit a proposito y va declarado como no entregado en vez de mencionado como si estuviera hecho.
33. **Cuatro pasadas propias no encontraron el vector H-01, y una auditoria ajena lo encontro en una.** El comentario de `schemas.py` decia: *"si la secuencia no puede aparecer en el copy, ningun anuncio puede fabricar un bloque atribuido a otro anunciante"*. La premisa era verdadera y la conclusion no se seguia, porque `formatear_anuncio` interpola TRES campos y solo uno tenia validador. Es el patron 2 de este registro (la promesa del docstring mas amplia que el guard) en la seccion de seguridad. **Lo que agrega:** yo verifique el guard que escribi, no la superficie que el guard tenia que cubrir. Verificar el sujeto exacto (E-01) tambien aplica a los guards propios.
34. **Acepte dos parches ajenos que no tenian guard, y casi los entrego asi.** Al revertir M-02 y M-03 la suite de 141 tests siguio en verde. Venian corridos y con salida cruda: el problema no era falta de evidencia, era que **la evidencia era una corrida puntual y no un test que la proxima regresion vuelva a cazar**. Regla: **un parche ajeno se acepta con la misma exigencia que uno propio, y esa exigencia es un guard, no una corrida.**
35. **La sonda que verificaba el gate nuevo dio exit=0 para sus seis controles**, incluido el que tenia que dar 1. El gate estaba bien; mi sonda leia el `$?` del `head` del pipe. Medi el sujeto equivocado **en el instrumento que verificaba al instrumento**. Lo cace porque el resultado era demasiado prolijo: seis controles distintos no pueden dar todos cero.
36. **Construi contenido en el payload del push por SEXTA vez en el mismo turno.** Al pushear `cognitive.py` agregue dos parrafos que no estaban en mi arbol, asi que el blob remoto (19.996 bytes) no coincidia con el local (19.206). La regla del 27 esta escrita, publicada, y la incumpli seis veces. **Conclusion que ya no admite otra lectura: esto no se arregla con una regla.** Se arregla porque el chequeo de blob despues de cada push es obligatorio y lo corri: el costo bajo de un ciclo de auditoria a veinte segundos. Lo que NO baja es la frecuencia del error, y eso hay que decirlo asi.
37. **Mi propia enumeracion de "que difiere contra el remoto" dio 7 falsos positivos.** Compare 32 rutas y siete marcaron DIFIERE: los cinco documentos de decision, el README y `fase0/README.md`. No difieren: **no existen en mi arbol**, porque mi copia local es una reconstruccion de los archivos de codigo, no un clon. Un comparador que trata "ausente" igual que "distinto" me habria hecho pushear siete archivos que no tengo, o sea borrarlos. Lo cace porque siete DIFIERE de golpe en archivos que no toque es demasiada coincidencia. Regla: **un diff contra un remoto tiene que distinguir TRES estados** (igual, distinto, ausente), que son los mismos tres de siempre.

## 9. Reproduccion

```bash
git clone https://github.com/gatehot59-star/cashgo.git
cd cashgo && git checkout titan/auditoria-cashgo
python3 -m venv .venv && . .venv/bin/activate
pip install -r fase0/requirements.txt
python3 -m fase0.fixtures.generar

# custodia (stdlib pura, sin dependencias)
python3 scripts/inventario.py
python3 scripts/inventario.py --csv | diff -u evidencia/inventario.csv -
python3 scripts/informe_vs_csv.py
python3 scripts/manifiesto.py --verificar

# suite
python3 -m unittest discover -s fase0/tests -t . -v
python3 -m unittest fase0.tests.test_hallazgos_auditoria -v
python3 -m unittest fase0.tests.test_frontera_de_ingesta -v
bash scripts/control_positivo_suite.sh
python3 -m fase0.pipeline fase0/fixtures/brief_ejemplo.json \
  --dry-run fase0/fixtures/ads_archive_sample.json --salida /tmp/aud --pdf
python3 scripts/modelo_costo_arq3.py
python3 scripts/sensibilidad_infra_y_equipo.py

# seguridad (bloqueante en CI, con el gate de tres estados)
pip install pip-audit
pip-audit -r fase0/requirements.txt --no-deps --timeout 60 \
  --format json -o /tmp/pins.json || true
python3 scripts/gate_deps.py /tmp/pins.json

# todo junto, con el chequeo de custodia al final
bash scripts/cerrar.sh

# y para dejar los recibos y el manifiesto describiendo este arbol
bash scripts/cerrar.sh --regenerar
```

### Verificaciones adversariales

1. Meter `inicio` en el hash: debe fallar `test_ignora_la_fecha_de_inicio`.
2. Cambiar `angulo: Angulo` a `str`: debe fallar `test_cada_campo_cerrado_contiene_por_si_solo`.
3. Quitar `html.escape`: debe fallar `TestEscapado`.
4. Romper la sintaxis de un modulo: `inventario.py` debe devolver exit 1.
5. Cambiar el prefijo estable: debe fallar su SHA-256 pinneado.
6. Pedir `US` en los paises: `AlcanceComercialError` antes de tocar la red.
7. Cambiar un byte de cualquier evidencia: `manifiesto.py --verificar` exit 1.
8. Quitar la neutralizacion de `<<<`: debe fallar el test B3.
9. Devolver `str` en `Completion`: errores explicitos, contrato roto.
10. **Cambiar un numero de la fila TOTAL de este informe: `informe_vs_csv.py` exit 1.**
11. **Ensuciar `fase0/report.py` sin commitear: el control positivo aborta con exit 2.**
12. **Borrar la linea de guard del CSV y volver a generarlo: los bytes tienen que ser identicos** (el guard ya no va a stdout).
13. **Sacar `ad_id` de los validadores de `AnuncioCrudo`: deben fallar 5 tests del vector H-01, y `test_el_copy_esta_neutralizado` debe quedar VERDE.** Si cae tambien el del copy, el parche rompio lo que ya funcionaba; si NO cae ninguno, el hallazgo H-01 era falso. **Esta es la verificacion que mas expone a este informe.**
14. **Sacar `sin_urls` de la narrativa en `report.py`: deben fallar exactamente 2 tests.** Antes de agregarlos, revertir ese parche dejaba la suite entera en verde.
15. **Correr `gate_deps.py` contra un JSON truncado: exit 2, no exit 1.** Es la propiedad que separa "vulnerable" de "no pude contestar".
16. **Bajar `pypdf` a 6.14.1: `deps-pins` debe reportar CVE-2026-59935.** Ojo con la lectura: ese job **ya esta rojo por otra causa** (5.5), asi que este control se valida por el ID del CVE en el informe JSON, no por el color del job.

## 10. Veredicto

La Fase 0 esta implementada y sus hallazgos de codigo (B1-B8 y H-01 a H-03) estan
cerrados con tests que pueden dar rojo, y eso ya no es una afirmacion propia: **el
job `suite` de un runner limpio verifico los 144 tests sobre el arbol corregido**.
Los hallazgos de proceso estan cerrados con **instrumentos**, no con disciplina, y
cada instrumento se probo en su direccion negativa; el de D2 se probo solo, en
produccion, en su primera oportunidad. Y los tres controles de seguridad dejaron de
ser un aviso: ahora pueden hacer fallar el CI, y uno de ellos ya dio verde ajeno
sobre el historial completo.

**El estado de esta revision en una linea:** la primera auditoria que no escribio el
autor del codigo encontro **un vector de seguridad abierto que cuatro pasadas
propias no vieron**, y el hallazgo resistio la re-medicion sobre el arbol real y
resulto **mas grave** que lo reportado. Eso es exactamente lo que este dossier
pedia a gritos desde la revision 1 y no podia darse a si mismo.

Lo que aprendi de eso, y va sin adorno: **mis 32 defectos propios eran casi todos de
proceso, y el que faltaba era de producto.** Yo audite con obsesion mis
instrumentos de medicion, y el agujero estaba en la frontera de ingesta, en una
promesa de comentario mas amplia que su alcance. Un auditor que no escribio el
codigo no tiene esa ceguera, y ninguna cantidad de rigor propio la reemplaza.

Lo que sigue sin medirse no se movio ni un milimetro: **funcionamiento contra APIs
reales, calidad semantica, tasa de cache y mercado**. Una de cuatro arquitecturas
tiene implementacion. El proximo movimiento correcto no es mas codigo: es la
verificacion de identidad en Meta, una llamada real a DeepSeek y un golden set
etiquetado a mano. Todo lo demas es afilar un instrumento que ya corta.

Y la pregunta que ningun parche contesta, y que la pasada independiente puso arriba
de la mesa: **el PR #1 lleva 49 archivos y +7.800 lineas sin mergear, y `main` sigue
teniendo 16 bytes.** El cuello de botella de CASHGO no es la calidad del codigo.
