# CONTRASTE: mi auditoria vs el blueprint de arquitectura recibido

**Fecha:** 2026-09-06 · **Modo:** TITAN FULL · **Tipo de entrega:** auditoria / ADR
**Rubrica:** 42/45 aplicables -> **93/100**. N/A: Ejecutabilidad de producto, Seguridad de
codigo, Testing, DevOps.
**Instrumento:** `scripts/sensibilidad_infra_y_equipo.py`, exit code 0, salida cruda en
`evidencia/salida_sensibilidad_infra_y_equipo.txt`.
**Documento contrastado:** "CASHGO — Auditoria de Arquitectura y Plan Maestro de Blindaje"
(4 capas de guardrails, stack de 14 componentes, DDL de 4 tablas, pseudocodigo del
watchdog, contrato del MCP Gateway, 6 sprints / 12 semanas).
**Mi documento:** `00-AUDITORIA-CASHGO.md` + `ADR-CG-001-guardrails-financieros.md`.

---

## 0. LO PRIMERO: EL BLUEPRINT ES BUENO, Y ESO CAMBIA COMO HAY QUE LEERLO

No es un documento para refutar de arriba a abajo. Coincide con mi auditoria en ~10 puntos
sustantivos a los que llegamos por caminos distintos, y **me gana en 3 puntos de arquitectura
que yo no tenia**. Este contraste tiene tres secciones y esa es la que va primero.

**Advertencia epistemica, porque importa:** dos analisis de IA convergiendo **no es medicion
independiente**. Es dos modelos con corpus solapado leyendo las mismas fuentes publicas. La
convergencia sube la confianza en que ninguno de los dos alucino el hecho; **no sube la
confianza en que el hecho sea cierto**. Lo unico que hace de falsador acá son las llamadas a
la doc oficial de Meta, que es lo que uso en la seccion 2.

---

## 1. LOS 10 ACUERDOS (convergencia, no confirmacion)

| # | Punto | El blueprint | Mi auditoria |
|---|---|---|---|
| 1 | El LLM propone, el backend determinista dispone | "Regla maestra" | "Cerebro vs Brazo", regla de frontera |
| 2 | Los guardrails viven en codigo, nunca en el prompt | Capa 2 | Regla 2 |
| 3 | La propuesta es un artefacto auditable, no un mensaje de chat | tabla `action_proposals` | Regla 1, contrato JSON |
| 4 | Audit log inmutable append-only | tabla `audit_log` | Regla 7 |
| 5 | HITL con proyeccion de peor escenario, no "si/no" | Capa 3, proyeccion a 30 dias | Regla 2, proyeccion a 7 y 30 dias |
| 6 | Maquina de estados finita con transiciones testeables | `PROPUESTA -> ... -> VERIFICADA` | mismo flujo, en prosa |
| 7 | Vertical, no SaaS generalista. E-commerce | Shopify por dato estructurado | e-commerce DTC por **evento medible** |
| 8 | El moat no puede ser la conectividad MCP | "se comoditiza rapido" | Meta la **regala** desde el 29-abr |
| 9 | Dedup determinista antes del LLM | "reduce 70-90%" | **88% medido** (52.800 de 60.000) |
| 10 | Roadmap: Arq2 primero, A2A ultima | Fase 0 -> 3 | Fase 0 -> 4, misma secuencia |

Y los dos citamos **Meta v. Bright Data** para el mismo fin. Eso no es casualidad: es la
fuente obvia. Vale como acuerdo, no como verificacion cruzada.

> **Diez acuerdos sobre diez preguntas distintas es senal de que el diseno de fondo esta
> bien.** Lo interesante no esta ahi: esta en los 3 lugares donde el blueprint ve algo que yo
> no vi, y en los 7 donde la doc de Meta nos corrige a los dos o a el.

---

## 2. LAS 3 CONCESIONES: donde el blueprint me gana

### C-1 · Aislamiento del scraper de las cuentas que gastan dinero real — **esto me faltaba**

Su punto ciego #6 dice algo que mi ADR de 8 reglas **no tiene en ninguna de las 8**:

> "nunca compartir contexto de sesion entre 'el brazo que gasta dinero del cliente' y 'el
> scraper que mina competencia'. Un bloqueo de IP o suspension de cuenta por scraping jamas
> debe poder tocar la cuenta publicitaria operativa."

