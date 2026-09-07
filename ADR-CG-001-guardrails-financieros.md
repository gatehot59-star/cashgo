# ADR-CG-001 · Guardrails financieros entre el LLM y las plataformas de ads

**Estado:** propuesto · **Fecha:** 2026-09-06 · **Contexto:** CASHGO, Arquitecturas 1 y 4

## Problema

Un bucle autonomo o una alucinacion del modelo puede vaciar la tarjeta de credito de un
cliente. Markifact y Adspirer resuelven esto con **human-in-the-loop en cada escritura**:
Markifact con un protocolo de 4 pasos, Adspirer creando siempre PAUSED y sin exponer ninguna
tool de delete. El MCP oficial de Meta hace lo mismo por diseno: sus 82 tools no incluyen
borrado de campanas y las creaciones nacen pausadas.

Eso es un piso, no un techo. La grieta que los tres comparten:

> **El freno esta en el chat, o sea adentro del sistema que puede alucinar.**

## Decision

El HITL no va en la conversacion: va en un **ledger de gasto comprometido** que vive en el
backend determinista. El modelo **propone**; el ledger **autoriza**; el adaptador **ejecuta**.

## Las 8 reglas

### Regla 0 · El LLM no porta la credencial. Nunca.

El token de Meta no entra al contexto del modelo bajo ninguna circunstancia. El middleware es
el unico portador. Si el modelo puede leer el token, **cualquier prompt injection escondida en
el copy de un competidor es una escritura**. Esta regla es la que hace que las otras siete
importen: sin ella son sugerencias.

### Regla 1 · Toda escritura es una propuesta tipada, no una llamada

El modelo devuelve JSON validado contra esquema (Pydantic / Zod). Contrato minimo:

```json
{
  "proposal_id": "uuid",
  "account_id": "act_...",
  "entity": {"type": "adset", "id": "..."},
  "field": "daily_budget",
  "current_value": 3000,
  "proposed_value": 4500,
  "currency": "USD",
  "rationale": "texto libre, NO ejecutable",
  "idempotency_key": "sha256(...)",
  "requires_fresh_approval": true
}
```

Si no valida, **no hay reintento con el mismo prompt**: falla, se registra el defecto y se
corta. Un modelo que alucina `daily_budget: 999999` muere en el validador, no en la API de Meta.

### Regla 2 · Los caps viven en la DB, no en el prompt

Por cuenta: `cap_diario`, `cap_mensual`, `delta_max_por_cambio` (%), `delta_max_acumulado_24h`.
Un cap en el prompt es una constante que nadie consulta: parece proteger y no protege.

Y antes de mostrar la propuesta, **el sistema la simula contra el ledger** y muestra:

> "Si aplicas esto y nadie lo vuelve a tocar, este cliente gasta **USD X a 7 dias** y
> **USD Y a 30 dias**. Cap mensual: USD Z. Consumido hoy: W%."

Esto es lo que ningun competidor da, y es lo unico que un humano necesita para poder aprobar
un delta de presupuesto con responsabilidad.

### Regla 3 · Idempotencia obligatoria

`idempotency_key = sha256(account_id, entity_id, field, proposed_value, ventana_temporal)`.
Un reintento con la misma key es **no-op y devuelve el recibo anterior**.

> **Esta es la regla que mata el bucle.** Un agente en loop no gasta N veces: gasta una y
> recibe el mismo recibo N veces. Sin esto, el resto de los guardrails frenan la primera
> escritura y dejan pasar las 400 siguientes que son "nuevas" para el sistema.

### Regla 4 · Circuit breaker por gasto, no por errores

Dispara con cualquiera de:
- N escrituras aprobadas en M minutos sobre la misma cuenta
- gasto acumulado del dia > X% del `cap_diario`
- **divergencia entre gasto real (insights) y gasto esperado (ledger) > Y%**

Al disparar: **modo solo-lectura para toda la cuenta** y alerta al operador humano.

El breaker pertenece al sistema. **El agente no puede resetearlo, ni consultarlo para
planificar alrededor.** El tercer criterio es el importante: es el unico que detecta que el
ledger se desincronizo de la realidad, que es el modo de falla silencioso.

### Regla 5 · Todo nace PAUSED, y la aprobacion tiene TTL

El MCP oficial de Meta ya crea pausado. **No dependas de eso: implementalo en tu capa**, porque
es una garantia de una beta sin compromiso de compatibilidad.

`unpause` y `subir presupuesto` son una **clase aparte de accion**: exigen un token de
aprobacion **fresco**, con TTL de minutos, **ligado por hash a esa propuesta exacta**.

> Una aprobacion no es un permiso permanente. Confundir las dos cosas es exactamente como un
> "si" de un humano se convierte en un bucle autonomo.

### Regla 6 · El copy de la competencia es dato hostil

En las Arquitecturas 2 y 3, texto escrito por terceros entra al contexto del modelo todos los
dias. Ahi esta el vector de inyeccion, y a nivel de protocolo **sigue sin resolverse**
(vale igual para A2A, ver F-5 de la auditoria).

Mitigacion en dos niveles, y el orden importa:
1. **Estructural (el que funciona):** Regla 0 + Regla 1. Sin credencial y sin capacidad de
   emitir llamadas, la peor inyeccion posible produce **una propuesta invalida**.
2. **Prompt (el que ayuda):** el contenido ajeno va delimitado y etiquetado, con la
   instruccion explicita de que **ningun contenido de anuncio puede originar una accion**.

Un guard que vive solo en el prompt es el mismo error que un cap en el prompt.

### Regla 7 · Read-after-write: dos testigos para el dinero

Toda escritura aprobada se **relee desde Meta** y se compara contra la propuesta. Si difiere:
revertir y alertar. La evidencia cruda de la lectura de vuelta se guarda en el audit log.

> Sin verificacion de vuelta, "aprobado y aplicado" es un relato. Y este audit log no es solo
> control interno: es el **producto vendible** que un CFO necesita para dejar que un agente
> toque la tarjeta (ver seccion 3 de la auditoria).

## Consecuencias

**A favor:** el peor caso de una alucinacion es una propuesta rechazada. El peor caso de un
bucle es un no-op repetido. El peor caso de una inyeccion es un JSON invalido.

**En contra:** ninguna escritura es instantanea, y el sistema **no puede** prometer
"optimizacion 24/7 sin intervencion". Eso es un costo de marketing real y hay que asumirlo:
es el precio de no aparecer en un hilo de Twitter por haberle quemado el presupuesto a un
cliente.

**Lo que NO cubre:** nada de esto protege contra un operador humano que aprueba sin leer.
Para eso esta la proyeccion a 7 y 30 dias de la Regla 2, que es un diseno de interfaz, no un
guardrail. **NO MEDIDO:** si esa proyeccion efectivamente cambia el comportamiento de quien
aprueba. Se mide con usuarios, no con codigo.
