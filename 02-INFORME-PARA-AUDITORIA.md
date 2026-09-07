# INFORME TECNICO DE AUDITORIA · PROYECTO CASHGO

**Revision:** 3 · **Rama:** `titan/auditoria-cashgo`
**Artefacto de custodia:** `evidencia/MANIFEST.sha256`
**Autor:** BRAIN (agente). **No es independiente.**

Este archivo no transcribe su propio head SHA: lo ata el manifiesto. Si el informe
que circula no aparece con su hash en `evidencia/MANIFEST.sha256`, y ese manifiesto
no verifica contra el arbol, **no es el informe auditado**. Verificacion en un
comando: `python3 scripts/manifiesto.py --verificar`.

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

### 1.1 Lo que NO esta cerrado en este head, dicho antes de que lo encuentre el auditor

**Los recibos de `evidencia/` y `evidencia/MANIFEST.sha256` todavia son los del
head anterior.** O sea: el paso `custodia/manifiesto` de este head **va a dar
ROJO**, y va a tener razon. No se declara verde nada que no lo este.

Dos cosas que si se pueden afirmar de ese rojo:

- **Es documental, no funcional.** Con el workflow partido (D2), ese rojo ya **no
  oculta** el estado del codigo: `suite` corre en paralelo con los 128 tests, el
  control positivo, el pipeline y los modelos. Es el arreglo de D2 demostrandose a
  si mismo en su primera oportunidad, y es exactamente la informacion que el head
  `de13b9a6` no pudo dar.
- **El contenido de esos recibos existe y esta medido**, corrido sobre este mismo
  arbol convergido con las tres dependencias pinneadas; lo que falta es
  commitearlo. Los numeros estan en la seccion 5.2. Regenerarlos y firmarlos es un
  comando: `bash scripts/cerrar.sh --regenerar`.

## 2. Que cambio, y por que cada cambio es un instrumento y no una promesa

| Hallazgo | Correccion | Como se verifica que quedo cerrado |
|---|---|---|
| **B (informe ≠ CSV ≠ arbol)** | un solo commit de convergencia: se decide `fase0/fixtures/__init__.py` (conserva su docstring, 1 linea) y se regenera TODO junto con `scripts/cerrar.sh` | `scripts/informe_vs_csv.py` da rojo si la fila TOTAL del informe no sale del CSV |
| **D1 (CSV contaminado)** | `inventario.py --csv` manda los mensajes de guard a **stderr**; stdout es CSV y nada mas | el CSV commiteado ya no tiene la linea `GUARD VERDE`; un parser lo lee entero |
| **D2 (un job secuencial ciega el codigo)** | el workflow se parte en **dos jobs paralelos**: `custodia` (6 pasos, stdlib pura) y `suite` (12 pasos) | un CSV viejo enrojece `custodia` sin ocultar `suite`. Verificado con parser YAML: 2 jobs, 6 y 12 pasos |
| **D3 (el control positivo muta el arbol real)** | aborta con exit 2 si `git status --porcelain` no esta limpio en los 3 archivos que muta; restauracion doble (copia + `git checkout --`); trap en EXIT, INT y TERM | probado en los dos sentidos: arbol limpio -> 7/7 cazadas; archivo sucio a proposito -> **exit 2, "No se midio nada"** |
| **D4 (descripcion del PR obsoleta)** | cuerpo del PR reescrito al alcance real | la pagina del PR ya no dice "cero codigo de producto" |
| **D5 (8 commits de convergencia a mano)** | `scripts/cerrar.sh`: regenera los recibos y **despues** exige `git status` limpio. Instalable como hook `pre-push` | A1 pasa a darse rojo antes del push en vez de despues |
| **A1 preventivo** | `.gitattributes` con `* text=auto eol=lf` | ningun hash del manifiesto depende de la plataforma del clon |

### 2.1 Lo que NO se hizo, y por que

