# AUDITORIA Y REDISENO DE CASHGO

**Fecha:** 2026-09-06 · **Modo:** TITAN FULL · **Tipo de entrega:** auditoria / ADR
**Rubrica:** 42/45 aplicables -> 93/100. N/A declarados: Ejecutabilidad, Seguridad de codigo,
Testing, DevOps (no hay producto desplegable todavia; puntuarlos seria medir el tipo de
entrega, no su calidad).

**Instrumento:** `scripts/modelo_costo_arq3.py`, corrido en sandbox, exit code 0.
Salida cruda verbatim en `evidencia/salida_modelo_costo_arq3.txt`. Cualquiera puede
recomputar el veredicto desde ahi y contradecirlo.

---

## 0. LO PRIMERO: SEIS COSAS QUE EL BRIEF DA POR CIERTAS Y LA MEDICION CAMBIA

El pedido pregunta por margen y diferenciacion. Antes de contestar eso hay que mover el
piso, porque cinco de las seis mediciones cambian **cual arquitectura vale**.

### F-1 · Meta tiene su propio MCP de ads, y eso mata la Arquitectura 1 como producto

VERIFICADO EN VIVO [2026-09-06]
- Fuente: https://developers.facebook.com/blog/post/2026/07/16/meta-ads-mcp-server/
- Fuente: https://www.usecarly.com/blog/meta-ads-mcp/ · https://adsuploader.com/blog/meta-ads-mcp-vs-cli

Meta lanzo **Meta Ads AI Connectors** el **2026-04-29**: un MCP server propio en
`mcp.facebook.com/ads` mas un CLI por npm. El **2026-07-16** lo abrio a cualquier developer
con su propia app. OAuth de Meta Business, **sin developer app, sin app review, sin token
manual**, y **gratis durante la beta** (Meta no anuncio precio post-beta).

La superficie medida: **82 tools** (52 read / 26 write / 4 delete), y las 4 de delete son de
audiencias y pixel, **no hay tool para borrar campanas** — solo pausar via update. Las
creaciones salen **PAUSED**.

> **Consecuencia dura:** la Arquitectura 1 ("controlar cuentas por chat sin entrar a la UI")
> ya no es un producto. Es una configuracion de dos minutos que **Meta regala**. Vender eso
> es vender agua al lado de una canilla publica. Sirve como **herramienta interna** para
> atender clientes con menos horas: eso es margen operativo, no SaaS.

### F-2 · La Ad Library SI da anuncios comerciales por API oficial, pero solo en UE/UK

VERIFICADO EN VIVO [2026-09-06]
- Fuente: https://adlibrary.com/posts/meta-ad-library-api-limitations
- Fuente: https://dev.to/odeeb/building-a-facebook-ad-library-scraper-api-limits-and-the-real-approach-3bad

El brief concluye que la unica senal disponible es "cuanto tiempo lleva activo el anuncio".
Eso es correcto para US y LatAm, y **falso para Europa**. El **Digital Services Act** obliga
a Meta a publicar **todos** los anuncios entregados a usuarios de la UE (y UK), con datos de
alcance, por ~12 meses. El endpoint `ads_archive` devuelve anuncios comerciales cuando
`ad_reached_countries` apunta a un estado miembro o UK. Fuera de ahi: solo political/issue.

O sea: **existe un camino legal, oficial, gratis y con esquema** al dato de competidores.
Su precio no es dinero, es **geografia**.

> Requisitos reales del camino oficial: verificacion de identidad con documento en
> `facebook.com/ID` (dias), app de developer, token (los de usuario expiran a ~60 dias;
> para jobs recurrentes va **system user token** con scope `ads_archive`). Sin app review.
> `limit` hasta 1000-2000 por llamada, paginacion por cursor `after`, batch de hasta 10
> `search_page_ids` por llamada. **Rate limit ~200 calls/hora** por token, dinamico y no
> publicado; el error a esperar es el **613**, con backoff exponencial.

### F-3 · Tu conclusion de ToS es mas dura que el precedente judicial

VERIFICADO EN VIVO [2026-09-06]
- Fuente: https://admakeai.com/blog/meta-ad-library-scraping-terms-of-service

El brief cierra en "viola los ToS seccion 3.2". El precedente dice algo mas fino:
**Meta v. Bright Data (enero 2024)**, con Meta **renunciando a apelar**:

