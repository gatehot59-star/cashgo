"""
Orquestacion de la Fase 0 y CLI.

El orden de los pasos NO es estetico, cada uno esta donde esta por un motivo
medido:

  1. traer          -> ads_archive oficial, UE/UK, batch de 10 page_ids, cursor
  2. persistir      -> antes de gastar un solo token: si el modelo falla, el
                       corpus ya esta guardado y la proxima corrida no lo re-baja
  3. DEDUP          -> aca se decide el 88% del costo, y no hay IA involucrada
  4. Flash por lote -> prefijo estable primero, validacion estricta, sin reintento
  5. agregar        -> determinista, cero LLM
  6. renderizar     -> PDF, con escapado obligatorio

El paso 2 antes del 3 y del 4 es deliberado: guardar el crudo es barato, y una
corrida que muere en el paso 4 no debe costar dos veces el paso 1 (que es el que
consume el rate limit escaso).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from . import config
from .adlibrary import AdsArchiveClient, Transport, transporte_http
from .cognitive import (
    PREFIJO_SHA256,
    Analizador,
    Completion,
    cliente_deepseek,
    estimar_tokens,
)
from .dedup import particionar
from .report import construir_informe, escribir_html, escribir_pdf
from .schemas import AnalisisAnuncio, AnuncioCrudo, Informe
from .store import Store


@dataclass
class Metricas:
    """Todo lo que la corrida quiere poder demostrar despues."""

    anuncios_traidos: int = 0
    anuncios_nuevos: int = 0
    anuncios_ya_vistos: int = 0
    duplicados_en_lote: int = 0
    lotes_al_modelo: int = 0
    analisis_validos: int = 0
    rechazos: int = 0
    llamadas_api: int = 0
    reintentos_613: int = 0
    tokens_prefijo_por_lote: int = 0
    prefijo_sha256: str = PREFIJO_SHA256
    motivos_rechazo: list[str] = field(default_factory=list)

    @property
    def ratio_dedup(self) -> float:
        if self.anuncios_traidos == 0:
            return 0.0
        return (self.anuncios_ya_vistos + self.duplicados_en_lote) / self.anuncios_traidos

    def como_dict(self) -> dict[str, object]:
        d = {k: v for k, v in self.__dict__.items()}
        d["ratio_dedup"] = round(self.ratio_dedup, 4)
        return d


@dataclass
class Resultado:
    informe: Informe
    metricas: Metricas
    pdf: Path | None = None
    html: Path | None = None


def correr_auditoria(
    *,
    store: Store,
    cliente: AdsArchiveClient,
    analizador: Analizador,
    prospecto_page_id: str,
    prospecto_nombre: str,
    competidores_page_ids: Sequence[str],
    nicho: str,
    paises: Sequence[str],
    desde: date | None = None,
    hoy: date | None = None,
    narrativa: str = "",
) -> Resultado:
    """
    Corre la auditoria completa y devuelve el informe mas las metricas.

    No escribe archivos: eso lo decide el llamador. Asi la funcion es testeable
    sin tocar el disco mas alla del SQLite.
    """
    m = Metricas(tokens_prefijo_por_lote=estimar_tokens(""))
    todas_las_paginas = [str(prospecto_page_id), *[str(p) for p in competidores_page_ids]]

    store.log("corrida_inicio", {
        "prospecto": prospecto_page_id,
        "competidores": len(competidores_page_ids),
        "paises": list(paises),
        "prefijo_sha256": PREFIJO_SHA256,
        "modelo": analizador.modelo,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })

    # 1. traer
    traidos: list[AnuncioCrudo] = list(cliente.anuncios_de(todas_las_paginas, desde=desde))
    m.anuncios_traidos = len(traidos)
    m.llamadas_api = cliente.llamadas_hechas
    m.reintentos_613 = cliente.reintentos_613

    # 2. persistir el crudo ANTES de gastar un token
    store.guardar_anuncios(traidos)

    # 3. dedup determinista
    #
    # Se particiona contra los hashes que ya tenian ANALISIS, no contra los del
    # corpus: los que acabamos de insertar en el paso 2 ya estan en el corpus, asi
    # que compararlos contra el corpus daria 100% de dedup y cero analisis.
    con_analisis = set(store.analisis_de(todas_las_paginas).keys())
    part = particionar(traidos, con_analisis)
    m.anuncios_nuevos = len(part.nuevos)
    m.anuncios_ya_vistos = len(part.ya_vistos)
    m.duplicados_en_lote = part.duplicados_en_lote

    # 4. modelo, solo sobre lo nuevo
    #
    # El resultado se indexa por CONTENT_HASH, no por ad_id. Eso es lo que hace
    # que el dedup sea gratis en vez de destructivo: una creatividad se clasifica
    # UNA vez y se atribuye a TODOS los ad_id que la comparten.
    #
    # DEFECTO PROPIO CAZADO POR test_la_segunda_corrida_produce_el_mismo_informe
    # (2026-09-06): la version anterior indexaba por ad_id, asi que el duplicado
    # intra-lote (misma creatividad, otro ad_id: una agencia reciclando) quedaba
    # SIN analisis en la primera corrida y CON analisis en la segunda, porque en
    # la segunda lo recuperaba de la base por hash. Resultado: dos informes
    # distintos para el mismo corpus. Un producto de inteligencia recurrente cuyo
    # informe cambia solo entre corridas no vale nada, y el bug era invisible en
    # una sola corrida.
    analisis_por_hash: dict[str, AnalisisAnuncio] = {}
    for i in range(0, len(part.nuevos), config.ANUNCIOS_POR_LOTE):
        lote = list(part.nuevos[i:i + config.ANUNCIOS_POR_LOTE])
        res = analizador.analizar(lote)
        m.lotes_al_modelo += 1
        m.tokens_prefijo_por_lote = res.tokens_prefijo
        por_ad = {a.ad_id: a for a in lote}
        pares = [
            (por_ad[an.ad_id].content_hash(), an)
            for an in res.analisis if an.ad_id in por_ad
        ]
        store.guardar_analisis(pares, analizador.modelo)
        for h, an in pares:
            analisis_por_hash[h] = an
        m.rechazos += len(res.rechazos)
        m.motivos_rechazo.extend(r.motivo for r in res.rechazos)
        if res.rechazos:
            store.log("rechazos_lote", {
                "lote": m.lotes_al_modelo,
                "n": len(res.rechazos),
                "motivos": [r.motivo for r in res.rechazos][:20],
            })

    # Lo ya visto reusa su analisis persistido: ese es el punto del dedup.
    for h, fila in store.analisis_de(todas_las_paginas).items():
        if h in analisis_por_hash:
            continue
        analisis_por_hash[h] = AnalisisAnuncio(
            ad_id=str(fila["ad_id"]),
            angulo=str(fila["angulo"]),          # type: ignore[arg-type]
            hook=str(fila["hook"]),              # type: ignore[arg-type]
            cta=str(fila["cta"]),                # type: ignore[arg-type]
            formato=str(fila["formato"]),        # type: ignore[arg-type]
            promesa=str(fila["promesa"]),
            publico_sugerido=str(fila["publico"]),
            confianza=float(fila["confianza"]),
        )

    # Reproyeccion hash -> ad_id: cada anuncio del corpus recibe el analisis de su
    # creatividad, con SU propio ad_id.
    analisis_por_ad: dict[str, AnalisisAnuncio] = {}
    for ad in traidos:
        an = analisis_por_hash.get(ad.content_hash())
        if an is not None:
            analisis_por_ad[ad.ad_id] = an.model_copy(update={"ad_id": ad.ad_id})
    m.analisis_validos = len(analisis_por_ad)

    # 5. agregar (determinista)
    prospecto = [a for a in traidos if a.page_id == str(prospecto_page_id)]
    competencia = [a for a in traidos if a.page_id != str(prospecto_page_id)]
    informe = construir_informe(
        prospecto_nombre=prospecto_nombre or (prospecto[0].page_name if prospecto else "Prospecto"),
        prospecto_page_id=str(prospecto_page_id),
        nicho=nicho,
        paises=paises,
        anuncios_prospecto=prospecto,
        anuncios_competencia=competencia,
        analisis=analisis_por_ad,
        rechazos=m.rechazos,
        descartados_por_dedup=m.anuncios_ya_vistos + m.duplicados_en_lote,
        narrativa=narrativa,
        hoy=hoy,
    )

    store.log("corrida_fin", m.como_dict())
    return Resultado(informe=informe, metricas=m)


# --- CLI ---------------------------------------------------------------------

def _cargar_brief(ruta: str) -> dict[str, object]:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    faltan = [k for k in ("prospecto_page_id", "competidores_page_ids", "nicho") if k not in datos]
    if faltan:
        raise SystemExit(f"el brief no tiene las claves obligatorias: {faltan}")
    return datos


def _transporte_fixture(ruta: str) -> Transport:
    """
    Transporte de --dry-run: lee un fixture y simula paginacion.

    Existe para que el pipeline completo se pueda correr y verificar SIN red y
    SIN gastar rate limit de Meta. Es el instrumento que hace que los tests
    puedan dar rojo de verdad.
    """
    paginas = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if isinstance(paginas, dict):
        paginas = [paginas]
    estado = {"i": 0}

    def _t(_url: str, _params: dict[str, object]) -> dict[str, object]:
        i = min(estado["i"], len(paginas) - 1)
        estado["i"] += 1
        return paginas[i]

    return _t


def _completion_fixture() -> Completion:
    """
    Clasificador deterministico por reglas, en lugar del modelo.

    NO ES UN MODELO Y NO PRETENDE SERLO: son heuristicas de palabra clave para
    que el --dry-run produzca un informe completo y revisable de punta a punta.
    Sirve para validar el PIPELINE, nunca para evaluar la CALIDAD de la
    clasificacion. Esa evaluacion necesita el modelo real y va declarada como
    pendiente.
    """
    import re

    reglas: list[tuple[str, str]] = [
        (r"\b(\d+\s*%|descuento|oferta|rebaja|barato|precio)\b", "precio"),
        (r"\b(ultim|hoy|solo por|termina|quedan|24 ?h|ahora)\b", "urgencia"),
        (r"\b(client|opini|rese|valorad|\d+\.?\d*\s*(mil|k)\b|personas)\b", "prueba_social"),
        (r"\b(experto|premiad|certificad|anos de|lider)\b", "autoridad"),
        (r"\b(no te pierdas|antes de que|se agota|perde)\b", "miedo_perdida"),
        (r"\b(garant|devoluc|30 dias|sin riesgo)\b", "garantia"),
        (r"\b(nuevo|nueva|estren|lanzamiento|acaba de)\b", "novedad"),
        (r"\b(mejor que|frente a|comparad|vs\.?)\b", "comparacion"),
        (r"\b(como|guia|aprende|descubri|te explicamos)\b", "educativo"),
        (r"\b(sonad|imagina|merece|transform|vida)\b", "aspiracional"),
    ]
    hooks: list[tuple[str, str]] = [
        (r"^\s*[^.!?]*\?", "pregunta"),
        (r"\b\d+\s*%|\b\d{2,}\b", "dato_duro"),
        (r"\b(compra|llev|consegu|pedi)\b", "oferta_directa"),
        (r"\b(dijo|conto|cuando|historia)\b", "historia"),
    ]
    ctas: list[tuple[str, str]] = [
        (r"\b(compra|comprar|carrito|llevalo)\b", "comprar"),
        (r"\b(registr|suscrib|crea tu cuenta)\b", "registrarse"),
        (r"\b(escribinos|mensaje|whatsapp|dm)\b", "mensaje_directo"),
        (r"\b(descarg|baja la)\b", "descargar"),
        (r"\b(agend|reserv|turno|cita)\b", "agendar"),
        (r"\b(mas info|conoce|ver mas|descubri mas)\b", "mas_info"),
    ]

    def _primero(pares: list[tuple[str, str]], texto: str, defecto: str) -> str:
        for patron, etiqueta in pares:
            if re.search(patron, texto, re.IGNORECASE):
                return etiqueta
        return defecto

    def _c(_modelo: str, mensajes: list[dict[str, str]], _temp: float) -> str:
        user = mensajes[-1]["content"]
        bloques = re.findall(r"<<<ANUNCIO>>>(.*?)<<<FIN>>>", user, re.DOTALL)
        salida = []
        for b in bloques:
            mid = re.search(r"ad_id:\s*(\S+)", b)
            mcopy = re.search(r"copy:\s*(.*)", b)
            ad_id = mid.group(1) if mid else "?"
            copy = (mcopy.group(1) if mcopy else "").strip()
            plats = re.search(r"plataformas:\s*(.*)", b)
            fmt = "desconocido"
            if plats and "instagram" in plats.group(1) and "facebook" in plats.group(1):
                fmt = "imagen"
            salida.append({
                "ad_id": ad_id,
                "angulo": _primero(reglas, copy, "otro"),
                "hook": _primero(hooks, copy, "otro"),
                "cta": _primero(ctas, copy, "otro"),
                "formato": fmt,
                "promesa": copy[:240],
                "publico_sugerido": "no inferido por el clasificador de fixture",
                "confianza": 0.4 if copy else 0.0,
            })
        return json.dumps({"analisis": salida}, ensure_ascii=False)

    return _c


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="cashgo-fase0",
        description="Genera la auditoria publicitaria competitiva (lead magnet).",
    )
    p.add_argument("brief", help="JSON con prospecto_page_id, competidores_page_ids, nicho")
    p.add_argument("--dry-run", metavar="FIXTURE",
                   help="corre sin red usando un fixture de ads_archive y un "
                        "clasificador por reglas en vez del modelo")
    p.add_argument("--salida", default=None, help="directorio de salida")
    p.add_argument("--pdf", action="store_true", help="renderizar PDF (requiere WeasyPrint)")
    p.add_argument("--desde", default=None, help="ad_delivery_date_min (YYYY-MM-DD)")
    args = p.parse_args(argv)

    brief = _cargar_brief(args.brief)
    st = config.Settings.from_env()
    paises = tuple(brief.get("paises") or st.paises)  # type: ignore[arg-type]

    problemas = st.validar(requiere_red=not args.dry_run)
    if problemas:
        for x in problemas:
            print(f"CONFIG: {x}", file=sys.stderr)
        return 2

    salida = Path(args.salida or st.salida_dir)
    desde = date.fromisoformat(args.desde) if args.desde else None

    if args.dry_run:
        transporte: Transport = _transporte_fixture(args.dry_run)
        completion: Completion = _completion_fixture()
        db = ":memory:"
    else:
        transporte = transporte_http()
        completion = cliente_deepseek(st.deepseek_api_key)
        db = st.db_path

    with Store(db) as store:
        cliente = AdsArchiveClient(st.token_ads_archive or "dry-run", transporte, paises=paises)
        res = correr_auditoria(
            store=store,
            cliente=cliente,
            analizador=Analizador(completion),
            prospecto_page_id=str(brief["prospecto_page_id"]),
            prospecto_nombre=str(brief.get("prospecto_nombre") or ""),
            competidores_page_ids=list(brief["competidores_page_ids"]),  # type: ignore[arg-type]
            nicho=str(brief["nicho"]),
            paises=paises,
            desde=desde,
        )
        slug = "".join(c if c.isalnum() else "-" for c in res.informe.prospecto_nombre.lower())[:40]
        res.html = escribir_html(res.informe, salida / f"auditoria-{slug}.html")
        if args.pdf:
            res.pdf = escribir_pdf(res.informe, salida / f"auditoria-{slug}.pdf")

    m = res.metricas
    print("=" * 72)
    print(f"AUDITORIA GENERADA - {res.informe.prospecto_nombre}")
    print("=" * 72)
    print(f"  anuncios traidos ................ {m.anuncios_traidos:>6}")
    print(f"  nuevos (pagaron tokens) ......... {m.anuncios_nuevos:>6}")
    print(f"  ya vistos (dedup) ............... {m.anuncios_ya_vistos:>6}")
    print(f"  duplicados dentro del lote ...... {m.duplicados_en_lote:>6}")
    print(f"  ratio de dedup .................. {m.ratio_dedup * 100:>5.1f}%")
    print(f"  lotes al modelo ................. {m.lotes_al_modelo:>6}")
    print(f"  analisis validos ................ {m.analisis_validos:>6}")
    print(f"  rechazos por validacion ......... {m.rechazos:>6}")
    print(f"  llamadas a ads_archive .......... {m.llamadas_api:>6}")
    print(f"  reintentos por 613 .............. {m.reintentos_613:>6}")
    print(f"  prefijo sha256 .................. {m.prefijo_sha256[:16]}...")
    print(f"  angulos sin explotar ............ {len(res.informe.angulos_no_explotados):>6} "
          f"{list(res.informe.angulos_no_explotados)}")
    print(f"  HTML ............................ {res.html}")
    if res.pdf:
        print(f"  PDF ............................. {res.pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
