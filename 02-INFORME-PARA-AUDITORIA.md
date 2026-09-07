# INFORME PARA AUDITORIA · CASHGO al 2026-09-06

**Sujeto auditado:** todo lo producido en la jornada del 2026-09-06 sobre el repo
`gatehot59-star/cashgo`, creado ese mismo dia.
**Modo:** TITAN FULL · **Tipo de entrega:** codigo de produccion + auditorias + ADRs
**Como leer esto:** cada afirmacion lleva su instrumento al lado. Lo que no se midio
dice NO MEDIDO. No hay una tercera categoria.

---

## 0. EL DATO QUE CAMBIA EL ESTADO DEL PROYECTO

> ### Por primera vez hay un verde que NO es mio.

**Instrumento:** GitHub Actions, workflow `fase0`, sobre el head sha `34a34d3`.
**Resultado:** 2 check runs `suite`, `status: completed`, **`conclusion: success`**,
28 segundos.

| | |
|---|---|
| Maquina | `ubuntu-24.04` limpio, provisto por GitHub |
| Dependencias | instaladas desde cero con `pip install -r fase0/requirements.txt` |
| Fixtures | generados en la maquina, no commiteados |
| Que corrio | 101 tests + control positivo por mutacion + pipeline end to end + PDF + los dos modelos de costo |
| Red | **ninguna llamada a Meta ni a DeepSeek**: el pipeline corre contra fixture |

Por que importa mas que todos los verdes anteriores: **hasta ahora cada "exit 0" de
esta jornada salio de mi propio sandbox**, con las librerias ya instaladas y el
arbol ya armado por mi. Este lo emitio una maquina que no es mia, que se bajo el
repo desde cero y que no sabe que se esperaba de ella. El instrumento no tiene
lealtades, y este ademas no es el mio.

### Y la contracara, que va declarada y no tapada (K-02)

> **Copilot NO emitio hallazgos. `get_reviews` devuelve `[]`.**
>
> **Eso no es una aprobacion. Es un estado NO MEDIDO**, y se escribe asi. Pedi el
> review dos veces sobre el PR #1 y al momento de emitir este informe no hay ni un
> comentario. "Nadie objeto" y "lo revisaron y esta bien" no son lo mismo, y
> confundirlos convierte un control en un adorno. Queda como **deuda abierta**.

---

## 1. QUE TENEMOS · inventario medido, no recordado

**PR #1:** 7 commits, 37 archivos, +5.609 lineas, `mergeable_state: clean`, sin mergear.

### 1.1 Codigo que corre (2.132 lineas)

| Lineas | Archivo | Que hace |
|---|---|---|
| 397 | `fase0/pipeline.py` | orquestador + CLI con `--dry-run` |
| 343 | `fase0/report.py` | agregacion determinista + HTML + PDF |
| 296 | `fase0/cognitive.py` | la unica capa con LLM. Prefijo estable + validacion |
| 284 | `fase0/adlibrary.py` | cliente `ads_archive`: batch, cursor, backoff 613 |
| 226 | `fase0/schemas.py` | contratos Pydantic. Aca vive el guard de inyeccion |
| 186 | `fase0/store.py` | SQLite + audit log append-only |
| 174 | `fase0/fixtures/generar.py` | datos de prueba como codigo |
| 145 | `fase0/config.py` | allowlist del DSA, limites, pins de modelo |
| 68 | `fase0/dedup.py` | la palanca del 88% del costo. Cero IA |

### 1.2 Verificacion (1.158 lineas de tests + 79 de control positivo)

| Lineas | Archivo | Tests |
|---|---|---|
| 267 | `tests/test_cognitive.py` | 23 |
| 234 | `tests/test_e2e_pipeline.py` | 19 |
| 232 | `tests/test_report.py` | 20 |
| 179 | `tests/test_adlibrary.py` | 20 |
| 157 | `tests/test_schemas_y_dedup.py` | 19 |
| 88 | `tests/apoyo.py` | (fabricas y dobles) |
| 79 | `scripts/control_positivo_suite.sh` | **audita la suite, no el codigo** |

**Total: 101 tests, exit 0.** Desglose por clase recontado con el loader en
`evidencia/salida_tests_fase0.txt`.

### 1.3 Instrumentos de medicion (444 lineas)

