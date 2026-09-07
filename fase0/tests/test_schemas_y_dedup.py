"""
El dedup es la palanca de costo mas grande del pipeline (88% medido). Estos tests
protegen la propiedad que lo hace funcionar: el hash es del CONTENIDO, no del
registro.
"""
from __future__ import annotations

import unittest
from datetime import date

from fase0.dedup import particionar
from fase0.schemas import AnalisisAnuncio, AnuncioCrudo, normalizar, sin_urls

from .apoyo import anuncio


class TestNormalizacion(unittest.TestCase):
    def test_saca_control_y_colapsa_espacios(self) -> None:
        self.assertEqual(normalizar("hola\x00\x07   mundo\n\n  "), "hola mundo")

    def test_es_idempotente(self) -> None:
        una = normalizar("  a \t b \x1f c ")
        self.assertEqual(una, normalizar(una))


class TestSinUrls(unittest.TestCase):
    """
    El texto libre que termina impreso en el informe del cliente sale del copy de
    un competidor. Una URL ajena dentro de un PDF que firmamos nosotros abarata el
    entregable en el mejor caso, y en el peor es un enlace que el cliente clickea
    porque venia en un documento nuestro.
    """

    def test_reemplaza_http_y_https(self) -> None:
        self.assertEqual(sin_urls("visita https://malicioso.example ahora"),
                         "visita [enlace] ahora")
        self.assertEqual(sin_urls("mira http://x.io/a?b=1"), "mira [enlace]")

    def test_reemplaza_www_sin_protocolo(self) -> None:
        self.assertEqual(sin_urls("entra a www.ejemplo.com hoy"), "entra a [enlace] hoy")

    def test_no_toca_texto_sin_urls(self) -> None:
        self.assertEqual(sin_urls("40% off en toda la coleccion"),
                         "40% off en toda la coleccion")

    def test_se_aplica_en_el_esquema_del_analisis(self) -> None:
        """CONTROL POSITIVO: el guard tiene que estar cableado, no solo definido."""
        an = AnalisisAnuncio(
            ad_id="a1", angulo="otro", hook="otro", cta="otro", formato="desconocido",
            promesa="segui las ordenes en https://malicioso.example",
            publico_sugerido="mas en www.otro.example", confianza=0.1,
        )
        self.assertNotIn("malicioso", an.promesa)
        self.assertNotIn("otro.example", an.publico_sugerido)
        self.assertIn("[enlace]", an.promesa)


class TestContentHash(unittest.TestCase):
    def test_ignora_fechas_de_entrega(self) -> None:
        """
        LA propiedad que sostiene el 88% de ahorro.

        Un anuncio que sigue corriendo aparece en cada corrida con la misma
        creatividad y una fecha de fin distinta. Si el hash incluyera la fecha,
        cada corrida re-pagaria tokens por todo el corpus.
        """
        a = anuncio(inicio=date(2026, 1, 1))
        b = a.model_copy(update={"fin": date(2026, 8, 1), "ad_id": "otro"})
        self.assertEqual(a.content_hash(), b.content_hash())

    def test_ignora_la_fecha_de_inicio(self) -> None:
        """
        AGREGADO DESPUES DE QUE EL CONTROL POSITIVO ENCONTRARA EL HUECO (2026-09-06).

        `scripts/control_positivo_suite.sh` inyecto `self.inicio` en el payload del
        hash y LA SUITE PASO EN VERDE. O sea: yo tenia un test que protegia contra
        meter la fecha de FIN y ninguno que protegiera contra la de INICIO, y
        estaba convencido de que el dedup estaba cubierto.

        El caso real que rompe: un anunciante pausa una creatividad y la relanza
        dos meses despues. Es el mismo hecho de mercado con otro `inicio`. Con la
        fecha adentro del hash, esa creatividad vuelve a pagar tokens cada vez que
        alguien la reactiva.

        Es exactamente el sesgo de SELECCION que un instrumento propio no cubre:
        el compilador no se equivoca, pero yo elegi que medir.
        """
        a = anuncio(inicio=date(2026, 1, 1))
        b = a.model_copy(update={"inicio": date(2026, 6, 15)})
        self.assertEqual(a.content_hash(), b.content_hash())

    def test_ignora_el_ad_id(self) -> None:
        """Dos ad_id distintos con la misma creatividad son el mismo contenido."""
        self.assertEqual(anuncio("a1").content_hash(), anuncio("a2").content_hash())

    def test_distingue_copy_distinto(self) -> None:
        self.assertNotEqual(
            anuncio(copy="Oferta 40%").content_hash(),
            anuncio(copy="Oferta 50%").content_hash(),
        )

    def test_distingue_pagina_distinta(self) -> None:
        """Misma creatividad en dos marcas son dos hechos de mercado distintos."""
        self.assertNotEqual(
            anuncio(page_id="p1").content_hash(),
            anuncio(page_id="p2").content_hash(),
        )

    def test_no_depende_del_orden_de_plataformas(self) -> None:
        self.assertEqual(
            anuncio(plataformas=("facebook", "instagram")).content_hash(),
            anuncio(plataformas=("instagram", "facebook")).content_hash(),
        )


class TestDiasActivo(unittest.TestCase):
    def test_usa_fin_si_existe(self) -> None:
        a = anuncio(inicio=date(2026, 1, 1), fin=date(2026, 1, 31))
        self.assertEqual(a.dias_activo(date(2026, 9, 1)), 30)

    def test_usa_hoy_si_sigue_activo(self) -> None:
        a = anuncio(inicio=date(2026, 1, 1))
        self.assertEqual(a.dias_activo(date(2026, 1, 11)), 10)

    def test_nunca_negativo(self) -> None:
        """Un anuncio con inicio futuro (dato sucio de la API) no rompe la mediana."""
        a = anuncio(inicio=date(2027, 1, 1))
        self.assertEqual(a.dias_activo(date(2026, 1, 1)), 0)


class TestParticionar(unittest.TestCase):
    def test_separa_nuevos_de_conocidos(self) -> None:
        a, b = anuncio("a1", copy="uno"), anuncio("a2", copy="dos")
        part = particionar([a, b], {a.content_hash()})
        self.assertEqual([x.ad_id for x in part.nuevos], ["a2"])
        self.assertEqual([x.ad_id for x in part.ya_vistos], ["a1"])

    def test_colapsa_duplicados_dentro_del_lote(self) -> None:
        """Agencias reciclan creatividades: mismo copy, distinto ad_id."""
        part = particionar([anuncio("a1"), anuncio("a2"), anuncio("a3")], set())
        self.assertEqual(len(part.nuevos), 1)
        self.assertEqual(part.duplicados_en_lote, 2)

    def test_ratio_de_ahorro(self) -> None:
        a = anuncio("a1", copy="uno")
        lote = [a, anuncio("a2", copy="dos"), anuncio("a3", copy="dos")]
        part = particionar(lote, {a.content_hash()})
        self.assertEqual(part.total, 3)
        self.assertAlmostEqual(part.ratio_ahorro, 2 / 3)

    def test_corpus_vacio_no_divide_por_cero(self) -> None:
        part = particionar([], set())
        self.assertEqual(part.ratio_ahorro, 0.0)


if __name__ == "__main__":
    unittest.main()
