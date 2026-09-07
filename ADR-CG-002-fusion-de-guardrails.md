# ADR-CG-002 · Fusion de guardrails: 12 reglas

**Estado:** propuesto · **Fecha:** 2026-09-06 · **Reemplaza a:** ADR-CG-001 (no lo contradice:
lo extiende con 4 reglas)
**Contexto:** fusion de `ADR-CG-001-guardrails-financieros.md` con el blueprint externo
auditado en `01-CONTRASTE-CON-BLUEPRINT-EXTERNO.md`.

## Orden de implementacion, y por que este y no el numerico

**Criterio:** primero lo que protege sin depender de que yo este vivo; despues lo que protege
cuando yo estoy vivo; al final lo que hace lindo el proceso.

| Prioridad | Regla | Costo de implementarla | Protege si mi infra esta caida |
|---|---|---|---|
| **1** | **12 · `spend_cap` de Meta** | **cero codigo, se hace a mano hoy** | **si** |
| 2 | 0 · el LLM no porta la credencial | decision de arquitectura | n/a |
| 3 | 1 · propuesta tipada | 1 esquema por accion | n/a |
| 4 | 3 · idempotencia por intencion | 1 funcion de hash | no |
| 5 | 2 · caps en DB + simulacion | 2 tablas + 1 query | no |
| 6 | 5 · todo PAUSED + TTL de aprobacion | maquina de estados | no |
| 7 | 9 · aislamiento del scraper | topologia, cero codigo | si (por diseno) |
| 8 | 4 + 10 · breaker en proceso aislado | servicio separado | no |
| 9 | 11 · verificacion post-ejecucion | worker + webhook | no |
| 10 | 7 · read-after-write + audit log | append-only | no |
| 11 | 6 · el copy ajeno es dato hostil | delimitadores + Reglas 0 y 1 | n/a |

> **Que la Regla 12 vaya primera no es una preferencia: es que es la unica que se puede tener
> puesta esta noche.** Las otras 11 son codigo que todavia no existe.

---

## Reglas 0 a 7 — sin cambios

Estan en `ADR-CG-001-guardrails-financieros.md` con sus contratos. Resumen de una linea:

0. El LLM no porta la credencial. Nunca.
1. Toda escritura es una propuesta tipada, no una llamada.
2. Los caps viven en la DB, no en el prompt, y la propuesta se simula contra el ledger.
3. Idempotencia por `sha256(cuenta, entidad, campo, valor, ventana)`. **Por intencion, no por
   registro:** un UUID de propuesta como key no frena un bucle, solo un reintento.
4. Circuit breaker por gasto, no por errores. El agente no lo resetea.
5. Todo nace PAUSED. `unpause` y subir presupuesto exigen aprobacion fresca con TTL.
6. El copy de la competencia es dato hostil.
7. Read-after-write contra Meta, con evidencia cruda en el audit log.

---

## Regla 9 · Aislamiento total entre el scraper y las cuentas que gastan dinero real

**Origen:** concesion al blueprint externo (C-1). Mi ADR-001 no tenia esto.

El subsistema de mineria (Arquitecturas 2 y 3) y el subsistema de escritura (Arquitecturas 1 y 4)
**no comparten nada** de lo siguiente:

| Recurso | Por que |
|---|---|
| Sesion de navegador / cookies de Meta | scrapear logueado hace que los ToS apliquen (Bright Data) |
| IP / rango de salida | un bloqueo de IP por mineria no debe tocar la operacion |
| Cuenta de Facebook / Business Manager | una suspension no debe alcanzar la cuenta del cliente |
| **`app_id` de Meta** | **un bloqueo a nivel de app se lleva los dos subsistemas** |
| Proyecto de facturacion / metodo de pago | contaminacion administrativa |

El scraper corre en **perfil de navegador limpio, sin sesion**, en contenedor e IP dedicados.

**Y la degradacion es parte de la regla:** si la extraccion falla por rate limit o por cambio de
UI, el sistema entra en **espera con backoff exponencial**, nunca en reintentos agresivos. Un
reintento agresivo convierte un bloqueo temporal en uno permanente.

> El `app_id` es mi agregado sobre el blueprint. El resto es suyo y es correcto.

---

## Regla 10 · El breaker corre en un proceso que no puede caer con lo que vigila

**Origen:** concesion al blueprint externo (C-2). Mi Regla 4 definia el *que*, no el *donde*.

El servicio de vigilancia corre en **contenedor / proceso separado** del orquestador de IA, con:

- su **propia conexion** a la base de datos;
- su **propio credencial**, con el **permiso minimo y exclusivo** de (a) leer gasto,
  (b) pausar campanas, (c) setear `spend_cap`. **Nada mas.** Ni `ads_management` completo ni
  solo-lectura: solo-lectura no puede pausar, y eso es la contradiccion que le refute al
  blueprint (R-3);
- su propio despliegue y su propio health check.

**Que no es un breaker:** un `if` adentro del orquestador. Si el pod del orquestador se cuelga o
entra en bucle, el `if` se cuelga con el.

### Instrumento: webhook con umbral, no polling

El blueprint escribe un loop de 60 s y lo llama webhook. El instrumento correcto existe
(VERIFICADO EN VIVO 2026-09-06):

- endpoint **`subscriptions`** sobre el objeto `ad_account`, con **umbrales y filtros propios**,
  que notifica cuando una metrica de insights como **`spend`** cruza el umbral definido;