| Archivo | Que mide | Puede dar rojo |
|---|---|---|
| `scripts/modelo_costo_arq3.py` | costo y margen de la Arq 3 | si: guard a 80% de margen |
| `scripts/sensibilidad_infra_y_equipo.py` | barrido de infra + semanas-persona | si: valida coherencia de supuestos |
| `scripts/control_positivo_suite.sh` | **si la suite puede dar rojo** | si: y **dio rojo la primera vez** |

### 1.4 Documentos de decision

`00-AUDITORIA-CASHGO.md` · `01-CONTRASTE-CON-BLUEPRINT-EXTERNO.md` ·
`ADR-CG-001-guardrails-financieros.md` · `ADR-CG-002-fusion-de-guardrails.md` ·
`CONTEXTO-CASHGO.md` · `fase0/README.md`

### 1.5 Evidencia cruda commiteada (372 lineas)

Seis salidas verbatim en `evidencia/`, incluida **la corrida FALLIDA del control
positivo**, que se deja a proposito porque es el hallazgo mas util del dia.

### 1.6 El entregable que un cliente veria

PDF de **4 paginas**, 23.258 bytes, 4.474 caracteres de texto extraibles,
generado sin tocar la red. Verificado con `pypdf`, no grepeando bytes.

---

## 2. DONDE ESTAMOS SEGUN LA COMPETENCIA

### La respuesta corta, sin maquillaje

> **No competimos todavia.** Ellos tienen producto vivo con clientes pagando.
> Nosotros tenemos **1 de 4 arquitecturas**, sin una sola corrida contra la API
> real y sin un cliente. La brecha no es de calidad de codigo: es de existencia.

### La tabla, 12 dimensiones

| Dimension | Adspirer | Markifact | Meta oficial | CASHGO hoy |
|---|---|---|---|---|
| Producto vivo con clientes pagando | **SI** | **SI** | SI (gratis, beta) | **NO** |
| Precio publico | $0/49/99/199 | no publicado | gratis en beta | sin precio |
| Plataformas de ads conectadas | 6 | 10+ | 1 (Meta) | **0** |
| Operaciones expuestas | 400+ tools | 1000+ ops / 8 meta-tools | 82 tools | **0** |
| Escritura en cuentas de ads | si, PAUSED | si, HITL 4 pasos | si, PAUSED | NO (por diseno) |
| Aprobado por Meta como tech provider | si | si | es Meta | no aplica todavia |
| Corpus de Ad Library propio | no | **si (MCP propio)** | no (prohibido) | pipeline listo, corpus vacio |
| Une ads con margen por SKU | no | no | no | disenado, sin construir |
| Ledger de gasto con proyeccion | no | no | no | 12 reglas en ADR, sin construir |
| Suite de tests publica | no visible | no visible | n/a | **101 tests, CI verde** |
| Control positivo de la suite | no visible | no visible | n/a | **3/3 mutaciones cazadas** |
| Trafico web mensual | — | ~95k (jun-2026) | — | **0** |

### Las tres cosas en las que estamos adelante, y por que ninguna es un moat todavia

1. **Sabemos que la capa de conexion no es negocio.** Ellos venden a $49-199 lo
   que Meta abrio gratis el 29-abr y a cualquier developer el 16-jul. Nosotros
   **no vamos a construir eso**. Es una ventaja de decision: nos ahorra el
   trimestre que costaria llegar a un mercado con techo de precio.
2. **Los guardrails financieros son mas profundos que el estandar del sector.**
   Los tres ponen el freno en el chat; nuestro ADR lo pone en el ledger, y suma
   `spend_cap` de Meta, que es el unico guard que sobrevive a que se caiga nuestra
   propia infra. **Todavia no esta construido.**
3. **Disciplina de verificacion que ellos no muestran.** 101 tests, CI publico, y
   un control positivo que audita la suite. **Eso no lo compra ningun cliente**,
   pero es lo que hace que las tres afirmaciones de arriba sean auditables en vez
   de un pitch.

### Y la unica ventaja que podria ser un moat real, con su condicion

