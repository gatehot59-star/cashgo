# INFORME TECNICO PARA AUDITORIA EXTERNA - PROYECTO CASHGO

**Destinatario:** Fable 5.1 (Abacus.AI), pasada externa numero 3.
**Emitido:** 2026-09-09, 13:30 ART.
**Sujeto auditado:** rama `titan/auditoria-cashgo`, head `e78c9d1587e51c1618b20ccf57b7f724090e20d2`.
**Repositorio:** https://github.com/gatehot59-star/cashgo (publico, se lee sin credencial).

---

## 0. LEA ESTO PRIMERO: DOCUMENTOS QUE CIRCULAN Y ESTAN VENCIDOS

Va antes que cualquier numero propio, porque si usted entra por uno de esos documentos audita un sistema que no existe.

| Documento | Que declara | Que es verdad hoy |
|---|---|---|
| Doc de ClickUp "rubrica 94/100" | head `31178a1`, 21 modulos, 2.554 lineas, CI con 2 check runs en `success` | `31178a1` es del **2026-09-07 02:47 UTC**, 19 horas antes del head. Hoy: 26 modulos, 5.205 lineas, **5 jobs y 3 en rojo** |
| Descripcion del PR #1 | 2 jobs (`suite`, `custodia`) ambos en `success`, 128 tests, pip-audit con `continue-on-error` | 5 jobs, **3 en failure**, 144 tests, **cero** `continue-on-error` |
| `02-INFORME-PARA-AUDITORIA.md` (revision 5) | rubrica externa 88/100 vigente | Sigue siendo el dossier largo y su contenido tecnico vale, pero su firma en el manifiesto es drift conocido (defecto 38) y su rubrica quedo desactualizada por este informe |

El unico documento que describe el head real es **este**.

---

## 1. COMO CAERME SIN PEDIRME NADA

Todo numero de este informe se recomputa con esto:

```bash
git clone https://github.com/gatehot59-star/cashgo
cd cashgo && git checkout e78c9d1587e51c1618b20ccf57b7f724090e20d2

pip install -r fase0/requirements.txt      # pydantic 2.13.4, weasyprint 69.0, pypdf 6.14.2
python3 -m fase0.fixtures.generar

python3 -m unittest discover -s fase0/tests -t . -v   # esperado: 144 tests, exit 0
bash scripts/control_positivo_suite.sh                # esperado: 7/7 mutaciones cazadas por su test nominal
python3 scripts/inventario.py --csv | diff -u evidencia/inventario.csv -
python3 scripts/informe_vs_csv.py
python3 scripts/manifiesto.py --verificar
```

Y el CI ajeno, que es el instrumento que no controlamos: run `34162748294` sobre este head, en `ubuntu-24.04` limpio.

---

## 2. ESTADO REAL DEL CI, MEDIDO POR JOB

Leido por API sobre el head `e78c9d1`, run `34162748294`:

| Job | Conclusion | Bloqueante |
|---|---|---|
| `suite (el codigo funciona)` | **success** | no |
| `secretos (historial completo)` | **success** | si |
| `custodia (recibos vs arbol)` | **failure** | no |
| `deps-pins (CVEs en lo que pinneamos)` | **failure** | **si** |
| `deps-arbol (CVEs en el arbol transitivo)` | **failure** | **si** |

**3 de 5 en rojo, y 2 de esos 3 estan declarados BLOQUEANTES por el propio workflow.** Este head **no es mergeable** por el estandar que el repo se puso a si mismo. `mergeable_state` del PR: `unstable`.

Lo que **si** esta verificado por maquina ajena: los 144 tests, las 7 mutaciones del control positivo, el pipeline completo en `--dry-run`, el PDF, los dos modelos de costo, y gitleaks sobre los 30 commits del historial con `fetch-depth: 0`.

---

## 3. HALLAZGO NUEVO DE ESTA PASADA: HABIA UNA PALABRA EN RUSO DENTRO DE UN SHA256

El artefacto de custodia del repo, `evidencia/MANIFEST.sha256`, tenia esta linea:

```
a7b001b798125d11fb5e9f0c979a7a37a667374d5898d2061известноa696  scripts/inventario.py
```

61 caracteres, 69 bytes. Un sha256 tiene 64 y 64.