- campo **`effective_status`** para rechazos de politica y bloqueos de delivery;
- campo **`in_process_ad_objects`** para saber cuando un cambio termino de procesarse.

El watchdog es un **endpoint HTTPS que valida `X-Hub-Signature-256`**. El polling queda como
fallback degradado, no como mecanismo principal.

**Prerrequisito declarado:** la app tiene que estar en **modo live** y con permisos aprobados,
o los webhooks de ad account no disparan fuera de las notificaciones de prueba.

### Orden del kill switch (corregido respecto del blueprint)

1. `spend_cap` al valor ya gastado → **Meta corta la delivery**, sin depender de mi.
2. pausar campanas con el permiso minimo.
3. marcar la cuenta `paused_by_watchdog` y **alertar a un humano**.
4. **la revocacion del token la decide una persona.** Revocarlo automaticamente te deja sin
   poder leer el gasto ni despausar: el kill switch se lleva puesto su propio instrumento de
   verificacion.

---

## Regla 11 · La verificacion post-ejecucion espera, y espera al evento correcto

**Origen:** concesion al blueprint externo (C-3), mejorada.

La Marketing API procesa de forma asincrona. Un read-after-write inmediato lee un estado
intermedio y produce **falsos negativos**, o sea rollbacks de cambios que estaban bien.

- **Disparador primario:** el webhook **`in_process_ad_objects`**, que avisa cuando el objeto
  **sale** del estado `IN_PROCESS`.
- **Fallback:** job diferido a **300 s** (el numero del blueprint), que es tambien el timeout.
- Si a los 300 s no llego el webhook ni el objeto salio de `IN_PROCESS`: **no se declara ni
  exito ni fallo.** Se marca `NO_VERIFICADO` y se alerta. Tres estados, no dos.

> "HTTP 200" no es "aplicado", y "lei distinto a los 2 segundos" no es "fallo".

---

## Regla 12 · `spend_cap`: el unico guard que sobrevive a mi propia caida

**Origen:** ninguno de los dos documentos lo tenia. Es el hallazgo del contraste.

**VERIFICADO EN VIVO [2026-09-06]** · `developers.facebook.com/docs/marketing-api/reference/ad-account/`

> `spend_cap`: "The maximum amount that can be spent by this Ad Account. **When the amount is
> reached, all delivery stops.**"

Existe a nivel de **cuenta** y de **campana** (minimo del orden de USD 100), con
`spend_cap_action` en `reset` / `delete`.

### Politica

1. **Al onboardear una cuenta, `spend_cap` es obligatorio.** Ninguna cuenta entra al sistema sin
   techo de periodo seteado. Es la precondicion, no una opcion de configuracion.
2. Se calcula como `presupuesto_acordado_del_periodo x (1 + colchon)`, con el colchon acordado
   por escrito con el cliente.
3. **Solo un humano lo sube.** El agente no puede proponer subirlo: es la unica accion que no
   tiene camino de propuesta. La razon: es el techo contra el que se validan todas las demas
   propuestas, y un guard que el vigilado puede mover no es un guard.
4. El watchdog **si** puede bajarlo, como paso 1 del kill switch.

### La restriccion que lo define, y que hay que respetar en el diseno

**VERIFICADO EN VIVO [2026-09-06]** · doc de Rate Limiting del Marketing API:

- **10 cambios de spending limit por dia** — `error 17, subcode 1885172`.
- `daily_budget` / `lifetime_budget` de un ad set: **4 cambios por hora**, y si te pasas el
  cambio queda **bloqueado una hora** — `error 613, subcode 1487225`.

> **Por lo tanto `spend_cap` NO es un control dinamico.** Es un **techo de periodo**: se setea al
> onboardear y se mueve por excepcion. Diez cambios por dia es todo el presupuesto de maniobra
> que existe, y quemarlo en optimizacion deja al sistema sin la palanca cuando la necesita.
>
> **Y el segundo limite tiene una consecuencia de diseno que el blueprint no vio:** el "rate
> limiting semantico" de su Capa 2 **ya existe del lado de Meta para el caso del presupuesto**
> (4/hora/adset, gratis, enforceado por ellos). Mantenerlo igual, pero sabiendo que su valor
> real esta en las acciones que Meta *no* limita: publicar creativos, despausar, cambiar
> targeting.

---

## Consecuencias de la fusion

**A favor.** Peor caso de una alucinacion: propuesta rechazada. Peor caso de un bucle: un no-op
repetido (Regla 3 por intencion). Peor caso de una inyeccion: JSON invalido. Peor caso de que
**todo mi sistema este muerto**: Meta corta la delivery al llegar al `spend_cap` (Regla 12).
Peor caso de un bloqueo por scraping: pierdo el corpus, **no la cuenta del cliente** (Regla 9).

**En contra.** Ninguna escritura es instantanea y el sistema **no puede** prometer
"optimizacion 24/7 sin intervencion". Es un costo de marketing real y hay que asumirlo. Y la
Regla 12 introduce friccion comercial: pedir un techo de gasto por escrito en el onboarding
asusta a algunos clientes. Se vende al reves: **es lo que hace que puedan decir si**.

**Lo que sigue sin cubrir, declarado.** Nada de esto protege contra un humano que aprueba sin
leer. **NO MEDIDO:** si la proyeccion a 7 y 30 dias de la Regla 2 cambia el comportamiento de
quien aprueba. Se mide con usuarios, no con codigo.