Es correcto y es importante, y lo mio se queda corto por una razon especifica: **yo trate el
riesgo del scraping como riesgo del scraper**, y el lo trato como **riesgo de contaminacion
entre dos subsistemas**. Es la diferencia entre "se me rompe el parser" y "me suspenden la
cuenta desde la que opero el dinero de un cliente". El segundo es un evento de negocio, no de
ingenieria.

Entra al ADR-CG-002 como **Regla 9**, y la endurezco un paso: no solo sesion e IP, tambien
**identidad de la app de Meta y del proyecto de facturacion**. Si el scraper y el gateway de
escritura comparten `app_id`, un bloqueo a nivel de app se lleva los dos.

### C-2 · El watchdog como proceso arquitectonicamente aislado — **mi Regla 4 tenia el que, no el donde**

Mi Regla 4 define el circuit breaker: los tres criterios de disparo, y que el agente no lo
pueda resetear. Lo que **no** dice es donde corre. El blueprint si:

> "corre en un proceso Kubernetes/contenedor separado del orquestador de IA, con su propia
> conexion a la base de datos y sus propias credenciales. Si el pod del orquestador se cae,
> se cuelga, o entra en un bucle, el watchdog sigue vivo."

Un breaker que comparte proceso con lo que vigila **no es un breaker, es un `if`**. Concedido
completo. Entra como **Regla 10**.

(Y ojo: la seccion 2 de este documento le va a refutar el *contenido* de ese watchdog. La
topologia esta bien; el instrumento que usa adentro, no.)

### C-3 · Verificacion post-ejecucion **con delay** — mi Regla 7 era ingenua

Mi Regla 7 dice "read-after-write contra Meta". El blueprint dice:

```python
await schedule_verification_job(proposal.id, delay_seconds=300)
```

Ese `delay_seconds=300` es la parte que yo no puse, y es la que hace que la verificacion sirva:
la Marketing API tiene procesamiento asincrono (de ahi que exista el webhook
`in_process_ad_objects`, que avisa cuando un objeto **sale** del estado `IN_PROCESS`). Un
read-after-write inmediato lee un estado intermedio y produce **falsos negativos**, o sea
rollbacks de cambios que estaban bien.

Mejor todavia que su delay fijo: **verificar cuando llegue el webhook de `in_process_ad_objects`**,
y usar los 300 s solo como timeout. Concedido y mejorado. Entra como **Regla 11**.

---

## 3. EL HALLAZGO QUE NOS GANA A LOS DOS

> ### Meta ya tiene el kill switch adentro, y es mejor que los dos que disenamos.

**VERIFICADO EN VIVO [2026-09-06]** · Fuente: `developers.facebook.com/docs/marketing-api/reference/ad-account/`

El campo `spend_cap` de la cuenta publicitaria:

> "The maximum amount that can be spent by this Ad Account. **When the amount is reached, all
> delivery stops.** A value of 0 means no spending-cap. Setting a new spend cap only applies
> to spend AFTER the time at which you set it."

Y existe tambien a nivel de campana (`spend_cap` en Ad Campaign, minimo del orden de USD 100),
mas `spend_cap_action` con valores `reset` y `delete`.

**Ahora comparalo con lo que disenamos los dos:**

| | Su Capa 4 (watchdog) | Mi Regla 4 (breaker) | `spend_cap` de Meta |
|---|---|---|---|
| Quien lo enforcea | mi proceso | mi backend | **Meta** |
| Sobrevive si mi pod muere | no | no | **si** |
| Sobrevive si mi DB no responde | no | no | **si** |
| Sobrevive si mi endpoint es inalcanzable | no | no | **si** |
| Sobrevive si mi token expira | no | no | **si** |
| Latencia de reaccion | 60 s a 5 min | igual | **inmediata, es la plataforma** |

> **Su Capa 4 y mi Regla 4 son los dos kill switches EXTERNOS.** Los dos dependen de que mi
> infraestructura este viva justo en el momento en que algo salio mal, que es exactamente el
> momento en que es menos probable que lo este. **Los dos disenamos el airbag y ninguno puso
> el cinturon que ya venia en el auto.**
>
> El guardrail correcto no es el que yo ejecuto: es el que **sobrevive a mi propia caida**.

