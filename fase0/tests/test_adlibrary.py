"""
Tests del cliente de ads_archive.

El guard mas importante de este archivo es el de alcance comercial: pedir 'US' no
es un error de red, es pedirle a la API un dato que por diseno no tiene. Si eso
no falla fuerte, alguien va a interpretar una lista vacia como "el competidor no
anuncia" y va a escribir eso en un informe que se cobra.
"""
from __future__ import annotations

import unittest
from datetime import date

from fase0 import config
from fase0.adlibrary import (
    AdsArchiveClient,
    AlcanceComercialError,
    PresupuestoDeLlamadasAgotado,
    PresupuestoLlamadas,
    RateLimitError,
    lotes,
)

from .apoyo import transporte_paginas, transporte_que_falla

FILA_OK = {
    "id": "ad1", "page_id": "p1", "page_name": "Marca",
    "ad_creative_bodies": ["copy"],
    "ad_delivery_start_time": "2026-06-01T00:00:00+0000",
    "publisher_platforms": ["facebook"],
}


def cliente(transporte, paises=("ES",), **kw):
    return AdsArchiveClient("tok", transporte, paises=paises, **kw)


class TestAlcanceComercial(unittest.TestCase):
    def test_rechaza_paises_sin_cobertura_comercial(self) -> None:
        """CONTROL POSITIVO: este guard TIENE que dar rojo con US."""
        for pais in ("US", "AR", "BR", "MX", "CA"):
            with self.subTest(pais=pais), self.assertRaises(AlcanceComercialError):
                cliente(transporte_paginas([{"data": []}]), paises=(pais,))

    def test_acepta_ue_y_uk(self) -> None:
        for pais in ("ES", "DE", "FR", "GB", "NO"):
            with self.subTest(pais=pais):
                cliente(transporte_paginas([{"data": []}]), paises=(pais,))

    def test_rechaza_lista_vacia(self) -> None:
        with self.assertRaises(AlcanceComercialError):
            cliente(transporte_paginas([{"data": []}]), paises=())

    def test_rechaza_mezcla_con_uno_invalido(self) -> None:
        """Un solo pais fuera de alcance invalida el pedido entero, no se filtra en silencio."""
        with self.assertRaises(AlcanceComercialError):
            cliente(transporte_paginas([{"data": []}]), paises=("ES", "US"))


class TestParseoYDescartes(unittest.TestCase):
    def test_descarta_filas_sin_fecha_de_inicio(self) -> None:
        """Sin inicio no hay senal de longevidad, que es el unico proxy de exito."""
        t = transporte_paginas([{"data": [FILA_OK, {"id": "x", "page_id": "p1"}]}])
        ads = list(cliente(t).anuncios_de(["p1"]))
        self.assertEqual([a.ad_id for a in ads], ["ad1"])

    def test_descarta_filas_sin_ids(self) -> None:
        rota = {**FILA_OK, "id": "", "page_id": ""}
        t = transporte_paginas([{"data": [rota, FILA_OK]}])
        self.assertEqual(len(list(cliente(t).anuncios_de(["p1"]))), 1)

    def test_parsea_fecha_solo_dia(self) -> None:
        fila = {**FILA_OK, "ad_delivery_start_time": "2026-06-01"}
        ads = list(cliente(transporte_paginas([{"data": [fila]}])).anuncios_de(["p1"]))
        self.assertEqual(ads[0].inicio, date(2026, 6, 1))

    def test_activo_si_no_hay_fecha_de_fin(self) -> None:
        ads = list(cliente(transporte_paginas([{"data": [FILA_OK]}])).anuncios_de(["p1"]))
        self.assertTrue(ads[0].esta_activo)


