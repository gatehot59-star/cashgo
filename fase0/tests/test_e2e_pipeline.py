"""
End to end del pipeline completo contra el fixture, sin red.

El test mas importante del archivo es `test_segunda_corrida_no_paga_tokens`: es la
verificacion de que el 88% de ahorro del modelo de costo existe en el codigo y no
solo en la planilla. Sin ese test, el numero del modelo es una afirmacion.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from fase0 import config
from fase0.adlibrary import AdsArchiveClient
from fase0.cognitive import Analizador
from fase0.pipeline import _completion_fixture, _transporte_fixture, correr_auditoria
from fase0.report import informe_a_html
from fase0.store import Store

from .apoyo import FIXTURES


def armar(store: Store):
    cliente = AdsArchiveClient(
        "tok",
        _transporte_fixture(str(FIXTURES / "ads_archive_sample.json")),
        paises=("ES", "DE", "FR", "IT", "NL", "GB"),
    )
    brief = json.loads((FIXTURES / "brief_ejemplo.json").read_text(encoding="utf-8"))
    return correr_auditoria(
        store=store,
        cliente=cliente,
        analizador=Analizador(_completion_fixture()),
        prospecto_page_id=brief["prospecto_page_id"],
        prospecto_nombre=brief["prospecto_nombre"],
        competidores_page_ids=brief["competidores_page_ids"],
        nicho=brief["nicho"],
        paises=tuple(brief["paises"]),
    )


class TestPrimeraCorrida(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Store(":memory:")
        self.res = armar(self.store)

    def tearDown(self) -> None:
        self.store.close()

    def test_trae_el_corpus_y_descarta_la_fila_rota(self) -> None:
        """El fixture tiene 24 filas: una sin fecha de inicio se descarta."""
        self.assertEqual(self.res.metricas.anuncios_traidos, 23)

    def test_colapsa_el_duplicado_del_fixture(self) -> None:
        self.assertEqual(self.res.metricas.duplicados_en_lote, 1)

    def test_pagina_con_dos_llamadas(self) -> None:
        """5 page_ids entran en un solo batch de 10; el fixture tiene 2 paginas."""
        self.assertEqual(self.res.metricas.llamadas_api, 2)

    def test_un_solo_lote_al_modelo(self) -> None:
        self.assertLessEqual(self.res.metricas.anuncios_nuevos, config.ANUNCIOS_POR_LOTE)
        self.assertEqual(self.res.metricas.lotes_al_modelo, 1)

    def test_el_duplicado_igual_recibe_su_analisis(self) -> None:
        """
        22 anuncios fueron al modelo y hay 23 analisis. No es un error de suma: el
        duplicado intra-lote no se clasifica de nuevo pero SI recibe el analisis de
        su creatividad por reproyeccion hash -> ad_id. Ese +1 es el bug que el test
        de determinismo entre corridas encontro.
        """
        self.assertEqual(self.res.metricas.anuncios_nuevos, 22)
        self.assertEqual(self.res.metricas.analisis_validos, 23)

    def test_separa_prospecto_de_competencia(self) -> None:
        inf = self.res.informe
        self.assertEqual(inf.anuncios_prospecto, 3)
        self.assertEqual(inf.anuncios_competencia + inf.anuncios_prospecto, 23)

    def test_encuentra_al_menos_un_gap(self) -> None:
        self.assertGreater(len(self.res.informe.angulos_no_explotados), 0)

    def test_el_informe_renderiza(self) -> None:
        html = informe_a_html(self.res.informe)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Mi Tienda DTC", html)

    def test_deja_audit_log(self) -> None:
        eventos = [e["evento"] for e in self.store.eventos()]
        self.assertIn("corrida_inicio", eventos)
        self.assertIn("corrida_fin", eventos)

    def test_el_audit_log_registra_el_hash_del_prefijo(self) -> None:
        """Trazabilidad: que prompt exacto produjo estos analisis."""
        inicio = next(e for e in self.store.eventos() if e["evento"] == "corrida_inicio")
        payload = json.loads(str(inicio["payload"]))
        self.assertEqual(payload["prefijo_sha256"], self.res.metricas.prefijo_sha256)
        self.assertEqual(payload["modelo"], config.MODELO_FLASH)

    def test_la_inyeccion_del_fixture_no_produjo_un_angulo_invalido(self) -> None:
        """
        El fixture trae un anuncio con una inyeccion de prompt. Cualquiera sea la
        clasificacion que reciba, tiene que caer dentro de la taxonomia cerrada.
        """
        from fase0.report import TODOS_LOS_ANGULOS
        angulos = {a for a, _ in self.res.informe.distribucion_angulos}
        self.assertTrue(angulos <= set(TODOS_LOS_ANGULOS) | {"otro"})

    def test_neutraliza_la_inyeccion_del_fixture_en_el_entregable(self) -> None:
        """
        El fixture trae un anuncio con inyeccion de prompt y una URL maliciosa.
        En el PDF que ve el cliente no puede quedar ni ejecutable ni navegable.

        Dos capas distintas y las dos hacen falta: `sin_urls` saca el dominio del
        texto libre, y `html.escape` impide que cualquier cosa se ejecute.
        """
        html = informe_a_html(self.res.informe)
        self.assertNotIn("malicioso.example", html)
        self.assertIn("[enlace]", html)
        self.assertNotIn("<script", html)
        self.assertNotIn("&quot;>", html)


class TestSegundaCorrida(unittest.TestCase):
    def test_segunda_corrida_no_paga_tokens(self) -> None:
        """
        LA PROPIEDAD QUE SOSTIENE EL MODELO DE COSTO.

        Mismo corpus, base persistida: la segunda corrida no debe mandar un solo
        anuncio al modelo. Si este test se pone en verde por casualidad y despues
        alguien mete la fecha en el content_hash, vuelve a rojo.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "t.sqlite3")
            with Store(db) as s1:
                r1 = armar(s1)
            with Store(db) as s2:
                r2 = armar(s2)

        self.assertGreater(r1.metricas.anuncios_nuevos, 0)
        self.assertEqual(r2.metricas.anuncios_nuevos, 0)
        self.assertEqual(r2.metricas.lotes_al_modelo, 0)
        self.assertGreater(r2.metricas.ratio_dedup, 0.95)

    def test_la_segunda_corrida_produce_el_mismo_informe(self) -> None:
        """
        El dedup no puede degradar el entregable: reusa el analisis persistido.

        ESTE TEST CAZO EL BUG MAS CARO DE LA FASE 0 (2026-09-06): los analisis se
        indexaban por ad_id, asi que el duplicado intra-lote quedaba sin analisis
        en la primera corrida y con analisis en la segunda. Dos informes distintos
        para el mismo corpus, en un producto cuyo unico valor recurrente es poder
        comparar agosto con septiembre. Y era invisible en una sola corrida.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "t.sqlite3")
            with Store(db) as s1:
                r1 = armar(s1)
            with Store(db) as s2:
                r2 = armar(s2)

        excluir = {"generado_en", "rechazos", "anuncios_descartados_por_dedup"}
        self.assertEqual(
            r1.informe.model_dump(exclude=excluir),
            r2.informe.model_dump(exclude=excluir),
        )


class TestPdf(unittest.TestCase):
    def test_genera_un_pdf_no_trivial(self) -> None:
        """
        Verifica que WeasyPrint produce un PDF real y con mas de una pagina.
        Un PDF de 2 KB seria una pagina en blanco con estilos y ningun dato.

        DEFECTO PROPIO EN ESTE TEST (2026-09-06): la primera version contaba
        ocurrencias del literal b"/Type /Page" en los bytes y dio 0. El PDF estaba
        PERFECTO: WeasyPrint comprime los objetos, asi que ese string no aparece
        en crudo. Grepear bytes de un formato binario comprimido es medir el
        envoltorio y concluir sobre el contenido. Se cuenta con un parser.
        """
        import tempfile

        from fase0.report import escribir_pdf

        with Store(":memory:") as store:
            res = armar(store)
            with tempfile.TemporaryDirectory() as tmp:
                ruta = escribir_pdf(res.informe, Path(tmp) / "a.pdf")
                datos = ruta.read_bytes()

        self.assertTrue(datos.startswith(b"%PDF"))
        self.assertGreater(len(datos), 20_000)

        import io

        from pypdf import PdfReader

        lector = PdfReader(io.BytesIO(datos))
        self.assertGreaterEqual(len(lector.pages), 2)
        texto = "".join(pag.extract_text() or "" for pag in lector.pages)
        # El PDF tiene que contener los datos, no solo el chrome del template.
        self.assertIn("Mi Tienda DTC", texto)
        self.assertIn("Digital Services Act", texto)


class TestConfigGuards(unittest.TestCase):
    def test_regla_9_detecta_la_colision_de_app_id(self) -> None:
        """
        CONTROL POSITIVO de la Regla 9 del ADR-CG-002: si el scraper y el gateway
        de escritura comparten app de Meta, un bloqueo se lleva los dos.
        """
        s = config.Settings(
            token_ads_archive="t", deepseek_api_key="k",
            research_app_id="APP_1", write_app_id="APP_1",
        )
        problemas = s.validar()
        self.assertTrue(any("REGLA 9 VIOLADA" in p for p in problemas))

    def test_apps_distintas_pasan(self) -> None:
        s = config.Settings(
            token_ads_archive="t", deepseek_api_key="k",
            research_app_id="APP_1", write_app_id="APP_2",
        )
        self.assertEqual(s.validar(), [])

    def test_rechaza_paises_fuera_del_dsa(self) -> None:
        s = config.Settings(token_ads_archive="t", deepseek_api_key="k", paises=("US", "AR"))
        self.assertTrue(any("fuera del alcance comercial" in p for p in s.validar()))

    def test_dry_run_no_exige_credenciales(self) -> None:
        s = config.Settings()
        self.assertEqual(s.validar(requiere_red=False), [])
        self.assertTrue(s.validar(requiere_red=True))


if __name__ == "__main__":
    unittest.main()