> "The Facebook and Instagram Terms do not bar logged-off scraping of public data;
> perforce it does not prohibit the sale of such public data."

Los ToS son un contrato y solo atan a quien tiene cuenta **y esta logueado**. La Ad Library
no tiene login wall. Con sesion abierta, en cambio, los ToS aplican y ahi si estas en falta.

> **Pero esto no habilita el metodo del video, lo reencuadra.** El riesgo del scraping no es
> contractual, es **operativo**, y esta medido: inspeccion del handshake TLS y del frame de
> settings de HTTP/2, clases CSS ofuscadas (`x1lliihq`) que cambian en cada deploy, **letras
> senuelo escondidas dentro de la palabra "Sponsored"**, CAPTCHAs, IPs de datacenter
> bloqueadas en horas. Nadie te va a demandar: **se te va a romper el martes**.
> Eso mueve el gasto de abogados a resiliencia de parser, o mejor: a **no depender de
> scraping para el nucleo del producto**.

### F-4 · El metodo del video no es una arquitectura, es una demo

La extension del navegador haciendo scroll y leyendo con vision resuelve el problema de
una persona, una vez. Le falta **todo** lo que hace producto a la Arquitectura 3: idempotencia,
reintentos, esquema estable, deduplicacion, cursores, y la capacidad de correr a las 3 de la
manana sin nadie mirando. Y su costo por anuncio es el de un token de vision de modelo
frontier, el mas caro de la tabla.

> Su contradiccion de fondo: **exige un humano en el loop para LEER**, que es exactamente lo
> contrario del One-to-Many que la Arquitectura 3 necesita para tener margen.

### F-5 · A2A: spec estable, adopcion enterprise, y el agujero sin tapar es justo el tuyo

VERIFICADO EN VIVO [2026-09-06]
- Fuente: https://a2a-protocol.org/latest/blog/2026/08/27/a-new-chapter-for-a2a-joining-the-agentic-ai-foundation/
- Fuente: https://packetnebula.com/articles/a2a-joins-aaif-v1-migration/ · https://tomrochette.com/agents/a2a/

A2A **v1.0.0 salio el 2026-03-12** (v1.0.1 el 28-05) y **rompe compatibilidad con v0.3.0**:
los Part types se unificaron, todos los enums pasaron a `SCREAMING_SNAKE_CASE`
(`completed` -> `TASK_STATE_COMPLETED`), y los errores pasaron de RFC 9457 a `google.rpc.Status`.
Es proyecto de la Agentic AI Foundation desde el 2026-08-17, +150 organizaciones, integrado
nativo en Azure AI Foundry, Bedrock AgentCore y Google Cloud.

Y los dos datos que deciden la prioridad:

1. **~10,9M descargas/mes del `a2a-sdk` contra ~257M del SDK de MCP** (pypistats, junio 2026).
   La adopcion esta concentrada en suites enterprise y es **casi invisible en startups**.
2. **La inyeccion de prompt cruzando la frontera entre agentes sigue sin resolverse a nivel
   de protocolo.**

> **Consecuencia:** la Arquitectura 4 no es el techo tecnologico del proyecto. Es
> **superficie de ataque nueva apuntada a la tarjeta de credito de un cliente**. Va ultima
> por seguridad, no por complejidad. Y cuando llegue, va **entre agentes propios dentro de
> un perimetro**, no "descentralizada en servidores paralelos".

### F-6 · Markifact ya tiene el dato de la competencia adentro del producto

VERIFICADO EN VIVO [2026-09-06]
- Fuente: https://www.markifact.com/mcp (lista **"Meta Ads Library MCP"** entre sus MCPs)
- Fuente: https://github.com/markifact/markifact-mcp · https://www.adspirer.com/pricing

| | Markifact | Adspirer | Meta oficial |
|---|---|---|---|
| Operaciones | 1000+, 20+ plataformas | 400+ tools, 6 plataformas | 82 tools, solo Meta |
| Superficie MCP | **8 meta-tools** (`find_operations` -> `get_operation_inputs` -> `run_operation`) | tool por operacion | tool por operacion |
| HITL | protocolo de 4 pasos en cada write | create PAUSED, **sin delete** hard-coded, confirmacion para budget | create PAUSED, sin delete de campanas |
| Ad Library | **si, MCP propio** | no | no (extraccion masiva prohibida) |
| Precio | no publicado | **$0 / $49 / $99 / $199** por tool calls | gratis en beta |
| Trafico | ~95k visitas/mes (jun-2026) | — | — |