### Y la restriccion que lo vuelve real en vez de magico

**VERIFICADO EN VIVO [2026-09-06]** · Fuente: doc de Rate Limiting del Marketing API

- **"We limit you to changing your account spending limits 10 times per day"** —
  `error 17, subcode 1885172`.
- El `daily_budget` / `lifetime_budget` de un ad set **solo se puede cambiar 4 veces por hora**;
  si te pasas, **el cambio de presupuesto de ese ad set queda bloqueado una hora** —
  `error 613, subcode 1487225`.

Dos consecuencias, las dos importantes:

1. **`spend_cap` es un guard grueso y lento.** Sirve como **techo del periodo**, no como control
   dinamico por propuesta: 10 cambios por dia es todo el presupuesto de maniobra que hay. Se
   setea al onboardear y se mueve por excepcion, no por optimizacion.
2. **La "Capa 2 · rate limiting semantico" del blueprint ya existe del lado de Meta para el caso
   del presupuesto.** 4 cambios/hora/adset, gratis, enforceado por ellos. Su `MAX_WRITES_PER_HOUR`
   **duplica un guard que ya esta puesto**, y su valor real esta en las acciones que Meta *no*
   limita (publicar creativos, despausar, cambiar targeting). Vale mantenerlo, pero sabiendo
   que para presupuesto es el segundo cinturon, no el primero.

---

## 4. LAS 7 REFUTACIONES MEDIDAS

### R-1 · Su watchdog dice "webhooks" y hace polling. Y el webhook que necesita **existe**.

El texto dice "monitoreando gasto real via webhooks de Meta (no via LLM)". El pseudocodigo
hace:

```python
while True:
    for account in await get_active_accounts():
        real_spend = await meta_webhook_client.get_actual_spend(account)
    ...
    await asyncio.sleep(WATCHDOG_INTERVAL_SECONDS)  # ej. 60s
```

Eso **no es un webhook**: es polling con un cliente que se llama `webhook_client`. Y no es un
detalle de nombres, porque el costo es medible: polling sobre N cuentas cada 60 s consume rate
limit del Marketing API en llamadas que **casi siempre devuelven "sin cambio"**, y ese es
exactamente el presupuesto de llamadas que el resto del sistema necesita.

**Y ahora la parte buena, que le da la razon al espiritu de su Capa 4:** el instrumento existe y
es mejor de lo que su documento supone.

**VERIFICADO EN VIVO [2026-09-06]** · Fuentes: doc oficial de Ads Webhooks (actualizada el
6-jul-2026) y la cobertura del post de Meta del 21-ago-2026.

- Los webhooks de ads se entregan sobre el objeto **`ad_account`**, con envelope
  `{object, entry[{id, time, changes[{field, value}]}]}`.
- Campos individuales disponibles: **`effective_status`** (nuevo: avisa rechazos de politica,
  bloqueos de delivery y vuelta a delivery activo), `creative_fatigue`, `ad_recommendations`,
  `in_process_ad_objects`, `with_issues_ad_objects`, `product_set_issue`.
- Y el que importa acá: el campo **`subscriptions`**, estructuralmente distinto a los otros
  cinco. Segun la doc, avisa cuando un objeto se crea o actualiza **o cuando una metrica de
  insights como impresiones, `spend` o conversiones cruza un umbral que vos definis**. Meta
  dice que un solo flujo de setup habilita **mas de 88 notificaciones**.
- Setup: un `POST` al edge `subscriptions` del **app ID** con **app access token**, y otro al
  edge de la **cuenta** con token de **admin de la cuenta** (system user o user token). El body
  lleva `event_type` y un array `filters`, donde cada filtro es `{field, value, operator}` — el
  ejemplo publicado usa `EQUAL`.
- Los otros cinco campos requieren `ads_management` y suscribir la app via
  `POST /{ad-account-id}/subscribed_apps`.

> **Corolario de diseno:** el watchdog no es un loop. Es un **endpoint HTTPS que valida
> `X-Hub-Signature-256`** y reacciona a un umbral de `spend` que Meta evalua del lado de ellos.
> El polling queda como **fallback degradado** para cuando el webhook no llega, no como el
> mecanismo principal.