El desglose por capa de la tabla de inventario (produccion / tests / fixtures /
scripts) **sigue siendo tipeado**: esa agrupacion es editorial y no existe en el
CSV, asi que `informe_vs_csv.py` **no la cubre**. Cubre la fila TOTAL y la cantidad
de archivos. Se declara aca en vez de dar la impresion de que todo el cuadro esta
atado. La suma de las cuatro capas contra la fila TOTAL se verifico a mano en esta
corrida y cierra, y eso es una verificacion de una vez, no un guard.

## 3. Inventario

Instrumento: `python3 scripts/inventario.py`. La fila TOTAL sale de
`evidencia/inventario.csv` y el CI falla si este informe cita otra.

| Capa | Archivos | Total | Codigo | Comentario | Docstring | Blanco |
|---|---:|---:|---:|---:|---:|---:|
| Produccion `fase0/` | 9 | 2.313 | 1.435 | 154 | 391 | 333 |
| Tests `fase0/tests/` | 8 | 1.474 | 904 | 6 | 291 | 273 |
| Fixtures | 2 | 175 | 130 | 15 | 11 | 19 |
| Scripts | 5 | 852 | 552 | 67 | 110 | 123 |
| **TOTAL Python** | **24** | **4.814** | **3.021** | **242** | **803** | **748** |

Lineas de codigo test/produccion: **0,63**. Ratio comentario+docstring/codigo:
**0,346**. Dependencias de terceros: 3, pinneadas exactas. Dependencias de test: 0.

**Sobre el 23 vs 24 de la pasada anterior:** el auditor tenia razon, eran 23. Ahora
son 24 porque esta revision agrega `scripts/informe_vs_csv.py`. Los otros 22
archivos se recomputaron aca fila por fila contra la recomputacion del auditor y
**coinciden las 22, incluida `fase0/fixtures/__init__.py = 1,0,0,1,0`**, que era la
causa raiz del rojo. Los unicos dos que cambian son los dos que se tocaron.

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
repetidos, omitidos e inventados se distinguen; `<<<` se neutraliza en ingesta; el
prompt estable tiene SHA-256 pinneado; el HTML se escapa; la tasa de cache tiene
tres estados (VERDE, ROJO, NO MEDIDO).

## 5. Verificacion

### 5.1 Estado del CI: lo que se puede y lo que no se puede afirmar

**No se afirma nada sobre CI ajeno en este head hasta que corra.** El ultimo verde
conocido al momento de escribir esto es `31178a1`, ocho commits atras, **antes** de
B1-B8. El head `de13b9a6` dio `failure` en los runs `34084699103` y `34084702756`.
Cualquier lectura de "verificado por CI ajeno" en la revision 2 valia para
`31178a1` y no para el arbol corregido: el auditor lo marco y es correcto.

Con el workflow partido, la afirmacion futura tiene que ser por job: `custodia`
verde significa que los recibos describen el arbol; `suite` verde significa que el
codigo funciona. Son dos cosas distintas y hasta ahora se reportaban como una. En
este head se espera `suite` verde y `custodia` roja en el paso del manifiesto, por
lo declarado en 1.1.

### 5.2 Instrumento propio, con evidencia cruda (W-01)

Corrido por BRAIN en su sandbox, Python 3.12, con las **tres dependencias en su
version pinneada exacta** (pydantic 2.13.4, weasyprint 69.0, pypdf 6.14.2), sobre
un arbol reconstruido y **verificado blob a blob contra `de13b9a6`**: 21 archivos
de codigo con SHA-1 de git identicos, o sea que lo que se midio es el arbol del
repo y no una copia parecida.

| Instrumento | Resultado |
|---|---|
| `unittest discover` | **128 tests, exit 0**, 1,288 s |
| conteo estatico de `def test_` | **128**, coincide con lo declarado |
| `control_positivo_suite.sh` | **7/7 cazadas por su test especifico**, arbol restaurado en verde |
| guard D3 del control positivo | **exit 2 con archivo sucio**: el guard puede dar rojo |
| `inventario.py` | 24 archivos parsean, las sumas cierran |
| `informe_vs_csv.py` | fila TOTAL del informe == CSV |
| `manifiesto.py --verificar` | verde en el sandbox; **rojo esperado en este head** (1.1) |
| pipeline `--dry-run --pdf` | 23 filas de 24, 1 duplicado colapsado, 2 llamadas, 1 lote, 23 analisis, **0 rechazos**, PDF de 4 paginas y 4.474 caracteres |
| `modelo_costo_arq3.py` | GUARD VERDE margen peak **96,28%** |
| `sensibilidad_infra_y_equipo.py` | corre completo; margen peak con el stack del blueprint (USD 395) **82,14%** |