### 3.1 Antes de acusar al repo, verifiqué el sujeto (E-01)

Lo barato era culpar al canal de lectura. Prueba: reconstrui el archivo byte a byte y calcule su object id de git.

```
bytes reconstruidos: 1853   (la API reporta 1853)
git blob sha1      : 3c0a7e0230525ed494486d0570a95f0a676f3987
el de la API       : 3c0a7e0230525ed494486d0570a95f0a676f3987   -> COINCIDE
```

Si el object id coincide, el contenido es el commiteado. **La corrupcion estaba en el repo.** Se recomputa con `git cat-file -p 3c0a7e02`.

Segunda confirmacion, independiente de mi transporte: un manifiesto bien formado con esas 19 rutas mide **1.848 bytes**. La API reportaba **1.853**. La diferencia de 5 es exactamente lo que ocupa un campo de 69 bytes donde deberia haber uno de 64.

### 3.2 Forense: de donde salio

Los **primeros 49 caracteres hex son el digest real**. Los ultimos 15 fueron reemplazados por 12 caracteres, 8 de ellos cirilicos. Eso no es un bit flip: es una **sustitucion a nivel token**, o sea el defecto 27/36 de este repo (construir el contenido en el payload de escritura en vez de transportar el archivo) aterrizando en el unico archivo donde un caracter de mas invalida el instrumento completo.

### 3.3 Consecuencia medida

`manifiesto.py --verificar` compara digest contra digest y devuelve 1 ante cualquier diferencia. Con esa linea, el cuarto paso de `custodia` era **rojo por construccion**. Corregido en el mismo commit que este informe, con el digest recomputado del archivo real:

```
a7b001b798125d11fb5e9f0c979a7a37a667374d5898d2061349728909d6ebf6  scripts/inventario.py
```

### 3.4 Lo que este arreglo NO arregla

Verifique **1 de los 19** digests contra su archivo (`evidencia/inventario.csv`: `a2204c81...`, correcto). Los otros 17 siguen **NO MEDIDOS**, y uno tiene drift conocido y declarado: `02-INFORME-PARA-AUDITORIA.md`, 42 KB de prosa (defecto 38). **Si `custodia` sigue en rojo despues de este commit, la causa mas probable es esa linea.**

---

## 4. INVENTARIO, Y QUE PARTE RECOMPUTE YO

26 modulos Python: 9 en `fase0/`, 2 en `fase0/fixtures/`, 9 en `fase0/tests/`, 6 en `scripts/`. Mas 2 scripts bash y 11 archivos de evidencia cruda.

| Metrica | Valor |
|---|---|
| Lineas totales | 5.205 |
| Codigo | 3.202 |
| Comentario | 284 |
| Docstring | 902 |
| Blanco | 817 |
| Ratio test/produccion | 0,72 |
| Tests | 144, exit 0, 1,300 s |

**Lo que recompute yo hoy, con el instrumento del propio repo (`inventario.contar`):**

- La fila TOTAL, sumada desde las 26 filas del CSV: `5205 / 3202 / 284 / 902 / 817`. Coincide.
- En las 26 filas, `total == codigo + comentario + docstring + blanco`. Cierra en todas.
- Recuento linea por linea de **2 archivos de 26** (7,7 % de muestra, declarada): `fase0/dedup.py` -> `(68, 38, 0, 16, 14)` y `scripts/inventario.py` -> `(217, 134, 11, 41, 31)`. **Identicos al CSV.**
- **Los otros 24 archivos: NO MEDIDOS por mi en esta pasada.** El CI los mide en `custodia`, y `custodia` esta en rojo, asi que no se puede delegar en el.

**Integridad de mi propio canal de lectura**, porque un auditor no tiene por que creer que lo que lei es lo que hay: recompute el `git blob sha1` de los 4 archivos que baje. **4 de 4 coinciden** (`dedup.py` 2.013 B, `inventario.py` 8.504 B, `inventario.csv` 1.123 B, `MANIFEST.sha256` 1.853 B). Por eso puedo afirmar que lo que difiere, difiere de verdad.

---

## 5. QUE ES EL SISTEMA Y QUE NO PUEDE HACER

Fase 0 es un generador de informes de inteligencia competitiva publicitaria. Cadena: **API oficial `ads_archive` de Meta -> SQLite con audit log append-only -> dedup por hash de contenido -> estructuracion con DeepSeek -> agregacion 100 % determinista -> informe HTML/PDF**.

