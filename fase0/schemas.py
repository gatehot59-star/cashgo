"""
Contratos de datos del pipeline. Pydantic v2.

Estos esquemas son el guardrail estructural de la Regla 6 del ADR-CG-002
("el copy de la competencia es dato hostil"). El razonamiento:

  El texto de un anuncio ajeno entra al contexto del modelo todos los dias. Si
  ese texto contiene una inyeccion de prompt, lo PEOR que puede lograr es que el
  modelo devuelva un JSON que no valide contra `AnalisisAnuncio`, porque todos
  los campos de clasificacion son Literal cerrados. Un JSON invalido se descarta
  y se registra.

  PRECISION AGREGADA POR B5 (auditoria externa, 2026-09-07): el docstring decia
  antes que los campos de texto libre estaban "acotados en longitud", presentando
  como guard estructural lo que en realidad es TRUNCAMIENTO. Son cosas distintas:
  un guard rechaza, el truncamiento degrada en silencio. El truncamiento es la
  conducta correcta aca (una promesa larga no debe invalidar los otros 39 analisis
  del lote) y ahora esta declarado como tal, con un test que lo fija.

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
# B8 (hallazgo del auditor externo, 2026-09-07): la version anterior era
# r"\b(?:https?://|www\.)\S+" y dejaba pasar `bit.ly/x`, `marca.com/oferta` y
# cualquier dominio sin protocolo ni `www`. El docstring prometia "URL de
# terceros" sin calificar, o sea que la promesa era mas amplia que el guard.
# Esta version cubre tambien dominio+TLD desnudo y los ofuscados `marca[.]com`.
# NO pretende ser exhaustiva: no hay regex que lo sea. El alcance real esta
# declarado en el docstring de sin_urls().
_TLD = (
    r"com|net|org|io|co|ai|app|shop|store|es|de|fr|it|nl|uk|eu|pt|be|se|dk|pl|ie"
    r"|gl|ly|me|to|cc|tv|xyz|online|site|link|biz|info"
)
_URL = re.compile(
    r"(?:https?://\S+"                                   # con protocolo
    r"|www\.\S+"                                         # con www
    r"|\b[\w-]+(?:\s*\[\s*\.\s*\]\s*|\.)(?:" + _TLD + r")\b(?:/\S*)?)",
    re.IGNORECASE,
)

# --- B3 (hallazgo del auditor externo, 2026-09-07) ---
# Los delimitadores con los que `cognitive.formatear_anuncio` envuelve cada
# anuncio son literales fijos. Un copy hostil que los contenga puede CERRAR su
# bloque y ABRIR otro con el ad_id de un competidor legitimo y texto inventado.
# El esquema cerrado NO lo frena, porque ese ad_id si estaba en la entrada y la
# clasificacion es valida; la verificacion de cobertura tampoco, por la misma
# razon. Es contaminacion cruzada DENTRO del lote, y no estaba en el modelo de
# amenazas: el vector declarado cubria "que el modelo devuelva algo invalido",
# no "que clasifique mal a un tercero con datos formalmente validos".
#
# Se neutraliza en la frontera de ingesta, no en la de formateo, para que el
# texto guardado en la base ya este limpio y ningun consumidor futuro herede el
# problema. La secuencia `<<<` es la unica que hay que romper.
_SECUENCIA_DELIMITADOR = re.compile(r"<{3,}|>{3,}")


def normalizar(texto: str) -> str:
    """
    Colapsa espacios, saca caracteres de control y neutraliza la secuencia con la
    que se delimitan los bloques enviados al modelo. Determinista e idempotente.

    La neutralizacion de `<<<` y `>>>` cierra el vector B3 (contaminacion cruzada
    intra-lote): si la secuencia no puede aparecer en NINGUN campo que se
    interpole en el bloque, ningun anuncio puede fabricar un bloque atribuido a
    otro anunciante. La palabra "NINGUN" es de H-01: la version anterior de este
    docstring decia "en el copy", y el copy era uno de tres.
    """
    limpio = _CONTROL.sub(" ", texto)
    limpio = _SECUENCIA_DELIMITADOR.sub(lambda m: m.group(0)[0] * 2, limpio)
    return _ESPACIOS.sub(" ", limpio).strip()


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

    @field_validator("cuerpos", "titulos", "descripciones", "plataformas",
                     mode="before")
    @classmethod
    def _limpiar_listas(cls, v: object) -> tuple[str, ...]:
        if v is None:
            return ()
        if isinstance(v, str):
            v = [v]
        return tuple(normalizar(str(x)) for x in v if str(x).strip())

    # H-01 (auditoria independiente de Tao, 2026-09-07): la correccion B3 neutralizo
    # `<<<` en el COPY y declaro cerrado el vector. La premisa era verdadera y la
    # conclusion no se seguia: `cognitive.formatear_anuncio` interpola TRES valores
    # en el bloque que va al modelo (`ad_id`, `plataformas` y el copy), y solo uno
    # tenia validador. O sea que la promesa del comentario era mas amplia que su
    # alcance, que es el patron 2 de este registro con otra ropa.
    #
    # MEDIDO SOBRE EL ARBOL REAL, y el efecto es peor que el reportado: en un lote
    # de dos anuncios, el payload en `ad_id` produjo TRES bloques, y el fabricado
    # nombraba el `ad_id` de un competidor legitimo del mismo lote. Como ese ad_id
    # SI estaba en la entrada, `_verificar_cobertura` no podia frenarlo, y como la
    # regla de B2 es "gana la primera ocurrencia" y el bloque fabricado va antes,
    # **la promesa que quedaba impresa en el PDF la escribia el atacante**:
    # 'producto defectuoso, no compren nunca' atribuido a la victima. El guard de
    # B2 jugaba a favor del atacante.
    #
    # `page_id` entra tambien porque alimenta el `content_hash` del dedup. La
    # neutralizacion es no-op sobre identificadores normales y eso esta medido con
    # un test de no regresion del hash: si se moviera, la proxima corrida re-pagaria
    # tokens por todo el corpus.
    @field_validator("page_name", "ad_id", "page_id", mode="before")
    @classmethod
    def _limpiar_texto(cls, v: object) -> str:
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

        TAMPOCO INCLUYE `plataformas` (B6, hallazgo del auditor externo 2026-09-07).
        La version anterior si las incluia, y eso reintroducia el mismo defecto que
        la fecha en menor magnitud: una creatividad que arranca solo en Facebook y
        despues se extiende a Instagram cambiaba de hash y volvia a pagar tokens,
        siendo el mismo hecho de mercado.
        Decision declarada: la identidad de una creatividad es `page_id` + copy.
        Las plataformas siguen disponibles en el registro crudo para el informe.
        """
        payload = "\u241f".join([
            self.page_id,
            *self.cuerpos,
            *self.titulos,
            *self.descripciones,
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sin_urls(texto: str) -> str:
    """
    Reemplaza cualquier URL por el marcador [enlace].

    Se aplica a los campos de texto libre que terminan impresos en el informe que
    ve el cliente: `promesa`, `publico_sugerido` y la `narrativa` (esta ultima por
    H-03, que la encontro afuera del filtro). Motivo: ese texto sale del copy de un
    competidor, y una URL ajena dentro de un PDF comercial que firmamos nosotros
    es, en el mejor caso, ruido que abarata el entregable, y en el peor un enlace
    que un cliente clickea porque venia en un documento nuestro.

    No reemplaza al escapado de HTML: son dos capas distintas. El escapado impide
    que el texto se ejecute; esto impide que el texto invite a navegar.

    ALCANCE DECLARADO (B8, hallazgo del auditor externo 2026-09-07): cubre URLs con
    protocolo, con `www`, dominio+TLD desnudo de una lista cerrada de TLDs, y la
    ofuscacion `marca[.]com`. NO es exhaustivo y no puede serlo: un TLD fuera de la
    lista, un dominio escrito en palabras o una IP desnuda pasan. El control que si
    es completo es el escapado de HTML del informe; esta funcion es cosmetica del
    entregable, no un control de seguridad, y el modelo de amenazas la declara asi.
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
    # B5 (hallazgo del auditor externo, 2026-09-07): estos dos campos tenian
    # `max_length=MAX_TEXTO_LIBRE`, y ese constraint era INALCANZABLE: el validador
    # de abajo corre en modo "before" y trunca a 240 antes de que Pydantic evalue la
    # longitud. Nunca podia disparar. Es la tercera aparicion del defecto 10 (guard
    # con rama negativa inalcanzable), y ademas el docstring del modulo vendia
    # "acotados en longitud" como guard estructural cuando era degradacion silenciosa.
    #
    # Decision declarada, no un parche: la conducta correcta ES truncar y no
    # rechazar, porque una promesa larga no debe invalidar los otros 39 analisis
    # del lote. Asi que se retira el constraint muerto y el truncamiento queda
    # documentado como conducta, con un test que lo fija.
    promesa: str = ""
    publico_sugerido: str = ""
    confianza: float = Field(ge=0.0, le=1.0)

    @field_validator("promesa", "publico_sugerido", mode="before")
    @classmethod
    def _acotar(cls, v: object) -> str:
        """TRUNCA a MAX_TEXTO_LIBRE. No rechaza. Ver el comentario de arriba."""
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