> **Union de performance de ads x margen real por SKU.** Ellos optimizan ROAS
> porque es lo unico que ven desde la API de ads. Con Shopify conectado se puede
> pausar un ad set con ROAS 4 y margen negativo, y eso ellos
> **estructuralmente no pueden hacerlo**: no es que no se les ocurrio, es que no
> tienen el dato.
>
> **Condicion:** requiere las Fases 2 y 3. Hoy es una hipotesis con un diseno, no
> una ventaja. Y el reloj corre: nada impide que Markifact conecte Shopify manana.

---

## 3. PARA QUE SIRVE EL BRIEF

El `brief.json` es **el pedido de trabajo de una auditoria**. Es lo unico que hay
que escribir a mano para producir un PDF vendible, y son cinco datos:

```json
{
  "prospecto_page_id": "1001",
  "prospecto_nombre": "Mi Tienda DTC",
  "nicho": "e-commerce de hogar y deco",
  "competidores_page_ids": ["2001", "2002", "2003", "2004"],
  "paises": ["ES", "DE", "FR", "IT", "NL", "GB"]
}
```

| Campo | Que es | De donde sale |
|---|---|---|
| `prospecto_page_id` | la pagina de Facebook del cliente al que le vas a vender | buscador publico de la Ad Library |
| `prospecto_nombre` | como aparece en la tapa del PDF | vos |
| `nicho` | texto que va en el encabezado | vos |
| `competidores_page_ids` | contra quien lo comparas | vos, o el propio cliente |
| `paises` | mercados a consultar | **solo UE/UK**: es un guard duro |

**Ojo con dos cosas:**

1. Son `page_id` de **paginas de Facebook**, NO de cuentas publicitarias. La Fase 0
   no tiene acceso a ninguna cuenta publicitaria de nadie: por eso puede correr
   antes de que exista el ledger.
2. Poner `US` o `AR` **aborta con `AlcanceComercialError`**. No es un bug: la API
   oficial no devuelve anuncios comerciales fuera de la UE y UK. Devolver una lista
   vacia seria peor, porque alguien la leeria como "el competidor no anuncia".

**La eleccion de los competidores es la decision humana que mas mueve la calidad
del informe**, y no la automatiza nada de esto. Cuatro competidores bien elegidos
dan un informe que se vende; diez mal elegidos dan una tabla larga que no dice nada.

---

## 4. RUBRICA, CON EVIDENCIA POR CRITERIO

Los 9 criterios aplican: el sujeto es codigo de produccion. **Cero N/A.**

| # | Criterio | Pts | Evidencia |
|---|---|---|---|
| 1 | Completitud | 15/15 | 0 TODO, 0 placeholder, 0 `pass` vacio. Los 9 modulos importan y corren |
| 2 | Ejecutabilidad | 15/15 | CI en ubuntu-24.04 limpio: `pip install` + 101 tests + PDF, **success** |
| 3 | Seguridad | 14/15 | inyeccion cubierta por esquema (`TestInyeccionEnElCopy`), escapado con barrido, `sin_urls`, Regla 9 cableada en `Settings.validar()`. −1: **no corrio ningun escaneo de dependencias ni de secretos sobre este arbol** |
| 4 | Testing | 14/15 | 101 tests + **control positivo por mutacion 3/3**. −1: sin medicion de coverage por linea; el control positivo cubre 3 propiedades, no el arbol entero |
| 5 | Arquitectura | 10/10 | capas separadas por criterio explicito (si cuesta plata es determinista); transporte y completion inyectables; el LLM no sabe que existe Meta |
| 6 | DevOps | 9/10 | workflow completo, corre sin red, sube el PDF como artifact. −1: sin deploy: la Fase 0 es un CLI, no un servicio |
| 7 | Documentacion | 10/10 | README con quick start ejecutable, 6 variables de entorno explicadas, 2 ADRs, limites del producto en el propio PDF |
| 8 | Innovacion | 4/5 | control positivo por mutacion, reconciliacion del modelo contra el codigo, `sin_urls`, fixtures como codigo. −1: ninguna es un aporte al producto, son al metodo |
| 9 | Proceso QA | 3/5 | cada score con archivo o instrumento. −2: **el review externo no emitio hallazgos, o sea que un control quedo NO MEDIDO** (K-02) |

### **TOTAL: 94/100** · umbral 90 · **APROBADO con la deuda del punto 9 declarada**

---