class TestPaginacion(unittest.TestCase):
    def test_sigue_el_cursor_after(self) -> None:
        p1 = {"data": [FILA_OK],
              "paging": {"cursors": {"after": "C2"}, "next": "https://x"}}
        p2 = {"data": [{**FILA_OK, "id": "ad2"}], "paging": {"cursors": {}}}
        ads = list(cliente(transporte_paginas([p1, p2])).anuncios_de(["p1"]))
        self.assertEqual([a.ad_id for a in ads], ["ad1", "ad2"])

    def test_para_sin_next_aunque_haya_cursor(self) -> None:
        """Meta devuelve `after` incluso en la ultima pagina: hay que mirar `next`."""
        p1 = {"data": [FILA_OK], "paging": {"cursors": {"after": "C2"}}}
        c = cliente(transporte_paginas([p1]))
        list(c.anuncios_de(["p1"]))
        self.assertEqual(c.llamadas_hechas, 1)

    def test_tope_de_paginas_evita_bucle_infinito(self) -> None:
        """Un cursor mal apuntado no debe comerse el rate limit entero."""
        infinita = {"data": [FILA_OK],
                    "paging": {"cursors": {"after": "SIEMPRE"}, "next": "https://x"}}
        c = cliente(transporte_paginas([infinita]))
        list(c.anuncios_de(["p1"], max_paginas_por_lote=3))
        self.assertEqual(c.llamadas_hechas, 3)

    def test_no_repite_el_mismo_ad_id(self) -> None:
        p = {"data": [FILA_OK], "paging": {"cursors": {"after": "C"}, "next": "https://x"}}
        ads = list(cliente(transporte_paginas([p])).anuncios_de(["p1"], max_paginas_por_lote=3))
        self.assertEqual(len(ads), 1)


class TestBatchDePageIds(unittest.TestCase):
    def test_lotes_de_diez(self) -> None:
        self.assertEqual(
            list(lotes([str(i) for i in range(25)], config.MAX_PAGE_IDS_POR_LLAMADA)),
            [[str(i) for i in range(0, 10)],
             [str(i) for i in range(10, 20)],
             [str(i) for i in range(20, 25)]],
        )

    def test_lotes_rechaza_tamano_invalido(self) -> None:
        with self.assertRaises(ValueError):
            list(lotes(["a"], 0))

    def test_veinticinco_paginas_son_tres_llamadas(self) -> None:
        """La palanca de eficiencia: 25 marcas en 3 llamadas, no en 25."""
        c = cliente(transporte_paginas([{"data": [], "paging": {}}]))
        list(c.anuncios_de([str(i) for i in range(25)]))
        self.assertEqual(c.llamadas_hechas, 3)


class TestRateLimit(unittest.TestCase):
    def test_reintenta_con_backoff_en_613(self) -> None:
        esperas: list[float] = []
        t = transporte_que_falla(3, {"data": [FILA_OK], "paging": {}})
        c = cliente(t, dormir=esperas.append)
        ads = list(c.anuncios_de(["p1"]))
        self.assertEqual(len(ads), 1)
        self.assertEqual(c.reintentos_613, 3)
        self.assertEqual(esperas, [4.0, 8.0, 16.0])

    def test_se_rinde_despues_del_maximo_de_intentos(self) -> None:
        """
        CONTROL POSITIVO: el backoff no puede ser infinito.

        Este test cazo un defecto real: `reintentos_613` se incrementaba tambien
        para el 613 final que hace abandonar, asi que reportaba 6 reintentos
        habiendo dormido 5 veces. Una metrica que no coincidia con su fenomeno.
        """
        t = transporte_que_falla(99, {"data": []})
        c = cliente(t, dormir=lambda _s: None)
        with self.assertRaises(RateLimitError):
            list(c.anuncios_de(["p1"]))
        self.assertEqual(c.reintentos_613, config.BACKOFF_MAX_INTENTOS)

    def test_backoff_tiene_techo(self) -> None:
        esperas: list[float] = []
        c = cliente(transporte_que_falla(99, {"data": []}), dormir=esperas.append)
        with self.assertRaises(RateLimitError):
            list(c.anuncios_de(["p1"]))
        self.assertTrue(all(e <= config.BACKOFF_MAX_SEG for e in esperas))

    def test_presupuesto_propio_corta_antes_que_meta(self) -> None:
        reloj = {"t": 0.0}
        pres = PresupuestoLlamadas(techo_por_hora=3, reloj=lambda: reloj["t"])
        infinita = {"data": [FILA_OK],
                    "paging": {"cursors": {"after": "S"}, "next": "https://x"}}
        c = cliente(transporte_paginas([infinita]), presupuesto=pres)
        with self.assertRaises(PresupuestoDeLlamadasAgotado):
            list(c.anuncios_de(["p1"], max_paginas_por_lote=99))
        self.assertEqual(pres.usadas, 3)

    def test_la_ventana_se_desliza(self) -> None:
        reloj = {"t": 0.0}
        pres = PresupuestoLlamadas(techo_por_hora=2, reloj=lambda: reloj["t"])
        pres.registrar()
        pres.registrar()
        with self.assertRaises(PresupuestoDeLlamadasAgotado):
            pres.registrar()
        reloj["t"] = 3601.0
        pres.registrar()          # una hora despues vuelve a haber cupo
        self.assertEqual(pres.usadas, 1)


if __name__ == "__main__":
    unittest.main()
