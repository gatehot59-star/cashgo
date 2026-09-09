"""
Tests del informe. Dos propiedades no negociables:

1. DETERMINISMO. Dos corridas con los mismos datos producen el mismo informe,
   fila por fila. Sin eso no se puede comparar una auditoria de agosto con una de
   septiembre, que es literalmente el valor recurrente del producto.

2. ESCAPADO. El informe se construye con texto escrito por competidores. Un
   informe generado desde texto de terceros y renderizado por un motor HTML es
   una superficie de inyeccion, aunque el motor sea WeasyPrint.
"""
from __future__ import annotations

import re
import unittest
from datetime import date

from fase0.report import (
    DIAS_PARA_CONSIDERAR_PROBADO,
    construir_informe,
    informe_a_html,
)
from fase0.schemas import AnalisisAnuncio

from .apoyo import anuncio

HOY = date(2026, 9, 6)


def analisis(ad_id: str, angulo: str, formato: str = "imagen", promesa: str = "p") -> AnalisisAnuncio:
    return AnalisisAnuncio(
        ad_id=ad_id, angulo=angulo, hook="oferta_directa", cta="comprar",
        formato=formato, promesa=promesa, publico_sugerido="", confianza=0.8,  # type: ignore[arg-type]
    )


def informe_base(**kw):
    prospecto = [anuncio("p_1", "1001", "mi copy", inicio=date(2026, 8, 1))]
    comp = [
        anuncio("c_1", "2001", "uno", inicio=date(2026, 1, 1)),
        anuncio("c_2", "2001", "dos", inicio=date(2026, 3, 1)),
        anuncio("c_3", "2002", "tres", inicio=date(2026, 8, 20)),
    ]
    an = {
        "p_1": analisis("p_1", "precio"),
        "c_1": analisis("c_1", "urgencia"),
        "c_2": analisis("c_2", "prueba_social"),
        "c_3": analisis("c_3", "urgencia"),
    }
    args = dict(
        prospecto_nombre="Mi Tienda", prospecto_page_id="1001",
        nicho="deco", paises=("ES", "GB"),
        anuncios_prospecto=prospecto, anuncios_competencia=comp,
        analisis=an, rechazos=0, descartados_por_dedup=0, hoy=HOY,
    )
    args.update(kw)
    return construir_informe(**args)  # type: ignore[arg-type]


class TestAgregacion(unittest.TestCase):
    def test_cuenta_angulos_de_la_competencia_solamente(self) -> None:
        inf = informe_base()
        self.assertEqual(dict(inf.distribucion_angulos), {"urgencia": 2, "prueba_social": 1})
        self.assertNotIn("precio", dict(inf.distribucion_angulos))

    def test_el_gap_es_una_resta_de_conjuntos(self) -> None:
        inf = informe_base()
        self.assertEqual(inf.angulos_del_prospecto, ("precio",))
        self.assertEqual(set(inf.angulos_no_explotados), {"urgencia", "prueba_social"})

    def test_no_marca_como_gap_lo_que_el_prospecto_ya_usa(self) -> None:
        comp = [anuncio("c_1", "2001", "uno", inicio=date(2026, 1, 1))]
        inf = informe_base(
            anuncios_competencia=comp,
            analisis={"p_1": analisis("p_1", "urgencia"), "c_1": analisis("c_1", "urgencia")},
        )
        self.assertEqual(inf.angulos_no_explotados, ())

    def test_otro_nunca_es_un_gap_accionable(self) -> None:
        """"Proba el angulo otro" no le sirve a nadie."""
        comp = [anuncio("c_1", "2001", "uno", inicio=date(2026, 1, 1))]
        inf = informe_base(
            anuncios_competencia=comp,
            analisis={"p_1": analisis("p_1", "precio"), "c_1": analisis("c_1", "otro")},
        )
        self.assertNotIn("otro", inf.angulos_no_explotados)

    def test_ordena_competidores_por_mediana_de_dias(self) -> None:
        """Por persistencia, no por volumen: el volumen puede ser una agencia."""
        inf = informe_base()
        self.assertEqual([c.page_id for c in inf.competidores], ["2001", "2002"])

    def test_anuncio_sin_analisis_no_cuenta_como_angulo(self) -> None:
        """
        Un anuncio que no se pudo clasificar es NO MEDIDO, no es angulo "otro".
        Meterlo en "otro" seria inventar una senal de mercado.
        """
        comp = [anuncio("c_1", "2001", "uno", inicio=date(2026, 1, 1)),
                anuncio("c_9", "2001", "sin analisis", inicio=date(2026, 1, 1))]
        inf = informe_base(anuncios_competencia=comp,
                           analisis={"c_1": analisis("c_1", "urgencia")})
        self.assertEqual(sum(n for _, n in inf.distribucion_angulos), 1)
        self.assertEqual(inf.anuncios_competencia, 2)   # sigue en el corpus

    def test_formato_ganador_es_el_mas_sostenido_no_el_mas_frecuente(self) -> None:
        comp = [
            anuncio("c_1", "2001", "a", inicio=date(2026, 8, 25)),
            anuncio("c_2", "2001", "b", inicio=date(2026, 8, 25)),
            anuncio("c_3", "2001", "c", inicio=date(2026, 8, 25)),
            anuncio("c_4", "2002", "d", inicio=date(2026, 1, 1)),
        ]
        an = {
            "c_1": analisis("c_1", "urgencia", "imagen"),
            "c_2": analisis("c_2", "urgencia", "imagen"),
            "c_3": analisis("c_3", "urgencia", "imagen"),
            "c_4": analisis("c_4", "precio", "video"),
        }
        inf = informe_base(anuncios_competencia=comp, analisis=an)
        self.assertEqual(inf.formatos_ganadores[0][0], "video")

    def test_longevos_respetan_el_umbral(self) -> None:
        inf = informe_base()
        for _, _, dias in inf.longevos:
            self.assertGreaterEqual(dias, DIAS_PARA_CONSIDERAR_PROBADO)

    def test_corpus_vacio_no_explota(self) -> None:
        inf = informe_base(anuncios_prospecto=[], anuncios_competencia=[], analisis={})
        self.assertEqual(inf.distribucion_angulos, ())
        self.assertEqual(inf.competidores, ())
        self.assertIn("Sin anuncios clasificados", informe_a_html(inf))