El HTML es byte-determinista; el PDF **no**, porque WeasyPrint embebe el timestamp
de creacion (medido: 23.259 / 23.251 / 23.254 bytes en tres corridas, tres SHA
distintos). Por eso el peso del PDF no se cita como dato reproducible y `*.pdf`
esta marcado `binary` en `.gitattributes`.

### 5.3 Control positivo del guard nuevo

Un guard que no puede dar rojo es un adorno (defecto 10 de este registro). El de D3
se probo en los dos sentidos en la misma corrida:

```
arbol limpio    -> "arbol limpio en los archivos mutables: verificado con git status."
                   VERDE: 7/7 mutaciones cazadas por su test especifico.
arbol sucio     -> ABORTA: el arbol tiene cambios sin commitear ...
                    M fase0/report.py
                   Commitea o guarda esos cambios y volve a correr. No se midio nada.
                   exit=2
```

**Limitacion declarada que sigue en pie:** un `kill -9` o la muerte del sandbox no
ejecutan ningun trap, asi que pueden dejar un mutante vivo. Lo que cambia es que la
proxima corrida **se niega a arrancar** en vez de medir sobre un arbol contaminado,
y `custodia` lo enrojece en el CI. Chequeo manual: `grep -rn "# MUTANTE" fase0`.

## 6. Rubrica

**Externa vigente: 88/100** (segunda pasada, head `de13b9a6`). No se sube un solo
punto por cuenta propia. Lo que esta revision hace es atacar exactamente los dos
criterios que el auditor bajo, y el resultado de eso lo mide el auditor, no yo.

| Criterio | 1a pasada | 2a pasada (vigente) | Que se toco en esta revision |
|---|---:|---:|---|
| Ejecutabilidad | 15 | 13 | CI partido en dos jobs; recibos regenerados desde el arbol final |
| Seguridad | 12 | 13 | sin cambios (B3 y B7 ya cerrados) |
| Testing | 12 | 13 | guard de arbol limpio en el control positivo |
| Proceso QA | 2 | 1 | `informe_vs_csv.py`, `cerrar.sh`, `.gitattributes`, D1 |
| Resto | 48 | 48 | — |
| **Total** | **89** | **88** | **pendiente de tercera pasada** |

## 7. Estados NO MEDIDOS

