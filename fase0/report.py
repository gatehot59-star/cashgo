"""
Construccion y renderizado del informe comercial.

CERO LLM EN ESTE MODULO. Contar, ordenar, calcular medianas y sacar diferencias
de conjuntos es trabajo determinista: un LLM haciendolo es un LLM equivocandose
gratis, y ademas irreproducible entre corridas. Es la regla Cerebro vs Brazo
aplicada al entregable, no solo a las escrituras.

La narrativa opcional (un parrafo de Pro) entra como texto, pasa por el MISMO
filtro de URLs que la promesa (H-03) y se ESCAPA al renderizar, igual que el copy
de los competidores. Un informe que se genera a partir de texto de terceros y se
abre en un navegador es una superficie de XSS, aunque el "navegador" sea WeasyPrint.
"""
from __future__ import annotations

import html
import statistics
from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import date, datetime, timezone
from pathlib import Path

from .schemas import (
    AnalisisAnuncio,
    AnuncioCrudo,
    FilaCompetidor,
    Informe,
    normalizar,
    sin_urls,
)

TODOS_LOS_ANGULOS: tuple[str, ...] = (
    "precio", "urgencia", "prueba_social", "autoridad", "miedo_perdida",
    "aspiracional", "garantia", "novedad", "comparacion", "educativo",
)
# "otro" queda afuera a proposito: un angulo no explotado tiene que ser
# accionable, y "proba el angulo otro" no le sirve a nadie.

# Umbral de longevidad para considerar un anuncio "probado". No es una medicion:
# es una convencion del sector (un anuncio que sobrevive dos meses no es un test).
# Va declarada como convencion en la pagina de metodologia del informe.
DIAS_PARA_CONSIDERAR_PROBADO = 60


def _contar(valores: Iterable[str]) -> tuple[tuple[str, int], ...]:
    """Cuenta y ordena por frecuencia desc, y por nombre asc para desempatar.

    El desempate alfabetico no es cosmetico: sin el, dos corridas con los mismos
    datos pueden producir informes con filas en distinto orden, y entonces no se
    pueden comparar (ni testear).
    """
    c = Counter(valores)
    return tuple(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))