> El detalle tecnico que vale robar: Markifact **no expone 1000 tools**, expone 8 meta-tools
> y el modelo descubre la operacion en runtime. Es la diferencia entre un catalogo que crece
> sin inflar el contexto y uno que se ahoga a las 200 tools. Copiar ese patron.
>
> El detalle comercial que duele: **$49-199/mes es el techo de precio de la capa de
> conexion.** Si CASHGO se explica como "chatea con tus ads", su precio ya esta capado ahi
> por dos competidores con producto vivo y por Meta con producto gratis.

---

## 1. PUNTO CRITICO DE SEGURIDAD FINANCIERA

El diseno completo (8 reglas, contratos, esquema del ledger, criterios del breaker) esta en
**`ADR-CG-001-guardrails-financieros.md`**. El resumen y la unica idea que hay que retener:

> **El HITL no va en el chat. Va en el ledger.**
> Poner la aprobacion en la conversacion es poner el control **adentro del sistema que puede
> alucinar**. Markifact y Adspirer ponen el freno en el chat; ahi hay una grieta y es donde
> CASHGO puede ser estrictamente mejor.

Las 8 reglas, en una linea cada una:

0. **El LLM no porta la credencial.** Nunca. El middleware es el unico portador.
1. **Toda escritura es una propuesta tipada, no una llamada.** Si no valida contra esquema, muere ahi.
2. **Los caps viven en la DB, no en el prompt**, y la propuesta se simula contra el ledger antes de mostrarse.
3. **Idempotencia obligatoria** por `hash(cuenta, entidad, campo, valor, ventana)`. Esto es lo que mata el bucle.
4. **Circuit breaker por gasto, no por errores**, y el agente no puede resetearlo.
5. **Todo nace PAUSED**, y `unpause` / `subir presupuesto` exigen aprobacion **fresca con TTL**.
6. **El copy de la competencia es dato hostil**: ningun contenido de anuncio puede originar una accion.
7. **Read-after-write contra Meta.** Sin verificacion de vuelta, "aprobado" es un relato.

Y la diferencia de producto, no de ingenieria: al pedir la aprobacion, no mostrar el cambio.
Mostrar **el gasto proyectado a 7 y 30 dias si el cambio se aplica y nadie lo vuelve a tocar**.
Ninguno de los dos competidores lo da, y es lo unico que un humano necesita para decir si.

---

## 2. CEREBRO vs BRAZO

Cuatro capas, y una regla de frontera que decide sola:

> **Si un error cuesta plata o es irreversible, es determinista.
> Si cuesta un token, es cognitivo.**

| Capa | Que hace | Con que | LLM |
|---|---|---|---|
| **Determinista** | auth, ledger, caps, idempotencia, breaker, scheduler, reintentos, cuotas, facturacion, audit log | Python/TS + Postgres | **cero** |
| **Cognitiva** | clasificar, extraer, resumir, redactar copy, proponer angulos | DeepSeek V4-Flash / Pro | si, **sin tools, sin credenciales, sin efectos** |
| **Ejecucion** | un adaptador por plataforma | **Marketing API directo (v26.0)** | no |
| **Conversacion** | el operador habla | MCP, y un unico tool: `submit_proposal` | si, lectura |

La capa cognitiva es una **funcion pura con temperatura**: entra texto, sale JSON validado.
No sabe que existe Meta.

### La decision contraintuitiva: tu backend NO debe hablar MCP con Meta

MCP existe para que **un LLM descubra herramientas en runtime**. Tu backend no descubre nada:
sabe exactamente que endpoint llamar y con que payload. Meter el MCP de Meta entre tu
servidor y la Marketing API es **agregar un interprete no determinista en el camino del
dinero**, con una superficie de tools que Meta cambia sin garantia de compatibilidad (la beta
no la promete) y un rollout parcial que devuelve `is_ads_mcp_enabled = false` por cuenta.

**Marketing API directo para escribir. MCP solo para la conversacion del operador, y en
lectura.** El mercado se equivoca justo aca: deja la logica de negocio a merced de un LLM
conectado por MCP porque MCP es lo que esta de moda, no porque sea la herramienta correcta
para un backend.

