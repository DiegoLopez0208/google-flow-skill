"""
Eleccion de la URL de contenido, sin red.

Un asset de video responde con la URL del MP4 y ademas la de su miniatura.
Quedarse con la primera bajaba un PNG de 46 KB en lugar del video.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flow_provider import api

VIDEO = "https://flow-content.google/video/11111111-1111-1111-1111-111111111111?Expires=1"
MINIATURA = "https://flow-content.google/image/22222222-2222-2222-2222-222222222222?Expires=1"
IMAGEN = "https://flow-content.google/image/33333333-3333-3333-3333-333333333333?Expires=1"


class EleccionDeUrlTest(unittest.TestCase):
    def test_video_no_agarra_la_miniatura(self):
        # Flow devuelve la miniatura primero: por eso no vale tomar urls[0].
        urls = [MINIATURA, VIDEO]
        self.assertEqual(api.elegir_url(urls, "video"), VIDEO)

    def test_imagen_toma_la_imagen(self):
        self.assertEqual(api.elegir_url([IMAGEN], "image"), IMAGEN)

    def test_sin_tipo_prefiere_el_video(self):
        self.assertEqual(api.elegir_url([MINIATURA, VIDEO], None), VIDEO)

    def test_sin_urls_devuelve_none(self):
        self.assertIsNone(api.elegir_url([], "video"))

    def test_tipo_sin_coincidencia_cae_a_la_primera(self):
        self.assertEqual(api.elegir_url([IMAGEN], "video"), IMAGEN)

    def test_recolecta_todas_las_urls_en_orden(self):
        crudo = ["id", [None, [MINIATURA]], [[VIDEO]], "otro"]
        self.assertEqual(api.buscar_urls_contenido(crudo), [MINIATURA, VIDEO])

    def test_ignora_urls_que_no_son_de_contenido(self):
        crudo = ["https://flow.google.com/asb/token", MINIATURA]
        self.assertEqual(api.buscar_urls_contenido(crudo), [MINIATURA])


if __name__ == "__main__":
    unittest.main()