def construir_informe(
    *,
    prospecto_nombre: str,
    prospecto_page_id: str,
    nicho: str,
    paises: Sequence[str],
    anuncios_prospecto: Sequence[AnuncioCrudo],
    anuncios_competencia: Sequence[AnuncioCrudo],
    analisis: dict[str, AnalisisAnuncio],
    rechazos: int,
    descartados_por_dedup: int,
    narrativa: str = "",
    hoy: date | None = None,
) -> Informe:
    """
    Agrega los analisis en un informe. `analisis` va indexado por ad_id.

    Los anuncios sin analisis se cuentan en el corpus pero no en las
    distribuciones. Eso es a proposito: un anuncio que no se pudo clasificar no
    es un anuncio de angulo "otro", es un anuncio NO MEDIDO. Meterlo en "otro"
    seria inventar una senal.
    """
    hoy = hoy or datetime.now(timezone.utc).date()

    por_pagina: dict[str, list[AnuncioCrudo]] = {}
    for ad in anuncios_competencia:
        por_pagina.setdefault(ad.page_id, []).append(ad)

    competidores: list[FilaCompetidor] = []
    for page_id, ads in por_pagina.items():
        dias = [a.dias_activo(hoy) for a in ads]
        angs = [analisis[a.ad_id].angulo for a in ads if a.ad_id in analisis]
        fmts = [analisis[a.ad_id].formato for a in ads if a.ad_id in analisis]
        competidores.append(FilaCompetidor(
            page_id=page_id,
            page_name=ads[0].page_name or page_id,
            anuncios=len(ads),
            activos=sum(1 for a in ads if a.esta_activo),
            dias_activo_mediana=int(statistics.median(dias)) if dias else 0,
            dias_activo_max=max(dias) if dias else 0,
            angulos=_contar(angs),
            formatos=_contar(fmts),
        ))
    competidores.sort(key=lambda f: (-f.dias_activo_mediana, -f.anuncios, f.page_name))

    angs_comp = [analisis[a.ad_id].angulo for a in anuncios_competencia if a.ad_id in analisis]
    angs_pros = {analisis[a.ad_id].angulo for a in anuncios_prospecto if a.ad_id in analisis}

    # El gap: angulos que la competencia usa y el prospecto no. Es una diferencia
    # de conjuntos, y esa simpleza es la razon por la que es defendible frente al
    # cliente: no hay modelo opinando, hay dos listas y una resta.
    usados_por_comp = {a for a, _ in _contar(angs_comp)}
    no_explotados = tuple(
        a for a, _ in _contar(angs_comp)
        if a in usados_por_comp and a not in angs_pros and a in TODOS_LOS_ANGULOS
    )

    # Formato "ganador" = el que la competencia sostiene mas tiempo, no el que
    # mas aparece. Aparecer mucho puede ser una agencia haciendo volumen.
    dias_por_formato: dict[str, list[int]] = {}
    for a in anuncios_competencia:
        an = analisis.get(a.ad_id)
        if an is None:
            continue
        dias_por_formato.setdefault(an.formato, []).append(a.dias_activo(hoy))
    formatos_ganadores = tuple(sorted(
        ((f, len(v), int(statistics.median(v))) for f, v in dias_por_formato.items()),
        key=lambda t: (-t[2], -t[1], t[0]),
    ))

    longevos_src = [
        (a.page_name or a.page_id, analisis[a.ad_id].promesa, a.dias_activo(hoy))
        for a in anuncios_competencia
        if a.ad_id in analisis and a.dias_activo(hoy) >= DIAS_PARA_CONSIDERAR_PROBADO
    ]
    longevos = tuple(sorted(longevos_src, key=lambda t: (-t[2], t[0]))[:12])

    return Informe(
        prospecto_nombre=normalizar(prospecto_nombre),
        prospecto_page_id=prospecto_page_id,
        nicho=normalizar(nicho),
        paises=tuple(p.upper() for p in paises),
        generado_en=datetime.now(timezone.utc),
        anuncios_prospecto=len(anuncios_prospecto),
        anuncios_competencia=len(anuncios_competencia),
        competidores=tuple(competidores),
        distribucion_angulos=_contar(angs_comp),
        angulos_del_prospecto=tuple(sorted(angs_pros)),
        angulos_no_explotados=no_explotados,
        formatos_ganadores=formatos_ganadores,
        longevos=longevos,
        rechazos=rechazos,
        anuncios_descartados_por_dedup=descartados_por_dedup,
        # H-03 (auditoria independiente de Tao, 2026-09-07): `sin_urls` protegia
        # `promesa` y `publico_sugerido` y NO la narrativa, que es el campo mas
        # expuesto de los tres: es texto que genera el modelo Pro a partir del copy
        # de terceros, o sea el unico donde una inyeccion indirecta puede ELEGIR
        # que se imprime en un PDF que firmamos nosotros. Latente hoy porque
        # `pipeline.main` no pasa narrativa; el dia que se conecte el parrafo de
        # Pro el agujero se abria solo y en silencio.
        narrativa=sin_urls(normalizar(narrativa))[:1200],
    )


# --- renderizado -------------------------------------------------------------

_CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm;
        @bottom-center { content: counter(page) " / " counter(pages);
                         font: 8pt "DejaVu Sans"; color: #8a8a8a; } }
body { font-family: "DejaVu Sans", sans-serif; font-size: 9.5pt; color: #1d1d1f; line-height: 1.45; }
h1 { font-size: 21pt; margin: 0 0 2mm 0; letter-spacing: -0.3pt; }
h2 { font-size: 12pt; margin: 8mm 0 2mm 0; padding-bottom: 1.5mm;
     border-bottom: 1.2pt solid #1d1d1f; }
h3 { font-size: 10pt; margin: 5mm 0 1.5mm 0; }
.sub { color: #6a6a6a; font-size: 9pt; margin: 0 0 6mm 0; }
table { width: 100%; border-collapse: collapse; margin: 2mm 0 4mm 0; font-size: 8.5pt; }
th { text-align: left; background: #f2f2f4; padding: 1.8mm 2mm; font-weight: bold;
     border-bottom: 0.8pt solid #d4d4d8; }
td { padding: 1.6mm 2mm; border-bottom: 0.4pt solid #e8e8ec; vertical-align: top; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.bar { background: #1d1d1f; height: 7px; display: inline-block; vertical-align: middle; }
.bar-bg { background: #ececf0; height: 7px; width: 100%; display: block; }
.kpi { display: inline-block; width: 30%; padding: 3mm 0; }
.kpi .v { font-size: 17pt; font-weight: bold; display: block; }
.kpi .l { font-size: 7.5pt; color: #6a6a6a; text-transform: uppercase; letter-spacing: 0.4pt; }
.gap { background: #fff8e1; border-left: 2.5pt solid #d4a017; padding: 2.5mm 3mm; margin: 2mm 0; }
.nota { background: #f6f6f8; border-left: 2.5pt solid #9a9aa2; padding: 2.5mm 3mm;
        font-size: 8pt; color: #4a4a52; margin: 3mm 0; }
.pill { display: inline-block; background: #ececf0; border-radius: 2mm;
        padding: 0.6mm 2mm; font-size: 8pt; margin: 0 1mm 1mm 0; }
ul { margin: 1mm 0 3mm 5mm; padding: 0; }
li { margin-bottom: 1.2mm; }
.pagebreak { page-break-before: always; }
a { color: #1d1d1f; text-decoration: none; }
"""


def _e(valor: object) -> str:
    """Escape obligatorio. Todo lo que viene del corpus pasa por aca."""
    return html.escape(str(valor), quote=True)


def _barra(n: int, maximo: int) -> str:
    pct = 0 if maximo <= 0 else max(2, round(n / maximo * 100))
    return f'<span class="bar-bg"><span class="bar" style="width:{pct}%"></span></span>'


def informe_a_html(inf: Informe) -> str:
    max_ang = max((n for _, n in inf.distribucion_angulos), default=0)
    total_ang = sum(n for _, n in inf.distribucion_angulos)

    filas_ang = "".join(
        f"<tr><td>{_e(a)}</td><td class='num'>{n}</td>"
        f"<td class='num'>{n / total_ang * 100:.0f}%</td>"
        f"<td style='width:38%'>{_barra(n, max_ang)}</td>"
        f"<td>{'usado' if a in inf.angulos_del_prospecto else '<b>sin usar</b>'}</td></tr>"
        for a, n in inf.distribucion_angulos
    ) or "<tr><td colspan='5'>Sin anuncios clasificados.</td></tr>"

    filas_comp = "".join(
        f"<tr><td>{_e(f.page_name)}</td><td class='num'>{f.anuncios}</td>"
        f"<td class='num'>{f.activos}</td><td class='num'>{f.dias_activo_mediana}</td>"
        f"<td class='num'>{f.dias_activo_max}</td>"
        f"<td>{', '.join(_e(a) for a, _ in f.angulos[:3]) or '&mdash;'}</td></tr>"
        for f in inf.competidores
    ) or "<tr><td colspan='6'>Sin competidores con anuncios en el periodo.</td></tr>"

    filas_fmt = "".join(
        f"<tr><td>{_e(f)}</td><td class='num'>{n}</td><td class='num'>{d}</td></tr>"
        for f, n, d in inf.formatos_ganadores
    ) or "<tr><td colspan='3'>Sin datos de formato.</td></tr>"

    filas_long = "".join(
        f"<tr><td>{_e(m)}</td><td>{_e(p) or '&mdash;'}</td><td class='num'>{d}</td></tr>"
        for m, p, d in inf.longevos
    ) or (f"<tr><td colspan='3'>Ningun anuncio supera los "
          f"{DIAS_PARA_CONSIDERAR_PROBADO} dias activos.</td></tr>")

    gaps = "".join(
        f"<div class='gap'><b>{_e(a)}</b> &mdash; lo usan "
        f"{dict(inf.distribucion_angulos).get(a, 0)} anuncios de la competencia "
        f"y ninguno tuyo.</div>"
        for a in inf.angulos_no_explotados
    ) or ("<p>No detectamos angulos que la competencia use y vos no. "
          "Eso es una buena noticia sobre tu cobertura y significa que la "
          "oportunidad esta en la ejecucion, no en el angulo.</p>")

    narrativa = (f"<h2>Lectura estrategica</h2><p>{_e(inf.narrativa)}</p>"
                 if inf.narrativa else "")

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Auditoria publicitaria &mdash; {_e(inf.prospecto_nombre)}</title>
<style>{_CSS}</style></head><body>

<h1>Auditoria publicitaria competitiva</h1>
<p class="sub"><b>{_e(inf.prospecto_nombre)}</b> &nbsp;&middot;&nbsp; nicho:
{_e(inf.nicho)} &nbsp;&middot;&nbsp; mercados: {_e(', '.join(inf.paises))}
&nbsp;&middot;&nbsp; generado el {inf.generado_en:%d/%m/%Y %H:%M} UTC</p>

<div>
  <span class="kpi"><span class="v">{inf.anuncios_competencia}</span>
    <span class="l">anuncios de competencia analizados</span></span>
  <span class="kpi"><span class="v">{len(inf.competidores)}</span>
    <span class="l">marcas monitoreadas</span></span>
  <span class="kpi"><span class="v">{len(inf.angulos_no_explotados)}</span>
    <span class="l">angulos sin explotar</span></span>
</div>

<h2>1. Angulos que no estas usando</h2>
<p>Un <i>angulo</i> es la palanca psicologica principal del anuncio. Comparamos
los {inf.anuncios_competencia} anuncios de tu competencia contra tus
{inf.anuncios_prospecto}.</p>
{gaps}

<h2>2. Distribucion de angulos en el mercado</h2>
<table><thead><tr><th>Angulo</th><th class="num">Anuncios</th>
<th class="num">Share</th><th>Peso relativo</th><th>Tu cuenta</th></tr></thead>
<tbody>{filas_ang}</tbody></table>

<h2>3. Tus competidores, por persistencia</h2>
<p>Ordenados por <b>mediana de dias activos</b>, no por cantidad de anuncios: un
anuncio que la competencia sostiene mucho tiempo es la unica senal de exito que
esta biblioteca publica.</p>
<table><thead><tr><th>Marca</th><th class="num">Anuncios</th><th class="num">Activos</th>
<th class="num">Dias (mediana)</th><th class="num">Dias (max)</th>
<th>Angulos dominantes</th></tr></thead><tbody>{filas_comp}</tbody></table>

<div class="pagebreak"></div>

<h2>4. Formatos que el mercado sostiene</h2>
<table><thead><tr><th>Formato</th><th class="num">Anuncios</th>
<th class="num">Dias activos (mediana)</th></tr></thead><tbody>{filas_fmt}</tbody></table>

<h2>5. Anuncios probados de tu competencia</h2>
<p>Creatividades con {DIAS_PARA_CONSIDERAR_PROBADO} dias o mas de entrega
continua. A esta altura ya no son un test.</p>
<table><thead><tr><th>Marca</th><th>Promesa</th>
<th class="num">Dias</th></tr></thead><tbody>{filas_long}</tbody></table>

{narrativa}

<h2>6. Metodologia y limites de este informe</h2>
<p>Los datos salen de la <b>Ad Library API oficial de Meta</b>
(endpoint <span class="pill">ads_archive</span>), consultada para los mercados
{_e(', '.join(inf.paises))}. Es una fuente publica de transparencia publicitaria.
No accedemos a ninguna cuenta publicitaria, ni tuya ni de terceros.</p>

<div class="nota">
<b>Lo que este informe NO puede decirte, y por que.</b><br>
Para anuncios comerciales, Meta <b>no publica</b> presupuesto, impresiones, CTR
ni conversiones: esas metricas solo son publicas para anuncios sobre temas
sociales, elecciones o politica. Por eso <b>no vas a encontrar aca cuanto gasta
tu competencia</b>. Cualquier proveedor que te muestre ese numero para un anuncio
comercial lo esta estimando, no midiendo.<br><br>
La unica senal de exito disponible es <b>el tiempo que un anuncio lleva
activo</b>, bajo el supuesto de que un anunciante racional apaga lo que no
funciona. Es un supuesto razonable y es un supuesto: un anuncio tambien puede
seguir corriendo por inercia. Los {DIAS_PARA_CONSIDERAR_PROBADO} dias que usamos
como umbral de "probado" son una convencion nuestra, no un dato de Meta.<br><br>
Cobertura: por el <b>Digital Services Act</b>, Meta publica todos los anuncios
entregados a usuarios de la UE y UK durante aproximadamente 12 meses. Fuera de
esos mercados la API no devuelve anuncios comerciales, asi que un competidor que
solo pauta en otras regiones <b>no aparece aca</b>, y su ausencia no significa
que no anuncie.<br><br>
Trazabilidad de esta corrida: {inf.anuncios_competencia} anuncios de competencia
en el corpus, {inf.anuncios_descartados_por_dedup} descartados por deduplicacion
(ya analizados en corridas anteriores), {inf.rechazos} descartados por no pasar
la validacion de esquema. Los descartados por validacion se registran y
<b>no se cuentan como angulo "otro"</b>: quedan como no medidos.
</div>

<p class="sub" style="margin-top:6mm">Este documento es inteligencia de mercado
derivada de fuentes publicas. No constituye asesoramiento financiero ni garantiza
resultados publicitarios.</p>

</body></html>"""


def escribir_pdf(inf: Informe, destino: str | Path) -> Path:
    """Renderiza el informe a PDF con WeasyPrint. Devuelve la ruta escrita."""
    from weasyprint import HTML  # import perezoso: es la dependencia mas pesada

    ruta = Path(destino)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=informe_a_html(inf)).write_pdf(str(ruta))
    return ruta


def escribir_html(inf: Informe, destino: str | Path) -> Path:
    """Escribe el HTML crudo. Util para revisar el informe sin abrir un PDF."""
    ruta = Path(destino)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(informe_a_html(inf), encoding="utf-8")
    return ruta