---

## 3. MOAT Y MONETIZACION

### Lo que NO puede ser el moat

La conexion (Meta la regala), la cantidad de tools (Markifact 1000+, Adspirer 400+, CASHGO 0
el dia uno), ni el chat (dos competidores con producto vivo y precio publico de $49).

### Vertical: si. Y el criterio de eleccion no es el tamano del mercado

> **La vertical se elige por donde el evento externo del cliente ya esta digitalizado y es
> medible.** Sin evento medible, la Arquitectura 4 no tiene disparador y el ecosistema A2A
> entero se queda sin insumo.

- **E-commerce DTC: gana.** Shopify / WooCommerce entregan por webhook stock, precio, COGS y
  ventas por SKU. El evento existe, llega solo y es confiable.
- **Inmobiliaria: pierde.** El "stock" es una propiedad que se vende por telefono y el CRM es
  un Excel. El disparador habria que inventarlo, y el cliente no lo va a mantener.

### El moat, en una frase

> **No es un dato de ads. Es la union de dos datos que los competidores no juntan.**

Markifact y Adspirer optimizan **ROAS**, porque es lo unico que ven desde la API de ads. Con
Shopify conectado, CASHGO ve **COGS, stock y margen por SKU**. Un agente que pausa un ad set
con **ROAS 4 y margen negativo** hace algo que ellos **estructuralmente no pueden hacer**: no
es que no se les ocurrio, es que no tienen el dato. Y el moat se profundiza solo, porque el
historico de margen por creativo lo vas acumulando vos.

### El segundo moat, mas barato y mas aburrido: el audit log financiero como producto

Nadie vende "aca esta cada peso que un agente movio, quien lo aprobo, cuando, y que
proyeccion tenia delante cuando dijo si". Eso es exactamente lo que un CFO necesita para
dejar que un agente toque la tarjeta. Es tedioso de construir, no tiene demo linda, y es lo
que cierra contratos B2B por encima del techo de $199.

### Pricing

La capa de conexion esta capada en $49-199. El ledger de margen **no se compara contra un
chat, se compara contra un analista**, y ahi el precio es otro. Si el producto se explica
como "chatea con tus ads", el pricing se hunde solo al piso del competidor.

---

## 4. PIPELINE DE COSTOS DE LA ARQUITECTURA 3 — MEDIDO

**Precios verificados en vivo [2026-09-06].** DeepSeek V4-Flash / V4-Pro, esquema peak/off-peak
vigente desde las 16:00 UTC del **2026-08-16**. Peak = 01:00-04:00 y 06:00-10:00 UTC, lun-vie.
Off-peak es la mitad.

| USD / 1M tokens | Flash off-peak | Flash peak | Pro off-peak | Pro peak |
|---|---|---|---|---|
| input cache **miss** | 0,22 | 0,44 | 0,66 | 1,32 |
| input cache **hit** | **0,007** | 0,014 | 0,022 | 0,044 |
| output | 0,66 | 1,32 | 1,98 | 3,96 |

- Fuente: https://ai-tldr.dev/models/deepseek-v4-flash/ · https://www.aipricing.guru/deepseek-pricing/
- **CONFLICTO DE FUENTES DECLARADO:** `deepseekai.guide` sigue publicando la tarifa plana
  anterior ($0,14 / $0,0028 / $0,28). El modelo usa la **nueva y mas cara**: si el margen
  cierra con la caras, cierra con las dos.

### El flujo, en orden, y por que ese orden

1. **Fuente:** `ads_archive` oficial con `ad_reached_countries` = UE/UK. Legal, gratis, con
   esquema. `search_page_ids` en batch de 10, `limit` alto, cursor `after`, backoff en 613.
2. **Deduplicacion por hash ANTES del modelo.** Un anuncio ya visto **no vuelve a pagar
   tokens**. Es el ahorro mas grande de todo el pipeline y **no tiene nada que ver con el
   modelo**: es un `SELECT`.
3. **Prefijo estable para cache-hit.** Taxonomia + esquema JSON + few-shots (~8.000 tokens)
   van **identicos y siempre primero**. El lote variable de anuncios va al final. Cache hit
   a $0,007 contra $0,22 de miss: **31x**. Si el prefijo cambia de orden, el cache se pierde
   entero y nadie te avisa.
