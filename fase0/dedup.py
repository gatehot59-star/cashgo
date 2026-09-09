"""
Deduplicacion determinista, ANTES del modelo.

Es la palanca de costo mas grande de todo el pipeline y no tiene una sola linea
de IA: es un SELECT. Medido en scripts/modelo_costo_arq3.py: de 60.000 anuncios
vistos por corrida, 52.800 (el 88%) no vuelven a pagar tokens.

El blueprint externo estimaba "70-90%". El numero medido con churn creativo del
12% cae justo en el borde superior de esa estimacion.
"""
from __future__ import annotations

from dataclasses import dataclass

from .schemas import AnuncioCrudo


@dataclass(frozen=True)
class Particion:
    """Resultado de partir un corpus contra lo ya visto."""

    nuevos: tuple[AnuncioCrudo, ...]
    ya_vistos: tuple[AnuncioCrudo, ...]
    duplicados_en_lote: int

    @property
    def total(self) -> int:
        return len(self.nuevos) + len(self.ya_vistos) + self.duplicados_en_lote

    @property
    def ratio_ahorro(self) -> float:
        """Fraccion del corpus que NO paga tokens. 0.0 si el corpus esta vacio."""
        if self.total == 0:
            return 0.0
        return (len(self.ya_vistos) + self.duplicados_en_lote) / self.total


def particionar(
    anuncios: list[AnuncioCrudo],
    hashes_conocidos: set[str],
) -> Particion:
    """
    Parte el corpus en (nuevos, ya vistos) por content_hash.

    Tambien colapsa duplicados DENTRO del mismo lote: dos anunciantes pueden
    correr creatividades identicas (agencias que reciclan), y la misma marca
    puede tener el mismo copy en varios ad_id.
    """
    nuevos: list[AnuncioCrudo] = []
    ya_vistos: list[AnuncioCrudo] = []
    en_este_lote: set[str] = set()
    duplicados = 0

    for ad in anuncios:
        h = ad.content_hash()
        if h in hashes_conocidos:
            ya_vistos.append(ad)
        elif h in en_este_lote:
            duplicados += 1
        else:
            en_este_lote.add(h)
            nuevos.append(ad)

    return Particion(
        nuevos=tuple(nuevos),
        ya_vistos=tuple(ya_vistos),
        duplicados_en_lote=duplicados,
    )