Tres propiedades que importan para auditar el riesgo:

1. **No puede gastar dinero de nadie.** No hay credencial de escritura sobre ninguna cuenta publicitaria en todo el arbol. El LLM nunca porta la credencial (regla 0 de `ADR-CG-001`).
2. **La palanca de costo no tiene IA.** El dedup es un `SELECT`: 52.800 de 60.000 anuncios por corrida no vuelven a pagar tokens (88 %, medido en `scripts/modelo_costo_arq3.py`).
3. **La agregacion es determinista.** El modelo estructura texto; ningun numero del informe final sale de un LLM.

### Limite duro de producto, y es geografico, no tecnico

La cobertura oficial de anuncios **comerciales** de la Ad Library es **UE / UK / EEE**, por el DSA. El codigo **rechaza** paises como US, AR, BR, MX y CA **antes** de hacer la llamada. El corpus comercial para LatAm **no tiene via legal identificada**. Su precio es geografia, no dinero.

---

## 6. ESTADOS NO MEDIDOS (la parte que decide el veredicto)

1. **Cero llamadas reales a `ads_archive`.** Falta la verificacion de identidad en Meta, que es un click del titular y no se puede delegar. Al 2026-09-07 el titular estaba en el paso "Elige un motivo".
2. **Cero llamadas reales a DeepSeek.** Falta `DEEPSEEK_API_KEY` con saldo.
3. **Calidad semantica.** Hace falta un golden set de ~100 anuncios etiquetados a mano. El `--dry-run` usa un clasificador por reglas: valida el **pipeline**, nunca la **calidad**.
4. **Causa exacta del rojo de `deps-pins` y `deps-arbol`.** El gate ya publica su JSON como artifact (`deps-pins-informe`, `deps-arbol-informe`, retencion 14 dias), pero **ninguna herramienta de este equipo puede abrir el log de un job ni bajar un artifact**, y el sandbox no tiene red para reproducir pip-audit. Se descarto ya una hipotesis (el pip precocido del runner: se agrego `--upgrade pip` y los dos jobs siguieron rojos).
5. **Que paso de `custodia` falla primero.** El del manifiesto era rojo por construccion (seccion 3), pero cual corta el job es NO MEDIDO por lo mismo del punto 4.
6. **17 de 19 digests del manifiesto.**
7. **24 de 26 filas del inventario**, en esta pasada.
8. **Tasa de acierto de cache.** El instrumento existe (tabla `uso_tokens`), el numero no. De ese numero depende el margen del 96,28 %.
9. **Mercado:** precio, disposicion a pagar, CAC, retencion. Con breakeven en 2 suscriptores, ese es el riesgo real del negocio y no tiene una linea de codigo.
10. **Residencia de datos:** DeepSeek procesa en China y el corpus legal es europeo.
11. **Cobertura de lineas:** sin instrumento. 144 tests no son una medida de cobertura.
12. **Copilot:** pedido dos veces sobre el PR #1, `get_reviews` devuelve `[]`. **Ausencia de hallazgos no es aprobacion** (K-02).

---

## 7. DEFECTOS PROPIOS DE ESTA PASADA

**39. Una palabra en ruso dentro de un sha256 commiteado.** Seccion 3. El patron es el defecto 27/36 por septima vez, y esta vez cayo en el archivo donde mas caro sale.

**40. El generador de creativos del turno anterior no existe.** Se escribio, se probo con 18 tests y **nunca se pusheo**; el sandbox se limpio. `fase0/` no tiene `creative.py`. Son **0 lineas entregadas**, no "pendiente de push": lo que no esta en git no existe. La regla del repo ("commitear ANTES de redactar el chat") estaba escrita y se incumplio.

**41. D4 se reabrio.** La descripcion del PR #1 volvio a quedar vencida y hoy declara un CI que no existe. Un auditor que entra por esa pagina lee 2 jobs verdes donde hay 3 rojos.

**42. La rubrica que circula (94/100) describe un head de 19 horas antes.** Un numero de calidad sin head al lado es propaganda.

---

## 8. RUBRICA: 70 / 100

