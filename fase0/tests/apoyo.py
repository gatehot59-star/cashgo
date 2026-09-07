"""Fabricas y dobles de prueba compartidos."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from fase0.adlibrary import RateLimitError, Transport
from fase0.schemas import AnuncioCrudo

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

# Los fixtures son datos de prueba COMO CODIGO: si no estan en disco, se
# generan. Determinista, asi que dos generaciones dan bytes identicos.
from fase0.fixtures.generar import escribir as _escribir_fixtures  # noqa: E402

if not (FIXTURES / "ads_archive_sample.json").exists() or \
        not (FIXTURES / "brief_ejemplo.json").exists():
    _escribir_fixtures()


def anuncio(
    ad_id: str = "a1",
    page_id: str = "p1",
    copy: str = "Oferta del 40% solo por hoy",
    inicio: date = date(2026, 6, 1),
    fin: date | None = None,
    plataformas: tuple[str, ...] = ("facebook",),
) -> AnuncioCrudo:
    return AnuncioCrudo(
        ad_id=ad_id, page_id=page_id, page_name=f"Marca {page_id}",
        cuerpos=(copy,), inicio=inicio, fin=fin, plataformas=plataformas,
    )


def transporte_paginas(paginas: list[dict[str, Any]]) -> Transport:
    """Devuelve las paginas en orden; repite la ultima si le piden mas."""
    estado = {"i": 0}

    def _t(_url: str, _params: dict[str, Any]) -> dict[str, Any]:
        i = min(estado["i"], len(paginas) - 1)
        estado["i"] += 1
        return paginas[i]

    return _t


def transporte_que_falla(veces: int, luego: dict[str, Any]) -> Transport:
    """Lanza RateLimitError `veces` y despues devuelve `luego`."""
    estado = {"n": 0}

    def _t(_url: str, _params: dict[str, Any]) -> dict[str, Any]:
        if estado["n"] < veces:
            estado["n"] += 1
            raise RateLimitError("613: User request limit reached")
        return luego

    return _t


def completion_fija(texto: str):
    """Completion que siempre devuelve el mismo texto crudo."""
    def _c(_m: str, _msgs: list[dict[str, str]], _t: float) -> str:
        return texto
    return _c


def completion_capturadora(texto: str, buzon: list[list[dict[str, str]]]):
    """Como completion_fija, pero guarda los mensajes que recibio."""
    def _c(_m: str, msgs: list[dict[str, str]], _t: float) -> str:
        buzon.append(msgs)
        return texto
    return _c


def json_analisis(*items: dict[str, Any]) -> str:
    return json.dumps({"analisis": list(items)}, ensure_ascii=False)


def item(ad_id: str = "a1", **kw: Any) -> dict[str, Any]:
    base = {
        "ad_id": ad_id, "angulo": "precio", "hook": "oferta_directa",
        "cta": "comprar", "formato": "imagen", "promesa": "40% off",
        "publico_sugerido": "sensibles al precio", "confianza": 0.8,
    }
    base.update(kw)
    return base