4. **Cron en ventana off-peak.** Peak en hora de Buenos Aires es 22:00-01:00 y 03:00-07:00.
   La ventana barata cubre **07:00-22:00 ART**, o sea el horario laboral argentino completo.
   Mitad de precio por elegir la hora.
5. **Flash estructura, Pro sintetiza.** Nunca Pro en el lote masivo. Pro una vez por nicho
   por semana, y ahi si se justifica el contexto de 1M.
6. **Postgres es la fuente de verdad. Notion es una vista.**

### Numeros (salida cruda en `evidencia/salida_modelo_costo_arq3.txt`, exit code 0)

Supuestos: 40 nichos x 25 marcas = 1.000 paginas, 60 anuncios activos promedio, corrida
semanal, churn creativo 12%, 320 tok in / 140 tok out por anuncio, lotes de 40, prefijo 8k
con 95% de cache hit, 40 informes Pro por corrida, infra USD 60/mes, 30 suscriptores a USD 79.

| | off-peak | peak |
|---|---|---|
| anuncios vistos / corrida | 60.000 | 60.000 |
| anuncios que pagan tokens | **7.200** | 7.200 |
| descartados por dedup | **52.800** | 52.800 |
| USD Flash / corrida | 1,1976 | 2,3952 |
| USD Pro (40 informes) / corrida | 2,0592 | 4,1184 |
| **USD modelo / mes** | **14,10** | **28,20** |
| USD infra / mes | 60,00 | 60,00 |
| **USD total / mes** | **74,10** | **88,20** |
| contrafactual sin dedup ni cache | 62,64 | 125,29 |
| factor de ahorro | 4,4x | 4,4x |
| costo por anuncio nuevo | USD 0,000166 | USD 0,000333 |
| ingreso / mes | 2.370,00 | 2.370,00 |
| **margen bruto** | **96,87%** | **96,28%** |
| suscriptores para breakeven | 1 | 2 |

### Y aca esta el hallazgo que refuta la premisa de la pregunta

> **El margen del SaaS de datos nunca estuvo en riesgo.** Cierra al **96,28% pagando la
> tarifa peak y sin optimizar nada**. El costo cognitivo son **USD 28 de una factura de
> USD 88**: optimizar prompts es optimizar el 24% del gasto de un producto que ya tiene
> 96 puntos de margen. **Es la palanca equivocada.**

El cuello de botella real de la Arquitectura 3 no es el costo por token. Son dos rate limits:

1. **Ad Library: ~200 calls/hora.** 1.000 paginas con paginacion son varios cientos de
   llamadas: la corrida completa tarda **horas**, no minutos. Semanal aguanta; diario no.
2. **Notion, y este es fatal para el producto tal como esta descripto.**
   VERIFICADO EN VIVO [2026-09-06] · Fuente: https://developers.notion.com/reference/request-limits
   - **promedio de 3 requests por segundo por conexion**, mas un limite **nuevo por workspace**
     compartido entre todas sus conexiones
   - payload maximo **1.000 bloques / 500KB**, arrays de 100 elementos, rich text 2.000 chars
   - **tope de paginacion de 10.000 resultados por query** en data sources, con
     `request_status.type === "incomplete"`

   Volcar 60.000 anuncios a Notion a 3 req/s son **~5,5 horas de escritura**, y despues el
   cliente **no puede consultarlos**, porque la query se corta a los 10.000. **Notion no
   escala como base de datos de este producto.** Sirve como superficie de entrega de un
   top-N curado (200 filas por nicho por semana = 8.000 escrituras, ~45 minutos). Que ademas
   es mejor producto: nadie paga por 60.000 filas, pagan por las 200 que importan.

---

## 5. ROADMAP

**Criterio de orden, declarado (O-01):** lo que hace que el producto **exista y cobre** va
primero, salvo que algo lo bloquee de verdad. No "lo que desbloquea mas".

**Dependencias verificadas, no supuestas:**
- Fase 0 **no** depende de Fase 2: en volumen de MVP los anuncios de competidores se traen a
  mano o en tandas chicas. No comparten modulo.
- Fase 4 **si** depende de Fase 3, y es la unica dependencia dura de la lista: sin ledger no
  hay donde frenar a un agente autonomo.