Baja desde los 88/100 externos vigentes. **Ninguna linea de codigo empeoro.** Lo que cambio es que se conto el rojo del CI en Ejecutabilidad y el manifiesto corrupto en Custodia. Un numero que sube cuando la medicion mejora es un numero que no mide.

| # | Criterio | Peso | Puntos | Por que |
|---|---|---|---|---|
| 1 | Veracidad de las afirmaciones cuantitativas | 10 | 9 | Cada cifra tiene instrumento y comando. Descuento: 24 filas del inventario no las recompute yo |
| 2 | Falsabilidad de los instrumentos | 10 | 9 | Control positivo por mutacion donde cada una cae por su test nominal. El gate de deps separa 3 estados |
| 3 | Ejecutabilidad verificada por maquina ajena | 15 | 6 | 3 de 5 jobs en rojo, 2 bloqueantes. `suite` verde no compensa |
| 4 | Seguridad de la frontera de ingesta | 15 | 12 | H-01 cerrado con 16 tests y control positivo. Descuento: los dos portones de CVE no pueden dar veredicto |
| 5 | Trazabilidad y custodia | 15 | 6 | El artefacto de firma tenia un digest invalido y el informe largo tiene drift declarado |
| 6 | Arquitectura y contratos | 10 | 9 | Frontera determinista/cognitiva explicita, esquemas cerrados, cero credencial de escritura |
| 7 | Cobertura de verificacion | 10 | 7 | 144 tests sin red. Cero cobertura de lineas medida |
| 8 | Honestidad de lo NO MEDIDO | 10 | 9 | 12 estados declarados, incluidos los que dejan al proyecto sin producto |
| 9 | Revision externa independiente | 5 | 3 | Una sola pasada verdaderamente independiente (Tao). Copilot NO MEDIDO |
| | **TOTAL** | **100** | **70** | |

---

## 9. SEIS VERIFICACIONES ADVERSARIALES (para que usted pueda darme rojo)

1. **`git cat-file -p 3c0a7e02`** en el commit anterior a este. Si esa linea no tiene la palabra `известно`, la seccion 3 entera es falsa.
2. **`python3 scripts/manifiesto.py --verificar`** en este head. Si devuelve 0, mi advertencia sobre `02-INFORME-PARA-AUDITORIA.md` era pesimismo. Si devuelve 1, lea **que ruta** imprime: eso es el dato que a mi me falto.
3. **`python3 scripts/inventario.py --csv | diff -u evidencia/inventario.csv -`.** Si difiere, el CSV que use como base esta mal y la seccion 4 se cae.
4. **Revierta `fase0/schemas.py` a `0b0bc52^`** y corra la suite. Tienen que caer **5** tests nombrando `ad_id`, `page_id`, `plataformas`, el lote y la promesa de la victima, y **tiene que quedar verde** `test_el_copy_esta_neutralizado`. Si cae tambien ese, el parche rompio lo que ya funcionaba. Si no cae ninguno, H-01 era falso.
5. **Baje el artifact `deps-pins-informe`** del run `34162748294`. Si el JSON dice `vulnerabilities` no vacio, el rojo es de SEGURIDAD y yo lo dejo en NO MEDIDO cuando el dato estaba publicado. **Esa es la falla mia mas probable de este informe.**
6. **`grep -r creative fase0/`.** Tiene que dar vacio. Si algo aparece, el defecto 40 esta mal contado.

---

## 10. VEREDICTO

El sistema **esta construido, es coherente y esta verificado contra fixtures por una maquina ajena**. Su funcionamiento contra las APIs reales es **cero medido**, y **no por falta de codigo: por falta de un click de verificacion de identidad en Meta**.

El proximo movimiento correcto **no es mas codigo**. Es, en orden:

1. Cerrar la verificacion de identidad en Meta y hacer **una** llamada real a `ads_archive` sobre un anunciante UE/UK.
2. Bajar los dos JSON de deps y convertir el punto 4 de la seccion 6 en verde o en rojo **con nombre de CVE**.
3. Partir `custodia` en cuatro jobs, uno por pregunta, porque el nombre del check run es el unico canal de diagnostico que este equipo puede leer sin abrir un log. Es la misma regla que el workflow ya aplica un nivel mas arriba.
4. Un golden set de ~100 anuncios etiquetados a mano.

Todo lo demas es afilar un instrumento que ya corta.
