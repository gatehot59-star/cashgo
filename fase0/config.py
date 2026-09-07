"""
Configuracion del pipeline de Fase 0.

Cada constante que sale de una medicion lleva su fuente y su fecha. Las que son
decisiones propias lo dicen. No hay numeros huerfanos en este archivo.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# VERIFICADO EN VIVO [2026-09-06]
# Fuente: https://adlibrary.com/posts/meta-ad-library-api-limitations
# Fuente: https://dev.to/odeeb/building-a-facebook-ad-library-scraper-api-limits-and-the-real-approach-3bad
#
# `ads_archive` con ad_type=ALL solo devuelve anuncios COMERCIALES cuando
# ad_reached_countries apunta a la UE o UK (obligacion del Digital Services Act,
# retencion ~12 meses). Fuera de ese conjunto devuelve solo political/issue ads,
# o sea NADA util para inteligencia competitiva de e-commerce.
#
# Esta allowlist NO es una preferencia de mercado: es el limite de lo que la via
# oficial puede entregar. Pedir 'US' no es un error de configuracion, es pedir
# un dato que la API no tiene.
# ---------------------------------------------------------------------------
DSA_COMMERCIAL_COUNTRIES: frozenset[str] = frozenset({
    # UE-27
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR",
    "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO",
    "SE", "SI", "SK",
    # EEE + UK
    "IS", "LI", "NO", "GB",
})

# VERIFICADO EN VIVO [2026-09-06] - Fuente: doc de la Ad Library API y analisis de limites.
# ~200 llamadas/hora por token, dinamico y NO publicado por Meta. El error a
# esperar es el 613. Usamos 180 como techo propio: 10% de colchon sobre un
# limite que la plataforma puede mover sin avisar.
CALLS_POR_HORA_TECHO = 180

# Hasta 10 search_page_ids por llamada (batch documentado). Es la palanca de
# eficiencia mas grande del cliente: 10 marcas por llamada en vez de 1.
MAX_PAGE_IDS_POR_LLAMADA = 10

# `limit` admite valores altos (1000-2000 segun endpoint y fuente). 500 es
# conservador: menos riesgo de timeout del lado de Meta, y la paginacion por
# cursor cubre el resto.
LIMIT_POR_PAGINA = 500

# Backoff exponencial para el error 613. Los reintentos agresivos convierten un
# bloqueo temporal en uno permanente (Regla 9 del ADR-CG-002).
BACKOFF_BASE_SEG = 4.0
BACKOFF_MAX_SEG = 300.0
BACKOFF_MAX_INTENTOS = 5

# Campos que pedimos. Pedir menos campos es la primera recomendacion de Meta
# para no comerse el rate limit.
#
# LIMITACION PROPIA DECLARADA (10.10, encontrada auditando para la revision 2):
# ninguno de estos campos informa el FORMATO del anuncio. El prompt instruye a
# poner "desconocido" si la entrada no lo dice, asi que en produccion `formato`
# sera "desconocido" casi siempre y la seccion 4 del informe entregable
# ("Formatos que el mercado sostiene") sera inerte. En el --dry-run no se nota
# porque el clasificador de fixture deriva el formato de las plataformas, que es
# justo lo que el prompt prohibe: adivinar.
CAMPOS_ADS_ARCHIVE: tuple[str, ...] = (
    "id",
    "page_id",
    "page_name",
    "ad_creative_bodies",
    "ad_creative_link_titles",
    "ad_creative_link_descriptions",
    "ad_delivery_start_time",
    "ad_delivery_stop_time",
    "publisher_platforms",
    "ad_snapshot_url",
)

# ---------------------------------------------------------------------------
# Capa cognitiva. Modelo pinneado, no alias.
# VERIFICADO EN VIVO [2026-09-06]: `deepseek-chat` y `deepseek-reasoner` fueron
# retirados el 2026-07-24. El id vigente de la familia barata es
# `deepseek-v4-flash`. Fuente: https://api-docs.deepseek.com/updates/
# ---------------------------------------------------------------------------
MODELO_FLASH = "deepseek-v4-flash"
MODELO_PRO = "deepseek-v4-pro"

# Tamano del lote que se le manda al modelo. 40 sale del modelo de costo
# (scripts/modelo_costo_arq3.py): es el punto donde el prefijo estable se
# amortiza sobre suficientes anuncios sin que el output se acerque al techo.
ANUNCIOS_POR_LOTE = 40

# B7 (hallazgo del auditor externo, 2026-09-07): tope explicito de tokens de
# salida. Un lote de ANUNCIOS_POR_LOTE anuncios a ~140 tokens de salida cada uno,
# mas el envoltorio JSON y los nombres de campo, son del orden de 8.000 tokens.
# Si el proveedor aplicara un tope por defecto menor, el JSON llegaria truncado y
# se perderia EL LOTE ENTERO como "no es JSON valido", que es la peor forma de
# fallar: caras y silenciosa. Se pide explicito con holgura de 2x.
MAX_TOKENS_SALIDA = ANUNCIOS_POR_LOTE * 400

# Piso aceptable de tasa de acierto del cache de contexto. El modelo de costo
# supone 0,95; por debajo de este valor el supuesto economico de la seccion 6 del
# informe deja de sostenerse y hay que revisarlo antes de escalar el corpus.
UMBRAL_CACHE_HIT = 0.80

# Temperatura 0 no es "mas preciso", es MENOS VARIABLE, y eso es lo que hace
# que el prefijo estable rinda cache y que dos corridas sean comparables.
TEMPERATURA_ESTRUCTURACION = 0.0


@dataclass(frozen=True)
class Settings:
    """
    Configuracion resuelta desde el entorno.

    REGLA 9 del ADR-CG-002 (aislamiento): la app de Meta que usa este subsistema
    NO puede ser la misma que la del gateway de escritura. Si alguna vez existe
    CASHGO_WRITE_APP_ID y coincide con CASHGO_RESEARCH_APP_ID, `validar()` corta.
    Un bloqueo a nivel de app se llevaria los dos subsistemas.
    """

    token_ads_archive: str = ""
    research_app_id: str = ""
    write_app_id: str = ""          # solo para detectar la colision, no se usa
    deepseek_api_key: str = ""
    db_path: str = "cashgo_fase0.sqlite3"
    salida_dir: str = "salidas"
    paises: tuple[str, ...] = ("ES", "DE", "FR", "IT", "NL", "GB")

    @classmethod
    def from_env(cls) -> "Settings":
        paises_env = os.environ.get("CASHGO_PAISES", "")
        paises = tuple(p.strip().upper() for p in paises_env.split(",") if p.strip())
        return cls(
            token_ads_archive=os.environ.get("CASHGO_ADS_ARCHIVE_TOKEN", ""),
            research_app_id=os.environ.get("CASHGO_RESEARCH_APP_ID", ""),
            write_app_id=os.environ.get("CASHGO_WRITE_APP_ID", ""),
            deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            db_path=os.environ.get("CASHGO_DB_PATH", "cashgo_fase0.sqlite3"),
            salida_dir=os.environ.get("CASHGO_SALIDA_DIR", "salidas"),
            paises=paises or cls.paises,
        )

    def validar(self, *, requiere_red: bool = True) -> list[str]:
        """
        Devuelve la lista de problemas. Lista vacia = configuracion sana.

        No lanza: el llamador decide si aborta o degrada. Tres estados, no dos.
        """
        errs: list[str] = []
        if requiere_red and not self.token_ads_archive:
            errs.append("CASHGO_ADS_ARCHIVE_TOKEN vacio (system user token con scope ads_archive)")
        if requiere_red and not self.deepseek_api_key:
            errs.append("DEEPSEEK_API_KEY vacio")
        fuera = sorted(set(p.upper() for p in self.paises) - DSA_COMMERCIAL_COUNTRIES)
        if fuera:
            errs.append(
                f"paises fuera del alcance comercial del DSA: {fuera}. "
                "ads_archive no devuelve anuncios comerciales para esos codigos."
            )
        if self.write_app_id and self.write_app_id == self.research_app_id:
            errs.append(
                "REGLA 9 VIOLADA: research_app_id == write_app_id. El scraper y el "
                "gateway de escritura no pueden compartir app de Meta."
            )
        return errs
