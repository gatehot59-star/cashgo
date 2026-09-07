# CONTEXTO-CASHGO.md

> Contexto vivo del proyecto. Se lee ANTES de responder cualquier cosa sobre CASHGO.
> Ultima actualizacion: 2026-09-06.

## Que es CASHGO

Ecosistema de automatizacion publicitaria y de agencia con IA. Cuatro arquitecturas
propuestas por el dueno del proyecto:

| # | Nombre | Que es | Estado |
|---|--------|--------|--------|
| 1 | Agencia Unipersonal Automatizada | chat + MCP para operar cuentas de ads sin entrar a la UI nativa | **degradada a herramienta interna**: Meta la regala |
| 2 | Captacion B2B (Lead Magnet Dinamico) | auditoria automatica de un prospecto + PDF/Doc comercial | **MVP, primera en cobrar** |
| 3 | Inteligencia de Mercado (SaaS de datos) | mineria periodica de la Ad Library, estructuracion, entrega por suscripcion | **segunda, margen medido 96%** |
| 4 | Ecosistema Autonomo A2A | eventos del cliente (stock, presupuesto) disparan cambios en campanas | **ultima, por seguridad no por costo** |

## Stack declarado

- **Motor cognitivo:** DeepSeek V4-Flash (masivo) + V4-Pro (razonamiento). Pesos MIT en HF.
- **Integracion externa:** MCP hacia plataformas de ads, Notion, Canva, Google Docs.
- **Orquestacion:** A2A entre agentes de departamento.

## Lo que ya esta medido (no repetir la medicion, leerla)

- `00-AUDITORIA-CASHGO.md` - las 6 refutaciones, las 5 respuestas, los puntos ciegos.
- `ADR-CG-001-guardrails-financieros.md` - las 8 reglas del middleware que toca dinero.
- `scripts/modelo_costo_arq3.py` + `evidencia/` - modelo de costo con salida cruda.

## Decisiones tomadas

1. **La capa de conexion no es producto.** No se vende "chatea con tus ads".
2. **Vertical: e-commerce DTC.** Criterio: es la unica vertical donde el evento externo
   del cliente ya esta digitalizado y es medible (Shopify/Woo: stock, COGS, margen por SKU).
3. **El moat es la union de dos datos que los competidores no juntan:** performance de ads
   x margen real por SKU. Mas el audit log financiero como producto vendible.
4. **El backend NO habla MCP con Meta.** Marketing API directo. MCP queda para la capa
   conversacional del operador, en lectura.
5. **Notion es una vista, no la base de datos.** Postgres es la fuente de verdad.

## Preguntas abiertas (NO MEDIDO, declarado)

- **Geografia del corpus.** El unico camino legal y oficial a anuncios comerciales de
  competidores es `ad_reached_countries` = UE/UK (obligacion del DSA). Si el cliente
  objetivo es LatAm, ese corpus no existe por via oficial. Sin resolver.
- **Residencia de datos.** DeepSeek procesa en China; el corpus legal es europeo. Si en
  algun momento entra dato personal (lead forms, paginas anunciantes), hay un problema de
  transferencia internacional que todavia no se evaluo.
- **Precio.** USD 79/mes es un supuesto del modelo, no una medicion de disposicion a pagar.
