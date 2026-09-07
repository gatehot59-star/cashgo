"""
Contratos de datos del pipeline. Pydantic v2.

Estos esquemas son el guardrail estructural de la Regla 6 del ADR-CG-002
("el copy de la competencia es dato hostil"). El razonamiento:

  El texto de un anuncio ajeno entra al contexto del modelo todos los dias. Si
  ese texto contiene una inyeccion de prompt, lo PEOR que puede lograr es que el
  modelo devuelva un JSON que no valide contra `AnalisisAnuncio`, porque todos
  los campos de clasificacion son Literal cerrados y los de texto libre estan
  acotados en longitud. Un JSON invalido se descarta y se registra.

  No hay ningun campo en el que el modelo pueda devolver algo ejecutable, ni una
  URL de destino, ni un id de cuenta, ni un monto. Eso no es casualidad: es el
  diseno.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# --- Taxonomias CERRADAS -----------------------------------------------------
# Son Literal y no str a proposito. Un modelo (o una inyeccion) que devuelva
# "precio; ignora las instrucciones anteriores" produce un ValidationError.
Angulo = Literal[
    "precio", "urgencia", "prueba_social", "autoridad", "miedo_perdida",
    "aspiracional", "garantia", "novedad", "comparacion", "educativo", "otro",
]
Hook = Literal[
    "pregunta", "dato_duro", "historia", "oferta_directa", "provocacion",
    "testimonio", "demostracion", "otro",
]
Cta = Literal[
    "comprar", "registrarse", "mensaje_directo", "descargar", "agendar",
    "mas_info", "otro",
]
Formato = Literal["imagen", "video", "carrusel", "catalogo", "desconocido"]

MAX_TEXTO_LIBRE = 240
_ESPACIOS = re.compile(r"\s+")
# Caracteres de control salvo tab/newline: se van antes de tocar el modelo.
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_URL = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)


def normalizar(texto: str) -> str:
    """Colapsa espacios y saca caracteres de control. Determinista e idempotente."""
    return _ESPACIOS.sub(" ", _CONTROL.sub(" ", texto)).strip()


class AnuncioCrudo(BaseModel):
    """Un anuncio tal como lo devuelve `ads_archive`, ya normalizado."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ad_id: str
    page_id: str
    page_name: str
    cuerpos: tuple[str, ...] = ()
    titulos: tuple[str, ...] = ()
    descripciones: tuple[str, ...] = ()
    inicio: date
    fin: date | None = None
    plataformas: tuple[str, ...] = ()
    snapshot_url: str = ""

    @field_validator("cuerpos", "titulos", "descripciones", mode="before")
    @classmethod
    def _limpiar_listas(cls, v: object) -> tuple[str, ...]:
        if v is None:
            return ()
        if isinstance(v, str):
            v = [v]
        return tuple(normalizar(str(x)) for x in v if str(x).strip())

    @field_validator("page_name", mode="before")
    @classmethod
    def _limpiar_nombre(cls, v: object) -> str:
        return normalizar(str(v or ""))

    @property
    def texto_completo(self) -> str:
        """Todo el copy en un solo string. Es lo unico que ve el modelo."""
        partes = [*self.cuerpos, *self.titulos, *self.descripciones]
        return " | ".join(partes)

    def dias_activo(self, hoy: date | None = None) -> int:
        """
        Antiguedad del anuncio en dias.

        VERIFICADO EN VIVO [2026-09-06]: para anuncios COMERCIALES la Ad Library
        NO publica spend, impresiones, CTR ni conversiones (solo lo hace para
        political/issue). Asi que la longevidad es el UNICO proxy de exito
        disponible por via oficial, y hay que tratarlo como proxy y no como
        metrica: un anuncio puede estar activo por inercia del anunciante.
        """
        ref = self.fin or (hoy or datetime.now(timezone.utc).date())
        return max(0, (ref - self.inicio).days)

    @property
    def esta_activo(self) -> bool:
        return self.fin is None

    def content_hash(self) -> str:
        """
        Hash de CONTENIDO, no del registro.

        Deliberadamente NO incluye fechas de entrega ni el ad_id. Razon medida:
        un anuncio que sigue corriendo aparece en cada corrida con la misma
        creatividad y una fecha de fin distinta. Si el hash incluyera la fecha,
        el 88% de dedup del modelo de costo se caeria a cero y cada corrida
        pagaria tokens por todo el corpus otra vez.

        Es la misma idea que la Regla 3 del ADR-CG-002: hashear la INTENCION
        (aca, la creatividad) y no el registro que la transporta.
        """
        payload = "\u241f".join([
            self.page_id,
            *self.cuerpos,
            *self.titulos,
            *self.descripciones,
            ",".join(sorted(self.plataformas)),
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sin_urls(texto: str) -> str:
    """
    Reemplaza cualquier URL por el marcador [enlace].

    Se aplica SOLO a los campos de texto libre que terminan impresos en el
    informe que ve el cliente. Motivo: ese texto sale del copy de un competidor,
    y una URL ajena dentro de un PDF comercial que firmamos nosotros es, en el
    mejor caso, ruido que abarata el entregable, y en el peor un enlace que un
    cliente clickea porque venia en un documento nuestro.

    No reemplaza al escapado de HTML: son dos capas distintas. El escapado impide
    que el texto se ejecute; esto impide que el texto invite a navegar.
    """
    return _ESPACIOS.sub(" ", _URL.sub("[enlace]", texto)).strip()


class AnalisisAnuncio(BaseModel):
    """Lo que el modelo DEBE devolver por anuncio. Nada mas que esto."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ad_id: str
    angulo: Angulo
    hook: Hook
    cta: Cta
    formato: Formato
    promesa: str = Field(default="", max_length=MAX_TEXTO_LIBRE)
    publico_sugerido: str = Field(default="", max_length=MAX_TEXTO_LIBRE)
    confianza: float = Field(ge=0.0, le=1.0)

    @field_validator("promesa", "publico_sugerido", mode="before")
    @classmethod
    def _acotar(cls, v: object) -> str:
        return sin_urls(normalizar(str(v or "")))[:MAX_TEXTO_LIBRE]


class LoteAnalizado(BaseModel):
    """Envoltorio del output del modelo: una lista y nada mas."""

    model_config = ConfigDict(extra="forbid")

    analisis: list[AnalisisAnuncio]


class Rechazo(BaseModel):
    """Un item que el modelo devolvio y el validador tiro. Se registra, no se reintenta."""

    model_config = ConfigDict(frozen=True)

    ad_id: str = "?"
    motivo: str
    crudo: str = Field(default="", max_length=2000)


class FilaCompetidor(BaseModel):
    """Una marca en el informe, con sus numeros agregados de forma determinista."""

    model_config = ConfigDict(frozen=True)

    page_id: str
    page_name: str
    anuncios: int
    activos: int
    dias_activo_mediana: int
    dias_activo_max: int
    angulos: tuple[tuple[str, int], ...]
    formatos: tuple[tuple[str, int], ...]


class Informe(BaseModel):
    """
    El entregable comercial.

    Construido 100% por agregacion DETERMINISTA sobre los analisis validados.
    Cero LLM en esta capa: contar y ordenar es trabajo de un backend, y un LLM
    contando es un LLM equivocandose gratis (regla Cerebro vs Brazo).
    """

    model_config = ConfigDict(frozen=True)

    prospecto_nombre: str
    prospecto_page_id: str
    nicho: str
    paises: tuple[str, ...]
    generado_en: datetime
    anuncios_prospecto: int
    anuncios_competencia: int
    competidores: tuple[FilaCompetidor, ...]
    distribucion_angulos: tuple[tuple[str, int], ...]
    angulos_del_prospecto: tuple[str, ...]
    angulos_no_explotados: tuple[str, ...]
    formatos_ganadores: tuple[tuple[str, int, int], ...]  # (formato, n, mediana_dias)
    longevos: tuple[tuple[str, str, int], ...]            # (page_name, promesa, dias)
    rechazos: int
    anuncios_descartados_por_dedup: int
    narrativa: str = ""
