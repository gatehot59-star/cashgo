# RESPUESTA A LA TERCERA PASADA EXTERNA (Fable 5.1, Abacus.AI)

**Auditoria recibida:** 2026-09-09, sobre el head `cbc9301`, contra el repo publico y sin credencial.
**Respondida:** 2026-09-09. Head de esta respuesta: ver `git log`.
**Documento que audito:** `03-INFORME-TECNICO-FABLE-5.1.md`.

Regla de esta respuesta: **ningun hallazgo ajeno se acepta de palabra y ninguno se rechaza sin medicion.** De los tres motivos por los que un hallazgo se puede caer (el sujeto era otro, el instrumento no discriminaba, o el dato ya estaba), cada punto de abajo dice cual aplica.

---

## 1. LO QUE ACEPTO SIN DESCUENTO

### 1.1 El rojo de `deps-pins` era de SEGURIDAD y tenia seis nombres (V-5)

Mi informe escribio, textual, en la verificacion adversarial 5: *"si el JSON dice `vulnerabilities` no vacio, el rojo es de SEGURIDAD y yo lo dejo en NO MEDIDO cuando el dato estaba publicado. **Esa es la falla mia mas probable de este informe**"*.

Era exactamente eso. Confirmado por mi lado contra NVD y los advisories del propio proyecto, o sea sin depender del reporte:

| Aviso | Que rompe | Fix |
|---|---|---|
| CVE-2026-71852 | `/W` de fuente CID sin cota, en extraccion de texto (CWE-834) | 6.15.0 |
| CVE-2026-84309 | `TreeObject.insert_child` sigue `/Next` en ciclo, loop infinito (CWE-835) | 6.16.0 |
| CVE-2026-84310 | `_get_outline` sin cota de profundidad ni de entradas | 6.16.1 |
| GHSA-23w6-3w8w-8484 | outlines con reuso de rutas anidadas | 6.16.1 |
| GHSA-763m-79hh-57f2 | XForm reusados en `extract_text` | 6.16.1 |
| + el sexto del mismo lote | | 6.16.1 |

**Pin corregido: `pypdf==6.16.1`.** Un porton BLOQUEANTE en rojo no se negocia con un argumento.

**Y el error de proceso, que es mas caro que el pin.** El dato estaba en OSV desde el 14 de agosto, publico y gratis. Mi diagnostico se trabo en "no puedo bajar el artifact ni abrir el log" y por eso el estado quedo NO MEDIDO dos dias enteros. Habia otra via evidente: consultar la base de advisories contra los tres pines, que son tres nombres y tres versiones. **No me faltaba informacion: deje de buscar en el primer obstaculo.**

### 1.2 Las tres rutas divergentes del manifiesto, y las dos que yo no predije (V-2)

No las acepte de palabra. Baje los dos archivos, verifique que mi canal de lectura no los deforma recomputando su `git blob sha1`, y recien despues compare los digest:

| Ruta | blob (transporte) | firma en el manifiesto | sha256 real | Veredicto |
|---|---|---|---|---|
| `evidencia/salida_control_positivo.txt` | `4aa47678` OK, 1.707 B | `e3825345...` | `4e17b5dd...` | **DIVERGE** |
| `evidencia/salida_tests_fase0.txt` | `29bc9017` OK, 746 B | `83e8310a...` | `3d0a2a2f...` | **DIVERGE** |

Las dos corregidas con el digest medido. Yo habia predicho **una** divergencia y habia **tres**.

**Y el diagnostico del auditor es mejor que el mio:** el manifiesto se firma ANTES de que se reescriban las salidas que declara firmar. Es *"el instrumento firmado antes que su objeto"*, el mismo patron que D4/41 pero adentro de la custodia.

### 1.3 El manifiesto plano no encadena, y eso permitio el defecto 39 (C5)

Correcto y es la observacion mas profunda de la pasada. Un manifiesto de 19 digests sin `prev_hash` permite reemplazar una linea y re-firmar sin que nada se rompa hacia adelante, que es **literalmente** lo que paso con la palabra en ruso: nadie lo detecto hasta que un lector externo conto caracteres.

Queda **abierto a proposito**: decidir cual de las cuatro implementaciones de esa primitiva sobrevive no es una decision de este repo.

---

## 2. LO QUE REFUTO, CON MEDICION

### 2.1 "La frontera de ingesta de este sistema son PDFs" (C4 y el descuento al criterio 4)

**Falso, y es E-01: se midio la libreria y se concluyo sobre el llamador.**

Medido sobre el arbol, `pypdf` aparece en **un solo lugar de las 5.205 lineas**:

```
fase0/tests/test_e2e_pipeline.py :: TestPdf.test_genera_un_pdf_no_trivial
    ruta = escribir_pdf(res.informe, ...)   <- WeasyPrint GENERA el pdf
    datos = ruta.read_bytes()
    lector = PdfReader(io.BytesIO(datos))   <- lee ESE pdf, dos lineas abajo
```

`fase0/report.py` importa `weasyprint.HTML` y **escribe**; no lee ningun PDF en ninguna ruta. El corpus entra como **JSON de `ads_archive`**. **No existe un camino de codigo por el que un PDF de un tercero llegue a `pypdf`.**

Los seis avisos son DoS por parseo de PDF hostil. Exposicion de produccion: **cero**. Exposicion de CI: un PDF que nosotros mismos acabamos de generar. Un fixture de PDF hostil seria un test para una amenaza que el sistema no tiene, o sea un guard sobre un sujeto que no es el de la afirmacion: el defecto exacto que este repo persigue.

