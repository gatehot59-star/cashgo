"""
Persistencia local en SQLite.

Postgres es la fuente de verdad en produccion; para la Fase 0 SQLite alcanza y
sobra, y tiene una ventaja concreta: el entregable es un archivo que se puede
copiar y auditar sin levantar un servicio. La forma de las tablas es la misma,
asi que la migracion es un cambio de driver.

`corridas` es APPEND-ONLY: nunca UPDATE, nunca DELETE. Es el embrion del
audit_log del ADR-CG-002, aplicado a un subsistema que todavia no toca dinero.
Empezar el habito antes de que sea critico es mas barato que agregarlo despues.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .schemas import AnalisisAnuncio, AnuncioCrudo

ESQUEMA = """
CREATE TABLE IF NOT EXISTS anuncios (
    content_hash  TEXT PRIMARY KEY,
    ad_id         TEXT NOT NULL,
    page_id       TEXT NOT NULL,
    page_name     TEXT NOT NULL,
    texto         TEXT NOT NULL,
    inicio        TEXT NOT NULL,
    fin           TEXT,
    plataformas   TEXT NOT NULL,
    snapshot_url  TEXT NOT NULL,
    visto_primero TEXT NOT NULL,
    visto_ultimo  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_anuncios_page ON anuncios(page_id);

CREATE TABLE IF NOT EXISTS analisis (
    content_hash TEXT PRIMARY KEY REFERENCES anuncios(content_hash),
    ad_id        TEXT NOT NULL,
    angulo       TEXT NOT NULL,
    hook         TEXT NOT NULL,
    cta          TEXT NOT NULL,
    formato      TEXT NOT NULL,
    promesa      TEXT NOT NULL,
    publico      TEXT NOT NULL,
    confianza    REAL NOT NULL,
    modelo       TEXT NOT NULL,
    creado_en    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS corridas (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    creado_en TEXT NOT NULL,
    evento    TEXT NOT NULL,
    payload   TEXT NOT NULL
);
"""


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    """Wrapper fino sobre SQLite. Idempotente por content_hash."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(self.path)
        self._con.row_factory = sqlite3.Row
        self._con.executescript(ESQUEMA)
        self._con.commit()

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- anuncios -----------------------------------------------------------
    def hashes_conocidos(self, page_ids: Iterable[str] | None = None) -> set[str]:
        if page_ids is None:
            filas = self._con.execute("SELECT content_hash FROM anuncios").fetchall()
        else:
            ids = list(page_ids)
            if not ids:
                return set()
            marcas = ",".join("?" * len(ids))
            filas = self._con.execute(
                f"SELECT content_hash FROM anuncios WHERE page_id IN ({marcas})", ids
            ).fetchall()
        return {f["content_hash"] for f in filas}

    def guardar_anuncios(self, anuncios: Iterable[AnuncioCrudo]) -> int:
        """
        Upsert por content_hash. Devuelve cuantas filas NUEVAS entraron.

        Si el hash ya existe solo se actualiza `visto_ultimo` y `fin`: eso es lo
        que permite despues distinguir "anuncio que sigue vivo" de "anuncio que
        no volvimos a ver", sin re-pagar tokens por el.
        """
        ahora = _ahora()
        nuevas = 0
        with closing(self._con.cursor()) as cur:
            for ad in anuncios:
                h = ad.content_hash()
                cur.execute("SELECT 1 FROM anuncios WHERE content_hash = ?", (h,))
                if cur.fetchone():
                    cur.execute(
                        "UPDATE anuncios SET visto_ultimo = ?, fin = ? WHERE content_hash = ?",
                        (ahora, ad.fin.isoformat() if ad.fin else None, h),
                    )
                    continue
                cur.execute(
                    """INSERT INTO anuncios
                       (content_hash, ad_id, page_id, page_name, texto, inicio, fin,
                        plataformas, snapshot_url, visto_primero, visto_ultimo)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        h, ad.ad_id, ad.page_id, ad.page_name, ad.texto_completo,
                        ad.inicio.isoformat(), ad.fin.isoformat() if ad.fin else None,
                        json.dumps(sorted(ad.plataformas)), ad.snapshot_url, ahora, ahora,
                    ),
                )
                nuevas += 1
        self._con.commit()
        return nuevas

    # -- analisis -----------------------------------------------------------
    def guardar_analisis(
        self,
        pares: Iterable[tuple[str, AnalisisAnuncio]],
        modelo: str,
    ) -> int:
        ahora = _ahora()
        n = 0
        with closing(self._con.cursor()) as cur:
            for content_hash, an in pares:
                cur.execute(
                    """INSERT OR REPLACE INTO analisis
                       (content_hash, ad_id, angulo, hook, cta, formato, promesa,
                        publico, confianza, modelo, creado_en)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        content_hash, an.ad_id, an.angulo, an.hook, an.cta, an.formato,
                        an.promesa, an.publico_sugerido, an.confianza, modelo, ahora,
                    ),
                )
                n += 1
        self._con.commit()
        return n

    def analisis_de(self, page_ids: Iterable[str]) -> dict[str, dict[str, object]]:
        """Analisis persistidos de las paginas dadas, indexados por content_hash."""
        ids = list(page_ids)
        if not ids:
            return {}
        marcas = ",".join("?" * len(ids))
        filas = self._con.execute(
            f"""SELECT a.*, n.page_id, n.page_name, n.inicio, n.fin, n.snapshot_url
                FROM analisis a JOIN anuncios n USING (content_hash)
                WHERE n.page_id IN ({marcas})""",
            ids,
        ).fetchall()
        return {f["content_hash"]: dict(f) for f in filas}

    # -- audit log ----------------------------------------------------------
    def log(self, evento: str, payload: dict[str, object]) -> None:
        self._con.execute(
            "INSERT INTO corridas (creado_en, evento, payload) VALUES (?,?,?)",
            (_ahora(), evento, json.dumps(payload, ensure_ascii=False, default=str)),
        )
        self._con.commit()

    def eventos(self) -> list[dict[str, object]]:
        return [dict(f) for f in self._con.execute(
            "SELECT * FROM corridas ORDER BY id"
        ).fetchall()]