## 5. LOS 9 "NO MEDIDO", QUE ES LA SECCION QUE UN AUDITOR TIENE QUE LEER PRIMERO

| # | Que | Por que importa | Como se cierra |
|---|---|---|---|
| 1 | **Ninguna llamada real a `ads_archive`** | `transporte_http()` esta escrito contra la doc y no ejecutado | verificacion de identidad en `facebook.com/ID` + app de developer + 1 corrida |
| 2 | **Ninguna llamada real a DeepSeek** | idem `cliente_deepseek()` | 1 corrida con API key |
| 3 | **Calidad de clasificacion del modelo** | el clasificador del `--dry-run` son heuristicas de palabra clave. Valida el pipeline, **no la calidad** | set anotado a mano de ~100 anuncios |
| 4 | **Review externo sin hallazgos** | K-02: no es aprobacion | reintentar Copilot o un revisor humano |
| 5 | **Precio y disposicion a pagar** | USD 79 x 30 suscriptores es un supuesto del modelo | hablar con 5 prospectos |
| 6 | **CAC y retencion** | con 96% de margen y breakeven en 2, **el riesgo del negocio no es el costo**: es conseguir a los 30 | planilla, cero codigo |
| 7 | **Corpus para LatAm** | no hay camino legal identificado. Un prospecto que solo pauta en Argentina **no tiene corpus** | decidir: vender UE/UK, o comprar dato (~EUR 329/mes) |
| 8 | **Residencia de datos** | DeepSeek procesa en China; el corpus legal es europeo | revision antes de que entre dato personal |
| 9 | **Umbrales del tier standard del Marketing API** | leidos de una fuente con el texto recortado | App Review dashboard |

**Los 1, 2 y 3 son los que impiden decir que la Fase 0 funciona.** Hoy lo correcto
es: *la Fase 0 esta construida y verificada contra fixtures por un instrumento
independiente; su funcionamiento contra las APIs reales es NO MEDIDO.*

---

## 6. DEFECTOS PROPIOS DE LA JORNADA, PARA QUE EL AUDITOR NO LOS TENGA QUE BUSCAR

| # | Defecto | Quien lo cazo | Patron |
|---|---|---|---|
| 1 | Hueco de cobertura: test contra la fecha de FIN en el hash, ninguno contra la de INICIO | **el control positivo** | sesgo de seleccion: elegi que medir |
| 2 | Analisis indexados por `ad_id`: la 2da corrida daba un informe **distinto** para el mismo corpus | test de determinismo entre corridas | invisible en una sola corrida |
| 3 | `reintentos_613` contaba el 613 final que hace abandonar (6 vs 5) | test de rate limit | metrica que no coincide con su fenomeno |
| 4 | Veredicto con "8 a 17 meses" hardcodeado contra 6,9 y 13,9 calculados | releer el stdout | escribi la conclusion antes de mirar el numero |
| 5 | Sobreestime el prefijo del prompt 12x en el modelo de costo | reconciliacion contra el codigo | supuesto tratado como medicion |
| 6 | Recibo de tests decia 100 cuando eran 101 | recontar con el loader | un conteo mal hace desconfiar del resto |
| 7-9 | Tres falsos rojos de mis propios tests (`{` en el prefijo, `onload=`, `/Type /Page`) | los propios tests | medi un substring en vez de la propiedad |

Los nueve estan anotados **en el codigo o en la evidencia**, con la leccion, no en
una lista aparte que nadie abre.

---

## 7. VEREDICTO

**Lo que se puede afirmar:** existe un pipeline completo de la Arquitectura 2,
verificado por 101 tests y por un CI ajeno en una maquina limpia, que produce un
PDF de 4 paginas a partir de datos de la Ad Library, con los guardrails de
inyeccion cableados en el esquema y no en el prompt. El metodo esta por encima del
estandar visible de los competidores.

**Lo que NO se puede afirmar:** que funciona. Cero llamadas reales, cero clientes,
cero pesos facturados.

**El cuello de botella dejo de ser tecnico.** Los tres bloqueos de arriba se
resuelven con dos tramites de dias de calendario y una conversacion comercial, no
con codigo. Cualquier linea adicional de Python antes de eso es trabajo sobre una
hipotesis sin validar, y ese es el error que este informe existe para prevenir.