**Deuda honesta:** la doc dice que la notificacion te avisa que algo cambio y que despues
hay que consultar el endpoint de insights para el detalle. O sea que el webhook **reduce** el
polling, no lo elimina. Y hay reportes viejos de comunidad de webhooks de ad account que no
disparaban con la app en development mode: **el modo live y los permisos aprobados son
prerrequisito**, no un detalle de configuracion.

### R-2 · Su idempotency key no frena el bucle que dice frenar

```python
idempotency_key = f"{proposal.id}:{proposal.action_type}"  # "evita doble ejecucion en reintentos"
```

`proposal.id` es un **UUID nuevo por propuesta**. Y un agente en bucle **no reintenta la misma
propuesta**: genera 400 propuestas nuevas, cada una con su UUID → **400 keys distintas → 400
ejecuciones**, todas "primera vez" para el sistema.

El comentario del codigo es **cierto para reintentos y falso para bucles**. Y el bucle es
literalmente el escenario que la pregunta original planteaba: *"un bucle autonomo que vacie la
tarjeta de credito"*.

En su diseno lo unico que frena eso es `MAX_WRITES_PER_HOUR`, o sea **un guard de tasa haciendo
el trabajo de un guard de identidad**. Funciona hasta que alguien sube el limite por una razon
operativa razonable, y entonces se cae el unico control que quedaba.

**El fix es una linea:** la key hashea la **intencion**, no el registro.
`sha256(account_id, entity_id, field, proposed_value, ventana_temporal)`. Ahi las 400 propuestas
colapsan en **una** ejecucion y 399 no-ops que devuelven el recibo original.

### R-3 · Su Capa 4 se contradice a si misma, y `revoke_oauth_token` es peor que no hacer nada

La nota de diseno dice que el watchdog corre "con sus propias credenciales OAuth de
**solo-lectura-de-gasto**". Dos lineas despues:

```python
await pause_all_campaigns(account.id)   # MCP write directo
await revoke_oauth_token(account.id)    # corta acceso del agente
```

**Credenciales de solo lectura no pausan campanas.** Una de las dos afirmaciones tiene que
ceder, y la que hay que ceder es la de solo-lectura: el watchdog necesita **un permiso de
escritura minimo y exclusivo** — pausar y setear `spend_cap`, nada mas — no `ads_management`
completo y no solo lectura.

Y el `revoke_oauth_token` es un error de orden con consecuencia: **revocar el token te deja sin
poder leer el gasto ni despausar**. El kill switch se lleva puesto el instrumento que
verificaria que funciono, y deja a la cuenta del cliente en un estado del que solo se sale a
mano. El orden correcto:

1. `spend_cap` al valor ya gastado → **Meta corta la delivery**, sin depender de mi.
2. pausar campanas con el permiso minimo.
3. marcar la cuenta `paused_by_watchdog` y **alertar a un humano**.
4. **la revocacion del token la decide una persona**, no el watchdog.

### R-4 · "Servidores MCP propios por plataforma" es una capa que no hace falta, y su propio contrato lo demuestra

Su tabla de stack dice: *"Servidores MCP propios por plataforma (Meta, Google, TikTok)
envolviendo las APIs oficiales"*. Pero el contrato que escribe dos secciones despues es:

```
POST /internal/mcp/execute
Headers: X-Idempotency-Key, X-Internal-Service-Token (nunca expuesto a internet)
```

**Eso no es MCP.** Es una API REST interna con un token de servicio, y **esta bien que lo sea**.
MCP existe para que un LLM **descubra tools en runtime**; un gateway determinista no descubre
nada: sabe exactamente qué endpoint llamar. Envolver la Marketing API en un servidor MCP para
que tu propio backend lo consuma es **agregar un protocolo de descubrimiento en el camino del
dinero** a cambio de cero beneficio.

El riesgo del nombre no es estetico: **invita a que alguien lo implemente de verdad**.
Llamalo `ads-gateway` y el error se vuelve imposible de cometer.

Dato que refuerza la direccion: cuando Meta lanzo su MCP **para developers** (fin de junio
2026), mantuvo **casi toda la superficie de sus 10 tools en solo-lectura**, y lo unico que un
agente puede modificar es la suscripcion de webhooks. Meta, con todos los recursos del mundo,
eligio que un agente **no escriba**.