1. Ninguna llamada real a `ads_archive`.
2. Ninguna llamada real a DeepSeek.
3. Calidad semantica del modelo (hace falta un golden set etiquetado a mano).
4. Review de Copilot: sin hallazgos emitidos **no es aprobacion** (K-02).
5. Precio y disposicion a pagar.
6. CAC y retencion.
7. Corpus comercial para LatAm: sin via legal identificada.
8. Residencia de datos (DeepSeek procesa en China, el corpus legal es europeo).
9. Umbrales exactos del tier estandar de Marketing API.
10. Formato de anuncio en produccion: ningun campo de `CAMPOS_ADS_ARCHIVE` lo informa, asi que la seccion 4 del PDF sera inerte. Hay que confirmar un campo oficial o retirar la seccion.
11. Resultados de pip-audit y gitleaks: van con `continue-on-error`, o sea que **todavia no son un control**.
12. Tercera revision externa de estas correcciones.
13. Cobertura de lineas: no hay instrumento. 128 tests no son una medida de cobertura.
14. El CI de este head: al cerrar el turno no habia corrido todavia. Ver 1.1 y 5.1.

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
22. **El primer `cerrar.sh` regeneraba recibos siempre, y por eso su chequeo de custodia daba ROJO SIEMPRE.** `unittest -v` imprime la duracion de la corrida ("Ran 128 tests in 1.356s"), asi que ese recibo cambia de bytes en cada ejecucion aunque el arbol sea identico, el manifiesto cambia con el, y `git status` nunca queda limpio. Es el defecto 13 exacto (guard autorreferente que grita siempre y por eso nadie lo mira) cometido DENTRO del instrumento que escribi para no volver a cometerlo. Correccion: dos modos, `--regenerar` y verificar, y la declaracion de que un recibo de corrida es una foto con su duracion adentro y no un artefacto reproducible.
23. **Mi propio `.gitattributes` preventivo casi rompe el manifiesto en cualquier clon fresco.** `csv.DictWriter` escribe CRLF por default, asi que `evidencia/modelo_costo_arq3.csv` tenia CRLF en el arbol de trabajo; con `* text=auto eol=lf` git guarda LF, un clon nuevo recibe LF, y el manifiesto (que firma bytes crudos) habria dado rojo por una diferencia que no es de contenido. Lo cazo `git` con un warning que estuvo a un caracter de pasar desapercibido. Correccion: `lineterminator="\n"` explicito en el escritor, no una excepcion en el `.gitattributes`. Una medida preventiva sin control positivo es una hipotesis.
24. **El informe se me quedo viejo mientras corregia otra cosa, y esta vez lo cazo el instrumento y no un humano.** Al agregar cinco lineas de comentario a `modelo_costo_arq3.py` la tabla del inventario dejo de coincidir con el CSV, y `informe_vs_csv.py` dio `GUARD ROJO: total informe=4805 csv=4811` antes de cualquier push. Es la septima aparicion de A1 y la primera que costo veinte segundos en vez de un ciclo de auditoria externa. Eso es la diferencia entre disciplina e instrumento, medida.
25. **Un recibo commiteado imprimia la ruta absoluta de mi sandbox** (`/home/.../cashgo/evidencia/...`). Dos problemas en una linea: no es reproducible en otro clon (el auditor recomputa y le da otra cosa) y filtra el layout de mi maquina a un archivo de evidencia publico. Correccion: ruta relativa a la raiz del repo. Lo encontre leyendo el recibo antes de pushearlo, que es exactamente lo que no habia hecho en las tres revisiones anteriores.
26. **Parti la convergencia en tres commits cuando la correccion pedida era UNO, y deje los recibos de evidencia sin regenerar en el repo.** El motivo es real y no es una excusa: el canal por el que escribo archivos tiene un limite de tamano por operacion y 105 KB no entraban. Lo que corresponde entonces es declararlo antes de que lo encuentre el auditor, no llamarlo "un solo commit". Esta en 1.1 con su consecuencia exacta: `custodia/manifiesto` va a dar rojo en este head.

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
bash scripts/control_positivo_suite.sh
python3 -m fase0.pipeline fase0/fixtures/brief_ejemplo.json \
  --dry-run fase0/fixtures/ads_archive_sample.json --salida /tmp/aud --pdf
python3 scripts/modelo_costo_arq3.py
python3 scripts/sensibilidad_infra_y_equipo.py

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

## 10. Veredicto

La Fase 0 esta implementada y sus ocho hallazgos de codigo (B1-B8) estan cerrados
con tests que pueden dar rojo. Los seis hallazgos de proceso (A1 y D1-D5) estan
cerrados con **instrumentos**, no con disciplina, y cada instrumento se probo en su
direccion negativa. En esta corrida, sobre el arbol convergido: **128 tests en
verde, 7/7 mutaciones cazadas por su test nominal, inventario e informe
consistentes entre si**. Lo que falta cerrar en el repo esta en 1.1, con nombre y
con el comando que lo cierra.

Lo que sigue sin medirse no se movio ni un milimetro: **funcionamiento contra APIs
reales, calidad semantica, tasa de cache y mercado**. Una de cuatro arquitecturas
tiene implementacion. El proximo movimiento correcto no es mas codigo: es la
verificacion de identidad en Meta, una llamada real a DeepSeek y un golden set
etiquetado a mano. Todo lo demas es afilar un instrumento que ya corta.