class TestDeterminismo(unittest.TestCase):
    def test_dos_construcciones_dan_lo_mismo(self) -> None:
        a, b = informe_base(), informe_base()
        campos = a.model_dump(exclude={"generado_en"})
        self.assertEqual(campos, b.model_dump(exclude={"generado_en"}))

    def test_el_orden_de_entrada_no_cambia_la_salida(self) -> None:
        """Sin desempate estable, dos corridas iguales dan informes incomparables."""
        comp = [
            anuncio("c_1", "2001", "uno", inicio=date(2026, 1, 1)),
            anuncio("c_2", "2002", "dos", inicio=date(2026, 1, 1)),
        ]
        an = {"c_1": analisis("c_1", "urgencia"), "c_2": analisis("c_2", "precio")}
        i1 = informe_base(anuncios_competencia=comp, analisis=an)
        i2 = informe_base(anuncios_competencia=list(reversed(comp)), analisis=an)
        self.assertEqual(
            [c.page_id for c in i1.competidores],
            [c.page_id for c in i2.competidores],
        )
        self.assertEqual(i1.distribucion_angulos, i2.distribucion_angulos)


class TestEscapado(unittest.TestCase):
    HOSTIL = '<script>alert(1)</script>" onload="x'

    def test_escapa_el_nombre_del_prospecto(self) -> None:
        html = informe_a_html(informe_base(prospecto_nombre=self.HOSTIL))
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_escapa_el_nombre_del_competidor(self) -> None:
        comp = [anuncio("c_1", "2001", "uno", inicio=date(2026, 1, 1))
                .model_copy(update={"page_name": self.HOSTIL})]
        html = informe_a_html(informe_base(
            anuncios_competencia=comp, analisis={"c_1": analisis("c_1", "urgencia")}))
        self.assertNotIn("<script>", html)

    def test_escapa_la_promesa_que_salio_del_modelo(self) -> None:
        comp = [anuncio("c_1", "2001", "uno", inicio=date(2026, 1, 1))]
        html = informe_a_html(informe_base(
            anuncios_competencia=comp,
            analisis={"c_1": analisis("c_1", "urgencia", promesa=self.HOSTIL)}))
        self.assertNotIn("<script>", html)

    def test_escapa_la_narrativa(self) -> None:
        html = informe_a_html(informe_base(narrativa=self.HOSTIL))
        self.assertNotIn("<script>", html)

    def test_no_queda_ningun_script_en_todo_el_documento(self) -> None:
        """
        CONTROL POSITIVO: barrido del documento entero, no campo por campo.

        DEFECTO PROPIO EN ESTE TEST (2026-09-06): la primera version afirmaba
        `assertNotIn("onload=", html)` y dio ROJO. El codigo estaba BIEN: el
        escapado convierte el payload en `onload=&quot;x`, que es inerte porque la
        comilla no puede cerrar el atributo. La assertion no distinguia
        `onload=&quot;` (inofensivo) de `onload="` (ataque real), asi que medi la
        presencia de un substring en vez de la propiedad que me importaba.
        Es el mismo error que E-01 a escala de test: el experimento estaba bien
        corrido sobre el sujeto equivocado.
        """
        comp = [anuncio("c_1", "2001", self.HOSTIL, inicio=date(2026, 1, 1))
                .model_copy(update={"page_name": self.HOSTIL})]
        html = informe_a_html(informe_base(
            prospecto_nombre=self.HOSTIL, nicho=self.HOSTIL, narrativa=self.HOSTIL,
            anuncios_competencia=comp,
            analisis={"c_1": analisis("c_1", "urgencia", promesa=self.HOSTIL)}))
        self.assertEqual(re.findall(r"<script", html, re.IGNORECASE), [])
        self.assertNotIn('onload="', html)      # con comilla real: eso seria el ataque
        self.assertIn("onload=&quot;", html)     # inerte: la comilla esta escapada


class TestContenidoDelHtml(unittest.TestCase):
    def test_declara_que_no_hay_datos_de_gasto(self) -> None:
        """
        La pagina de metodologia es parte del producto, no un disclaimer legal:
        es lo que impide que un cliente crea que le vamos a decir cuanto gasta su
        competencia. Meta no publica eso para anuncios comerciales.
        """
        html = informe_a_html(informe_base())
        self.assertIn("no publica", html)
        self.assertIn("cuanto gasta", html)

    def test_declara_el_limite_geografico_del_dsa(self) -> None:
        html = informe_a_html(informe_base())
        self.assertIn("Digital Services Act", html)
        self.assertIn("no aparece aca", html)

    def test_declara_que_la_longevidad_es_un_supuesto(self) -> None:
        html = informe_a_html(informe_base())
        self.assertIn("es un supuesto", html)

    def test_expone_la_trazabilidad_de_la_corrida(self) -> None:
        html = informe_a_html(informe_base(rechazos=7, descartados_por_dedup=99))
        self.assertIn("99 descartados por deduplicacion", html)
        self.assertIn("7 descartados por no pasar", html)


if __name__ == "__main__":
    unittest.main()
