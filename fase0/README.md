# CASHGO Fase 0 — Lead Magnet Dinamico

Genera una **auditoria publicitaria competitiva** en PDF para un prospecto, a
partir de la Ad Library oficial de Meta. Es la Arquitectura 2 del proyecto y la
primera fase del roadmap.

## Por que esta es la primera fase

**No tiene ninguna credencial de escritura sobre ninguna cuenta publicitaria.**
No puede gastar dinero de nadie. Por eso puede salir a produccion *antes* de que
exista el ledger financiero del `ADR-CG-002`, y por eso es la unica que cobra sin
pedirle a un desconocido que te confie su tarjeta de credito.

Y cada auditoria que entregas hace tres cosas a la vez: te paga, te construye el
corpus de la Arquitectura 3, y te diagnostica un prospecto.

## Quick start (sin red, sin credenciales)

```bash
pip install -r fase0/requirements.txt
python -m fase0.fixtures.generar          # datos de prueba: viven como codigo
python -m fase0.pipeline fase0/fixtures/brief_ejemplo.json \
  --dry-run fase0/fixtures/ads_archive_sample.json \
  --salida salidas --pdf
```

Eso produce `salidas/auditoria-mi-tienda-dtc.pdf` (4 paginas) sin tocar internet:
usa un fixture de `ads_archive` y un clasificador por reglas en lugar del modelo.

Suite completa:

```bash
python -m unittest discover -s fase0/tests -t . -v   # 128 tests
bash scripts/control_positivo_suite.sh               # 7/7 mutaciones cazadas
python3 scripts/manifiesto.py --verificar            # integridad de la evidencia
```

## Correr contra las APIs reales

```bash
export CASHGO_ADS_ARCHIVE_TOKEN="<system user token con scope ads_archive>"
export DEEPSEEK_API_KEY="<api key>"
export CASHGO_RESEARCH_APP_ID="<app de Meta SOLO para research>"
export CASHGO_PAISES="ES,DE,FR,IT,NL,GB"
python -m fase0.pipeline mi_brief.json --pdf
```

| Variable | Obligatoria | Que es |
|---|---|---|
| `CASHGO_ADS_ARCHIVE_TOKEN` | si (sin `--dry-run`) | System user token con scope `ads_archive`. Los tokens de usuario expiran a ~60 dias; para jobs recurrentes va el de system user. |
| `DEEPSEEK_API_KEY` | si (sin `--dry-run`) | API key de DeepSeek. |
| `CASHGO_RESEARCH_APP_ID` | recomendada | App de Meta dedicada a research. **No puede ser la misma que la de escritura** (Regla 9). |
| `CASHGO_WRITE_APP_ID` | opcional | Si se define y coincide con la de research, la config **aborta**. |
| `CASHGO_PAISES` | opcional | Codigos ISO. Solo UE/UK: ver abajo. |
| `CASHGO_DB_PATH` | opcional | SQLite. Default `cashgo_fase0.sqlite3`. |

### Antes de la primera corrida real, dos tramites

1. **Verificacion de identidad** en `facebook.com/ID` con documento. Tarda dias.
   Sin esto el token es valido y las queries igual se rechazan: es el error de
   setup mas comun.
2. **App de developer** con el producto Ad Library API. **No** hace falta App
   Review para este endpoint.

## El brief

```json
{
  "prospecto_page_id": "1001",
  "prospecto_nombre": "Mi Tienda DTC",
  "nicho": "e-commerce de hogar y deco",
  "competidores_page_ids": ["2001", "2002", "2003", "2004"],
  "paises": ["ES", "DE", "FR", "IT", "NL", "GB"]
}
```

Los `page_id` son de las **paginas de Facebook**, no de cuentas publicitarias. Se
sacan del buscador publico de la Ad Library.

## El limite que hay que entender antes de vender esto

> **`ads_archive` solo devuelve anuncios COMERCIALES para la UE y UK.**

Es una obligacion del Digital Services Act, con retencion de ~12 meses. Fuera de
ese conjunto la API devuelve unicamente anuncios sobre temas sociales, elecciones
o politica, o sea nada util para inteligencia competitiva.

El codigo trata eso como un **guard duro**, no como una nota: pedir `US` levanta
`AlcanceComercialError`. Motivo: una lista vacia es indistinguible de "el
competidor no anuncia", y alguien va a escribir eso en un informe que se cobra.

**Consecuencia comercial:** el primer cliente de la Fase 0 es una marca que pauta
en Europa, o una marca de LatAm que exporta a Europa. Para un prospecto que solo
pauta en Argentina, este pipeline **no tiene corpus**. No hay workaround por via
oficial y esta declarado como abierto en `CONTEXTO-CASHGO.md`.

Lo segundo: para anuncios comerciales Meta **no publica** spend, impresiones, CTR
ni conversiones. La unica senal de exito es **cuanto tiempo lleva activo** el
anuncio. El informe lo dice en su propia pagina de metodologia, con esas palabras.