### R-5 · Pone el scraper en el Sprint 1-2 y nunca menciona la via oficial que existe

Su punto ciego #6 dice, correctamente, que para anuncios comerciales de EE.UU. la API de la
Ad Library no devuelve nada. De ahi concluye que hay que scrapear con Playwright + proxies
residenciales, y lo pone como **fundacion de la semana 1**.

Le falta la mitad del mapa: por el **DSA**, `ads_archive` devuelve **todos** los anuncios
comerciales entregados a la UE y UK, con esquema, gratis y legal (ver F-2 de
`00-AUDITORIA-CASHGO.md`). Construir la pieza fragil primero, cuando existe una fuente estable
para un subconjunto del corpus, es el orden equivocado.

Y cuesta plata medible: en mi desglose del stack, **los proxies residenciales mas el pool de
contenedores son USD 135 de USD 395**, o sea el **34% de la infra**, dedicado a la unica pieza
del sistema que **se rompe cuando Meta hace un deploy**.

### R-6 · "El 95% del gasto en tokens va al modelo barato" — mi modelo dice 37%

Su seccion 4 afirma: *"el razonamiento caro (V3/R1) se limita a un resumen de baja frecuencia y
bajo volumen — el 95% del gasto en tokens va al modelo barato"*.

Medido, con los supuestos de mi modelo (40 informes semanales de 60k tokens de input cada uno):

| ventana | Flash / corrida | Pro / corrida | **Pro como % del gasto de tokens** |
|---|---|---|---|
| off-peak | USD 1,1976 | USD 2,0592 | **63,2%** |
| peak | USD 2,3952 | USD 4,1184 | **63,2%** |

**Pro es el 63% del gasto de tokens, no el 5%.** Cuarenta informes por semana con 60k de
contexto **no son "bajo volumen"**: son 2,4M de tokens de input semanales al modelo caro. Su
intuicion de arquitectura es correcta (Flash masivo, Pro selectivo); su numero esta invertido.

Si el objetivo es que Pro sea el 5%, hay dos palancas y ninguna es de prompt: **bajar la
frecuencia de los informes** (mensual en vez de semanal) o **bajar el contexto que se les mete**
(resumen de Flash en vez del corpus crudo). Es una decision de producto, no de optimizacion.

### R-7 · El Sprint 7-8 asume un acceso al Marketing API que una app nueva no tiene

**VERIFICADO EN VIVO [2026-09-06]** · doc de Rate Limiting del Marketing API:

> "By default, apps have `development_access` to the Marketing API."

Para pasar al tier **standard** hay criterios de uso sostenido — del orden de **50 cuentas
publicitarias en 15 dias** y una **tasa de error por debajo de ~15% sobre las ultimas ~500
llamadas**. El tier se ve en el header `X-Ad-Account-Usage` (`ads_api_access_tier`).