**Pero hay un defecto real que el hallazgo destapo sin nombrarlo, y lo concedo:** `pypdf` estaba declarado como dependencia de **produccion** y es de **test**. `requirements.txt` ahora dice cual es cual con el motivo. Un pin mal categorizado hace que cualquiera lea un CVE de DoS como riesgo de produccion, que es precisamente lo que paso en esta pasada.

El descuento al criterio 4 queda **rechazado**, y aun asi **no me subo el puntaje**: eso lo decide la cuarta pasada, no el auditado.

---

## 3. LO QUE HICE CON LAS MEJORAS

| # | Mejora | Estado |
|---|---|---|
| C1 | `pypdf==6.16.1` | **HECHO.** Falsador: los dos jobs de deps en `success` |
| C2 | Firmar el manifiesto despues de regenerar las salidas | **HECHO, pero cambiando el instrumento y no el orden.** Ver 3.1 |
| C3 | Que `--verificar` diga la ruta que falla | **HECHO en su forma real.** Ver 3.2 |
| C4 | Test de PDF hostil | **RECHAZADO con medicion.** Ver 2.1 |
| C5 | Manifiesto encadenado (Testis) | **DIFERIDO** con motivo escrito. Ver 1.3 |
| C6 | Descripcion del PR generada por el CI | **DIFERIDO.** Hoy sigue escrita a mano y por eso D4 se va a reabrir otra vez |
| C7 | Meta, llamada real, golden set | **SIGUE ABIERTO** y sigue siendo lo unico que importa |

### 3.1 C2: firma la maquina, no el operador. Y declaro que se pierde.

Reordenar `cerrar.sh` no alcanza, y el motivo esta medido seis veces: mi canal de escritura transporta **texto**, asi que firmar 42 KB de prosa obliga a re-transcribirla y la copia siempre difiere. Una de esas re-transcripciones metio la palabra rusa dentro de un sha256 y dejo el manifiesto invalido por construccion durante dos dias. **Cuidar mas no arregla eso.**

Job nuevo `custodia-4`, con `contents: write` y solo en push a `titan/**`: corre `--escribir` y si el manifiesto cambio, lo commitea. La maquina que puede leer los bytes es la que firma.

**MEDIDO, y funciono:** el job corrio **8 segundos** despues del push, autor `github-actions[bot]`, y cambio **exactamente una linea**: la del informe de 42 KB, la unica que yo no podia calcular. La dejo en `59b6258988d112f36e5b66f010a67aefe8751506e37a2e0accd19ef30a8af50f`.

Control de que fue solo eso: tome mi copia local del manifiesto, le cambie unicamente esa linea y recompute el object id de git. Da `12fe67fe22a36deb3bacbc37d040fd34583fc4b0`, **identico** al blob que sirve la API para el head del bot. O sea que mis 19 lineas viajaron byte-exactas y la maquina toco una sola.

**LO QUE SE PIERDE, declarado en el YAML y no solo aca:** el manifiesto deja de detectar *"alguien edito el informe y no regenero los recibos"*, porque la maquina re-firma lo que encuentra. Esa propiedad la sigue dando git, que direcciona por contenido y guarda el historial. Lo que el manifiesto conserva, que es para lo que se creo (A1), es que un tercero compruebe que el documento que recibio **es** el del repo. Un arreglo que no declara que empeora es media medicion.

**DEFECTO 43, nuevo, medido despues de escribir el job:** los commits que empuja el `GITHUB_TOKEN` **no disparan workflows** (proteccion de GitHub contra loops). Asi que `custodia-4` arregla el arbol y deja el veredicto sin actualizar: el head del bot tenia **cero** check runs. La auto-firma converge en **dos** pushes, no en uno. No lo sabia cuando escribi el job.

### 3.2 C3: el problema no era el script, era el canal

`--verificar` **ya imprimia** la ruta con `DIFIERE` / `FALTA` / `SIN FIRMA`. El problema es que esa salida vive en un log que nadie del equipo puede abrir, y por eso un auditor externo tuvo que recomputar 19 sha256 a mano para decirnos cuales tres divergian.

**El nombre del check run es el unico canal de diagnostico que se lee por API sin abrir un log.** Asi que `custodia` se parte en cuatro jobs, uno por pregunta:

```
custodia-1 (el conteo describe el arbol)
custodia-2 (el informe cita el CSV real)
custodia-3 (las firmas describen el arbol)
custodia-4 (re-firma el manifiesto)
```

Es la **cuarta** vez que este repo llega a la misma conclusion por el mismo camino: un job que agrupa dos preguntas devuelve media respuesta. Ademas los tres portones escriben su veredicto en `GITHUB_STEP_SUMMARY` y suben su salida como artifact.

---

## 4. LO QUE LA PASADA CAMBIA EN EL ESTADO DEL PROYECTO

**Cerrados por el auditor, no por mi:** NO MEDIDO #4 (causa del rojo de deps) y, casi entero, NO MEDIDO #6 (17 digests sin verificar pasan a cero: 18 los medimos entre los dos y el 19 lo firma la maquina).

**Sigue igual, y es lo unico que decide si esto es un negocio:** cero llamadas reales a `ads_archive`, cero a DeepSeek, cero golden set, cero clientes. La palanca critica es **un click de verificacion de identidad en Meta**, frenada desde el 7 de septiembre, y ningun commit la mueve.

Sobre el encuadre del auditor: tiene razon en que el mercado esta en UE/UK y el operador en Argentina, y en que **el rail de cobro es lo primero y no lo ultimo**. Tambien en que el limite del DSA, mirado del otro lado, **es** la barrera de entrada: quien tenga la identidad verificada y el pipeline tiene un dato que un agente no puede ir a buscar solo.

**Rubrica: sigue en 70/100.** No sube por este turno. Los dos jobs bloqueantes tienen que dar verde por si mismos primero, y eso lo dice el CI, no yo.