**Y una limitacion propia declarada (10.10 del informe):** ningun campo de
`config.CAMPOS_ADS_ARCHIVE` informa el FORMATO del anuncio, y el prompt prohibe
adivinarlo. En produccion `formato` sera "desconocido" casi siempre y la seccion 4
del entregable ("Formatos que el mercado sostiene") sera inerte. En el `--dry-run`
no se nota porque el clasificador de fixture lo deriva de las plataformas, que es
justo lo que el prompt prohibe.

## Arquitectura

```
ads_archive (oficial, UE/UK)          adlibrary.py
   |  batch de 10 page_ids, cursor `after`, backoff en 613
   v
persistir el crudo                    store.py       <- ANTES de gastar un token
   |
   v
DEDUP por content_hash                dedup.py       <- aca se decide el 88% del costo
   |  (cero IA: es un SELECT)
   v
DeepSeek V4-Flash por lotes de 40     cognitive.py   <- prefijo estable primero
   |  validacion estricta, sin reintento del prompt
   v
agregacion DETERMINISTA               report.py      <- cero LLM
   |
   v
PDF (WeasyPrint)                      report.py      <- escapado obligatorio
```

### Las cuatro decisiones que sostienen esto

1. **El crudo se persiste antes de llamar al modelo.** Guardar es barato; el rate
   limit de `ads_archive` es el recurso escaso. Una corrida que muere en el paso
   del modelo no debe re-consumir el paso de la API.

2. **`content_hash` es del CONTENIDO, no del registro.** No incluye fechas, ni
   `ad_id`, ni plataformas. Un anuncio que sigue corriendo aparece en cada corrida
   con otra fecha de fin: si el hash la incluyera, el ahorro seria cero. Y una
   creatividad se clasifica una vez y se atribuye a **todos** los `ad_id` que la
   comparten.

3. **El prefijo del prompt es byte-identico y va primero.** Cache hit a
   USD 0,007/Mtok contra USD 0,22 de miss: 31x. Su SHA-256 esta pinneado en
   `tests/test_cognitive.py`; editarlo pone la suite en rojo a proposito.
   Corolario medido (`evidencia/salida_reconciliacion_prefijo.txt`): con 95% de
   cache hit, errar el TAMANO del prefijo por 12x mueve la factura 0,7%. **No
   vale la pena acortar el prompt para ahorrar plata**; si vale alargarlo con mas
   ejemplos. Lo unico que hay que cuidar es que no cambie.

4. **La agregacion no usa LLM.** Contar y ordenar es trabajo de un backend. Y
   ademas hace el informe **determinista**: dos corridas con el mismo corpus dan
   el mismo HTML. (El PDF NO es byte-determinista: WeasyPrint le embebe un
   timestamp. Ver el defecto 16 del informe.)

## Guardrails que ya estan puestos

| Regla (ADR-CG-002) | Como se implementa | Test |
|---|---|---|
| 0 · el LLM no porta credenciales | `Analizador` recibe una `Completion`, no un token de Meta | `test_cognitive.py` |
| 1 · output tipado o se descarta | Literal cerrados + `extra="forbid"` | `TestValidacionEstricta` |
| 6 · el copy ajeno es dato hostil | delimitadores neutralizados en la ingesta + taxonomia cerrada + `sin_urls` | `TestInyeccionEnElCopy`, `TestB3_ContaminacionCruzadaIntraLote` |
| 9 · aislamiento del scraper | `Settings.validar()` aborta si research y write comparten `app_id` | `TestConfigGuards` |

**La Regla 6 no la protege el prompt, la protege el esquema.** Si el modelo se
deja inyectar por completo y devuelve un valor fuera de la taxonomia, el resultado
es un `ValidationError` y un rechazo registrado. Hay un test **por cada campo
cerrado**, para que la contencion no dependa de que varios campos se cubran entre
si (defecto 12 del informe).

## Lo que NO esta verificado (declarado)

- **Nada corrio contra las APIs reales.** El sandbox donde se escribio esto no
  tiene red. `transporte_http()` y `cliente_deepseek()` estan escritos contra la
  documentacion y **no ejecutados**. La primera corrida real es la verificacion
  pendiente numero uno.
- **La calidad de clasificacion del modelo es NO MEDIDA.** El clasificador del
  `--dry-run` son heuristicas de palabra clave: sirve para validar el *pipeline*,
  nunca para evaluar la *calidad*. Eso necesita un set anotado a mano.
- **La tasa real de acierto del cache es NO MEDIDA.** Desde la revision 2 tiene
  instrumento (`Metricas.veredicto_cache()`, con guard a `UMBRAL_CACHE_HIT=0,80`),
  pero medirla exige el proveedor real. El `--dry-run` reporta "NO MEDIDO" a
  proposito, porque el clasificador de fixture no es un proveedor.
- **`estimar_tokens` no es un tokenizador** (~4 chars por token). Sirve para el
  reporte, no para facturar.