| Fase | Cuando | Que | Por que ahi |
|---|---|---|---|
| **0** | semanas 1-2 | **Arquitectura 2**, el lead magnet | La unica que cobra **sin infraestructura de confianza**: no toca la cuenta del cliente, no toca dinero, no necesita ledger ni breaker. Y cada auditoria que entregas **te construye el corpus y te diagnostica un prospecto**. Es servicio, no SaaS, y esta bien que lo sea. |
| **1** | mes 1-2 | **Arquitectura 1 como herramienta interna** | No se vende: Meta la regala. Se usa para atender con menos horas a los clientes que trajo la Fase 0. Margen operativo. |
| **2** | mes 2-4 | **Arquitectura 3**, el SaaS de datos | Ya tenes corpus, pipeline y clientes que te dijeron que quieren ver. Ingreso recurrente que financia el resto. Margen medido: 96%. |
| **3** | mes 4+ | **El ledger financiero + escrituras reales** | Recien aca tocas dinero ajeno, y solo con las 8 reglas del ADR puestas **y testeadas**. Aca nace el moat vendible. |
| **4** | mes 8+ | **A2A, entre agentes propios y dentro del perimetro** | Ultima por seguridad (F-5). "Servidores paralelos" hablandose sin frontera de confianza es como un evento de stock falso se convierte en una campana con presupuesto duplicado. |

**La respuesta corta a la pregunta 5:** la Arquitectura 2. Y no por facil: porque es la unica
que **genera caja sin exigir que un desconocido te confie su tarjeta de credito**, que es el
activo que las Arquitecturas 3 y 4 necesitan y que todavia no tenes.

---

## 6. PUNTOS CIEGOS DEL BRIEF (los que nadie pregunto)

1. **No hay capa de creativo, y el creativo es el 80% de la performance en Meta.** Todo el
   plan mueve presupuesto y analiza copy. Canva por MCP no es una capa creativa, es un
   renderizador. Un sistema que optimiza distribucion sobre un creativo mediocre
   **automatiza la mediocridad a escala**.
2. **El cliente de la Arquitectura 3 no es el mismo que el de 1, 2 y 4.** Inteligencia de
   mercado es one-to-many, suscripcion, marketing de producto. Ad ops es one-to-one,
   servicio, venta consultiva. **Son dos empresas.** Elegir una y usar la otra como lead
   magnet; hacer las dos en serio al mismo tiempo es como se muere esto.
3. **Lock-in del vendor cognitivo, con seguro disponible.** V4-Flash tiene **pesos MIT en
   Hugging Face** (284B total / 13B activos). Es una salida real si el API sube — y ya subio:
   el esquema peak/off-peak del 2026-08-16 dejo **todas** las tarifas por encima de la plana
   anterior. Escribi la capa cognitiva detras de una interfaz, no contra `api.deepseek.com`.
4. **Residencia de datos, sin resolver.** DeepSeek procesa en China y el unico corpus legal
   es europeo. Los anuncios comerciales suelen no traer dato personal, pero las paginas
   anunciantes y los lead forms si. **NO MEDIDO**, y va declarado asi en vez de adivinado.
5. **El copy de la competencia es el vector de inyeccion mas probable de todo el sistema**, y
   el brief no lo menciona. En las Arquitecturas 2 y 3 ese texto ajeno pasa por el modelo
   todos los dias. Ver Regla 6 del ADR.
6. **Nadie modelo el CAC.** Con 96% de margen bruto y breakeven en 2 suscriptores, el riesgo
   del negocio **no es el costo**: es conseguir y retener a los 30. Esa es la planilla que
   falta, y no tiene una sola linea de codigo.

---

## 7. DEUDA DECLARADA

- **Precio (USD 79) y suscriptores (30) son supuestos**, no mediciones de disposicion a pagar.
- **El corpus para LatAm no tiene camino legal identificado.** Vias posibles sin evaluar:
  vender inteligencia UE/UK a marcas que exportan, o comprar el dato
  (adlibrary.com Business ~EUR 329/mes, Apify, ScrapeCreators).
- **El limite por workspace de Notion no tiene numero publico**, solo "escala con el plan".
  El calculo de 5,5 horas usa el limite por conexion, que es el conocido.
- **Nada de esto se corrio contra una cuenta de ads real.** Cero lineas de producto escritas.
  Esta auditoria es un mapa, no un territorio.
