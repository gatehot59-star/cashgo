"""
Cliente de `ads_archive` (Ad Library API oficial de Meta).

Por que la via oficial y no scraping, medido el 2026-09-06:

  - Es LEGAL sin discusion: no hay ToS que interpretar ni fallo judicial que
    citar. La via de scraping tiene el precedente Meta v. Bright Data a favor,
    pero tiene en contra el fingerprint de TLS/HTTP2, clases CSS ofuscadas que
    cambian en cada deploy, letras senuelo dentro de "Sponsored" y CAPTCHAs.
    O sea: no te demandan, se te rompe el martes.
  - Devuelve ESQUEMA. El scraping devuelve HTML que hay que parsear de nuevo
    cada vez que Meta hace un deploy.
  - Cuesta USD 0 y no necesita proxies residenciales (USD ~75/mes) ni un pool
    de contenedores de navegador (USD ~60/mes).

Su precio es GEOGRAFIA, no dinero: solo devuelve anuncios comerciales para
UE/UK (obligacion del DSA). Ese limite esta codificado como guard, no como
comentario.

Transporte inyectable: el cliente no importa `requests` ni `urllib` directo.
Recibe una funcion `transport(url, params) -> dict`. Eso permite testearlo
contra fixtures sin red, y es lo que hace que los tests puedan dar ROJO de
verdad en vez de saltearse.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from . import config
from .schemas import AnuncioCrudo

Transport = Callable[[str, dict[str, Any]], dict[str, Any]]

GRAPH_URL = "https://graph.facebook.com/v26.0/ads_archive"


class AdsArchiveError(RuntimeError):
    """Error de dominio del cliente."""


class AlcanceComercialError(AdsArchiveError):
    """
    Se pidieron paises para los que la API NO devuelve anuncios comerciales.

    No es un error de red ni de permisos: es pedirle a la API un dato que no
    tiene. Falla temprano y explicito en vez de devolver una lista vacia que
    despues alguien interpreta como "el competidor no anuncia".
    """


class RateLimitError(AdsArchiveError):
    """Error 613 de Meta: user request limit reached."""


class PresupuestoDeLlamadasAgotado(AdsArchiveError):
    """Se alcanzo el techo propio de llamadas/hora antes que el de Meta."""


@dataclass
class PresupuestoLlamadas:
    """
    Contador de llamadas con ventana deslizante de una hora.

    Existe porque el limite de Meta es DINAMICO y NO PUBLICADO: no se puede
    confiar en un numero fijo del lado de ellos, asi que el techo propio va
    10% por debajo del observado y se frena solo.
    """

    techo_por_hora: int = config.CALLS_POR_HORA_TECHO
    _marcas: list[float] = field(default_factory=list)
    reloj: Callable[[], float] = time.monotonic

    def registrar(self) -> None:
        ahora = self.reloj()
        self._marcas = [t for t in self._marcas if ahora - t < 3600.0]
        if len(self._marcas) >= self.techo_por_hora:
            raise PresupuestoDeLlamadasAgotado(
                f"techo propio de {self.techo_por_hora} llamadas/hora alcanzado; "
                "la corrida se reanuda en la proxima ventana"
            )
        self._marcas.append(ahora)

    @property
    def usadas(self) -> int:
        ahora = self.reloj()
        return len([t for t in self._marcas if ahora - t < 3600.0])


def _parse_fecha(valor: object) -> date | None:
    if not valor:
        return None
    texto = str(valor)
    # ads_archive devuelve ISO con offset ("2026-03-04T00:00:00+0000") o solo fecha.
    try:
        return date.fromisoformat(texto[:10])
    except ValueError:
        try:
            return datetime.fromisoformat(texto).date()
        except ValueError:
            return None


def lotes(items: list[str], tamano: int) -> Iterator[list[str]]:
    """Parte una lista en lotes de `tamano`. Ultimo lote puede ser mas chico."""
    if tamano <= 0:
        raise ValueError("tamano debe ser > 0")
    for i in range(0, len(items), tamano):
        yield items[i:i + tamano]


class AdsArchiveClient:
    """Cliente con paginacion por cursor, batch de page_ids y backoff en 613."""

    def __init__(
        self,
        token: str,
        transport: Transport,
        *,
        paises: tuple[str, ...],
        presupuesto: PresupuestoLlamadas | None = None,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        fuera = sorted(set(p.upper() for p in paises) - config.DSA_COMMERCIAL_COUNTRIES)
        if fuera:
            raise AlcanceComercialError(
                f"paises sin cobertura comercial en ads_archive: {fuera}. "
                "Por el DSA la API solo publica anuncios comerciales para UE/UK; "
                "para el resto devuelve unicamente political/issue ads."
            )
        if not paises:
            raise AlcanceComercialError("hay que pedir al menos un pais")
        self._token = token
        self._transport = transport
        self._paises = tuple(p.upper() for p in paises)
        self._presupuesto = presupuesto or PresupuestoLlamadas()
        self._dormir = dormir
        self.llamadas_hechas = 0
        self.reintentos_613 = 0

    # -- interno ------------------------------------------------------------
    def _llamar(self, params: dict[str, Any]) -> dict[str, Any]:
        intento = 0
        while True:
            self._presupuesto.registrar()
            self.llamadas_hechas += 1
            try:
                return self._transport(GRAPH_URL, params)
            except RateLimitError:
                intento += 1
                if intento > config.BACKOFF_MAX_INTENTOS:
                    # DEFECTO PROPIO CAZADO POR EL TEST (2026-09-06): antes de esta
                    # correccion `reintentos_613` se incrementaba ANTES de este
                    # chequeo, asi que contaba tambien el 613 final que hace
                    # abandonar. Reportaba 6 reintentos habiendo dormido 5 veces:
                    # una metrica que no coincidia con su propio fenomeno. Ahora
                    # el contador solo cuenta reintentos EFECTIVAMENTE hechos, y
                    # por construccion es igual a la cantidad de esperas.
                    raise
                self.reintentos_613 += 1
                espera = min(
                    config.BACKOFF_BASE_SEG * (2 ** (intento - 1)),
                    config.BACKOFF_MAX_SEG,
                )
                self._dormir(espera)

    def _params_base(self, page_ids: list[str], desde: date | None) -> dict[str, Any]:
        params: dict[str, Any] = {
            "access_token": self._token,
            "ad_reached_countries": list(self._paises),
            "ad_type": "ALL",
            "ad_active_status": "ALL",
            "search_page_ids": page_ids,
            "fields": ",".join(config.CAMPOS_ADS_ARCHIVE),
            "limit": config.LIMIT_POR_PAGINA,
        }
        if desde:
            params["ad_delivery_date_min"] = desde.isoformat()
        return params

    # -- publico ------------------------------------------------------------
    def anuncios_de(
        self,
        page_ids: list[str],
        *,
        desde: date | None = None,
        max_paginas_por_lote: int = 40,
    ) -> Iterator[AnuncioCrudo]:
        """
        Itera los anuncios de las paginas dadas.

        Batchea hasta MAX_PAGE_IDS_POR_LLAMADA page_ids por request (la palanca
        de eficiencia mas grande: 10 marcas por llamada en vez de 1) y pagina por
        cursor `after` hasta que no haya mas.

        `max_paginas_por_lote` es un tope de seguridad: sin el, un cursor que
        Meta devuelve mal apuntado es un bucle infinito consumiendo rate limit.
        """
        vistos: set[str] = set()
        for lote in lotes([str(p) for p in page_ids], config.MAX_PAGE_IDS_POR_LLAMADA):
            params = self._params_base(lote, desde)
            paginas = 0
            while True:
                payload = self._llamar(params)
                for fila in payload.get("data", []):
                    ad = self._a_anuncio(fila)
                    if ad is None or ad.ad_id in vistos:
                        continue
                    vistos.add(ad.ad_id)
                    yield ad
                paginas += 1
                cursor = (payload.get("paging") or {}).get("cursors", {}).get("after")
                tiene_siguiente = bool((payload.get("paging") or {}).get("next"))
                if not cursor or not tiene_siguiente or paginas >= max_paginas_por_lote:
                    break
                params = {**params, "after": cursor}

    @staticmethod
    def _a_anuncio(fila: dict[str, Any]) -> AnuncioCrudo | None:
        """
        Convierte una fila cruda en AnuncioCrudo. Devuelve None si no se puede.

        Sin fecha de inicio no hay senal de longevidad, y la longevidad es el
        unico proxy de exito que la Ad Library da para anuncios comerciales.
        Un anuncio sin inicio no aporta nada al informe: se descarta aca en vez
        de contaminar la agregacion con un cero.
        """
        inicio = _parse_fecha(fila.get("ad_delivery_start_time"))
        if inicio is None:
            return None
        ad_id = str(fila.get("id") or "").strip()
        page_id = str(fila.get("page_id") or "").strip()
        if not ad_id or not page_id:
            return None
        return AnuncioCrudo(
            ad_id=ad_id,
            page_id=page_id,
            page_name=fila.get("page_name") or "",
            cuerpos=fila.get("ad_creative_bodies") or (),
            titulos=fila.get("ad_creative_link_titles") or (),
            descripciones=fila.get("ad_creative_link_descriptions") or (),
            inicio=inicio,
            fin=_parse_fecha(fila.get("ad_delivery_stop_time")),
            plataformas=tuple(fila.get("publisher_platforms") or ()),
            snapshot_url=str(fila.get("ad_snapshot_url") or ""),
        )


def transporte_http(timeout: float = 30.0) -> Transport:
    """
    Transporte real contra Graph API. Solo stdlib, cero dependencias nuevas.

    NO SE EJECUTO CONTRA LA API REAL (declarado): el sandbox donde se escribio
    este pipeline no tiene red. La forma del request sale de la documentacion
    oficial y el mapeo del error 613 tambien, pero la primera corrida contra
    Meta es una verificacion PENDIENTE y va declarada como tal en el PR.
    """
    import json
    import urllib.error
    import urllib.parse
    import urllib.request

    def _t(url: str, params: dict[str, Any]) -> dict[str, Any]:
        plano: dict[str, str] = {}
        for k, v in params.items():
            plano[k] = json.dumps(v) if isinstance(v, (list, tuple)) else str(v)
        query = urllib.parse.urlencode(plano)
        try:
            with urllib.request.urlopen(f"{url}?{query}", timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "replace")
            try:
                err = json.loads(cuerpo).get("error", {})
            except json.JSONDecodeError:
                err = {}
            if err.get("code") == 613 or err.get("error_subcode") == 1487225:
                raise RateLimitError(f"613: {err.get('message', cuerpo)}") from e
            raise AdsArchiveError(f"HTTP {e.code}: {cuerpo[:500]}") from e

    return _t