El Sprint 7-8 ("Servidor MCP propio envolviendo Marketing API de Meta, primero lectura, luego
escritura") **asume que ese acceso esta dado**. Para una app recien creada, no lo esta, y el
criterio de salida es de **volumen**, que es justo lo que un producto nuevo no tiene: un gate de
gallina y huevo que hay que planificar, no descubrir en la semana 7.

El limite de mutaciones (**100 QPS por app + cuenta publicitaria**) no es el problema. **El tier
si.**

> **Declarado como parcialmente medido:** los umbrales exactos del tier los lei de una fuente
> con el texto recortado. La existencia de los dos tiers y del header estan firmes; **los
> numeros 50 / 15 dias / 15% / 500 hay que confirmarlos en el App Review dashboard antes de
> planificar el sprint.** No los doy por cerrados.

---

## 5. EL COSTO QUE NINGUNO DE LOS DOS DOCUMENTOS PUSO EN UNA TABLA

Salida cruda completa en `evidencia/salida_sensibilidad_infra_y_equipo.txt` (exit code 0).

### A) Su stack cuesta 6,6x el mio en infra — y el margen aguanta igual

| | componentes | USD / mes | margen peak | breakeven |
|---|---|---|---|---|
| Mi stack | 3 | **60** | **96,28%** | 2 suscriptores |
| Su stack | 14 | **395** | **82,14%** | 6 suscriptores |

Puntos de quiebre del margen (ingreso fijo de USD 2.370/mes):

| margen objetivo | costo de infra que lo produce |
|---|---|
| 80% | USD 445,80 / mes |
| 50% | USD 1.156,80 / mes |
| 0% | USD 2.341,80 / mes |

> **Su stack NO rompe la rentabilidad**, y eso hay que decirlo: 82% de margen sigue siendo un
> negocio excelente. Lo que cambia es otra cosa, y es lo interesante: **el modelo pasa de ser
> el 32% de la factura al 7%**. O sea que su optimizacion de prompt caching — que esta bien
> pensada — esta trabajando sobre **el 7% del gasto** de un sistema cuyo 93% es infra que el
> mismo eligio. Los dos llegamos a la misma conclusion desde lados opuestos: **DeepSeek no es
> el problema.**
> (K8s no esta contado en los USD 395: su documento lo pone como destino, no como MVP.)

### B) Y el costo que no aparece en ninguna tabla: semanas-persona

El plan declara **12 semanas** asumiendo **"2-3 devs full-stack + tu como product/negocio"**.
Contado en semanas-persona:

| | valor |
|---|---|
| Semanas de calendario declaradas | 12 |
| Devs asumidos | 2,5 |
| **Semanas-persona de trabajo** | **30** |
| Con UNA persona a tiempo completo | **6,9 meses** |
| Con UNA persona al 50% (hay otros proyectos vivos) | **13,9 meses** |

> **El numero "12 semanas" no es del plan: es del EQUIPO que el plan supone.** Con una sola
> persona, el mismo plan es de 6,9 a 13,9 meses, y las Fases 3-4 quedan del otro lado de un
> ano. Esto **no refuta el blueprint**: refuta leerlo como un cronograma.
>
> Y es el punto donde una prioridad mal puesta cuesta mas que cualquier error tecnico de este
> documento: 30 semanas-persona es **mas de un trimestre de la unica persona disponible**,
> mientras hay otros proyectos corriendo. La Fase 0 sola son 5 semanas-persona (S1-2 + S3-4
> recortado). **Esa es la unica fase que hay que comprometer hoy.**

---

## 6. VEREDICTO

**Lo que el blueprint tiene y yo no tenia (3):** aislamiento del scraper respecto de las cuentas
de dinero real, topologia del watchdog como proceso aislado, y verificacion post-ejecucion con
delay. Los tres entran al ADR-CG-002 como Reglas 9, 10 y 11.

**Lo que yo tengo y el no (7):** el MCP oficial de Meta como matador de la Arquitectura 1, la via
legal UE/UK del `ads_archive`, los limites de Notion que hacen inviable el producto tal como se
describio, la idempotencia que si frena bucles, el numero real de Pro contra Flash, el gate del
tier del Marketing API, y el costo en semanas-persona.

**Lo que ninguno de los dos tenia, y es la pieza mas barata del sistema:** `spend_cap`. Entra
como **Regla 12**, y va **primera en orden de implementacion** porque es la unica que se puede
poner **hoy, a mano, desde Ads Manager, sin escribir una linea de codigo**, y ya deja al cliente
mas protegido que las 11 reglas restantes juntas mientras el resto se construye.

**Recomendacion operativa, en una linea:** fusionar los dos disenos en `ADR-CG-002`, y recortar
el plan de 6 sprints a **la Fase 0 sola (5 semanas-persona)**, con `spend_cap` seteado a mano
desde el dia uno en cualquier cuenta que se toque.

---

## 7. DEUDA DE ESTE CONTRASTE

- Los umbrales del tier standard del Marketing API estan **parcialmente medidos** (R-7).
- **No verifique** si una app puede revocar programaticamente un token de usuario de Meta
  (`DELETE /{user-id}/permissions` existe para permisos de app; el token del MCP oficial lo
  revoca el usuario en Business Integrations). La refutacion R-3 no depende de eso: se sostiene
  por la contradiccion interna y por el orden de operaciones.
- Los precios del desglose de infra son **ordenes de magnitud de tiers de arranque**, no
  cotizaciones. Estan uno por uno en el script para poder discutirlos por separado.
- **Nada de esto se corrio contra una cuenta de ads real.** Los dos documentos siguen siendo
  mapas.
