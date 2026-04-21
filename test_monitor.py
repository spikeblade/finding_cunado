"""
Tests para monitor_github.py
Corre con: pytest test_monitor.py -v
"""

import pytest
from unittest.mock import patch, MagicMock
from monitor_github import buscar_en_url, obtener_texto_pagina, guardar_resultados


HTML_CON_NOMBRE = """
<html>
<head><script>var x = 1;</script><style>body{}</style></head>
<body>
  <h1>Lista de bajas</h1>
  <p>Clavijo, soldado de infanteria, fallecido el 01-01-2024</p>
</body>
</html>
"""

HTML_SIN_NOMBRE = """
<html>
<body>
  <h1>Lista de bajas</h1>
  <p>Ivanov, soldado, fallecido el 01-01-2024</p>
</body>
</html>
"""

HTML_CON_NOMBRE_EN_SCRIPT = """
<html>
<head><script>var data = "Clavijo en script";</script></head>
<body><p>No hay coincidencias en el texto visible</p></body>
</html>
"""


class TestObtenerTextoPagina:
    def test_extrae_texto_visible(self):
        """Extrae texto del body ignorando scripts y estilos"""
        with patch('requests.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                text=HTML_CON_NOMBRE
            )
            texto = obtener_texto_pagina("https://ejemplo.com")

        assert "Clavijo" in texto
        assert "var x = 1" not in texto  # script eliminado
        assert "body{}" not in texto     # style eliminado

    def test_no_encuentra_nombre_en_script(self):
        """No debe encontrar nombres que solo aparecen dentro de <script>"""
        with patch('requests.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                text=HTML_CON_NOMBRE_EN_SCRIPT
            )
            texto = obtener_texto_pagina("https://ejemplo.com")

        assert "Clavijo" not in texto

    def test_reintenta_si_falla(self):
        """Reintenta 3 veces antes de rendirse"""
        import requests as req
        with patch('monitor_github.requests.get', side_effect=req.RequestException("timeout")) as mock_get:
            with patch('time.sleep'):
                resultado = obtener_texto_pagina("https://ejemplo.com", intentos=3)

        assert resultado is None
        assert mock_get.call_count == 3

    def test_retorna_none_si_status_no_es_200(self):
        """Retorna None si el servidor responde con error HTTP"""
        import requests as req
        with patch('monitor_github.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = req.HTTPError("404")
            mock_get.return_value = mock_response
            with patch('time.sleep'):
                resultado = obtener_texto_pagina("https://ejemplo.com", intentos=1)

        assert resultado is None


class TestBuscarEnUrl:
    def test_encuentra_termino_en_pagina(self):
        """Detecta correctamente un termino de busqueda"""
        url_info = {"url": "https://ejemplo.com", "nombre": "Sitio Test"}

        with patch('monitor_github.obtener_texto_pagina', return_value="Clavijo estuvo aqui"):
            resultado = buscar_en_url(url_info)

        assert resultado["encontrado"] is True
        assert "Clavijo" in resultado["terminos"]

    def test_no_encuentra_termino_ausente(self):
        """No genera falsos positivos cuando el nombre no esta"""
        url_info = {"url": "https://ejemplo.com", "nombre": "Sitio Test"}

        with patch('monitor_github.obtener_texto_pagina', return_value="Ivan Petrov soldado"):
            resultado = buscar_en_url(url_info)

        assert resultado["encontrado"] is False
        assert resultado["terminos"] == []

    def test_busqueda_insensible_a_mayusculas(self):
        """Encuentra el termino sin importar mayusculas/minusculas"""
        url_info = {"url": "https://ejemplo.com", "nombre": "Sitio Test"}

        with patch('monitor_github.obtener_texto_pagina', return_value="CLAVIJO en mayusculas"):
            resultado = buscar_en_url(url_info)

        assert resultado["encontrado"] is True

    def test_maneja_sitio_inaccesible(self):
        """Retorna error limpio si el sitio no responde"""
        url_info = {"url": "https://ejemplo.com", "nombre": "Sitio Test"}

        with patch('monitor_github.obtener_texto_pagina', return_value=None):
            resultado = buscar_en_url(url_info)

        assert resultado["encontrado"] is False
        assert "error" in resultado

    def test_encuentra_multiples_terminos(self):
        """Detecta varios terminos en la misma pagina"""
        url_info = {"url": "https://ejemplo.com", "nombre": "Sitio Test"}
        texto = "Anubis Octavio Clavijo Valencia soldado"

        with patch('monitor_github.obtener_texto_pagina', return_value=texto):
            resultado = buscar_en_url(url_info)

        assert resultado["encontrado"] is True
        assert len(resultado["terminos"]) >= 3

    def test_encuentra_terminos_en_ruso(self):
        """Detecta terminos en alfabeto cirilico"""
        url_info = {"url": "https://ejemplo.com", "nombre": "Sitio Test"}

        with patch('monitor_github.obtener_texto_pagina', return_value="Клавихо боец"):
            resultado = buscar_en_url(url_info)

        assert resultado["encontrado"] is True
        assert "Клавихо" in resultado["terminos"]


class TestGuardarResultados:
    def test_crea_archivo_resultados(self, tmp_path, monkeypatch):
        """Genera el archivo resultados.txt correctamente"""
        monkeypatch.chdir(tmp_path)
        resultados = [
            {"sitio": "Test", "url": "https://x.com", "encontrado": False,
             "terminos": [], "timestamp": "2026-01-01T00:00:00"}
        ]
        guardar_resultados(resultados)
        assert (tmp_path / "resultados.txt").exists()

    def test_resumen_con_coincidencias(self, tmp_path, monkeypatch):
        """Marca claramente cuando hay coincidencias"""
        monkeypatch.chdir(tmp_path)
        resultados = [
            {"sitio": "Test", "url": "https://x.com", "encontrado": True,
             "terminos": ["Clavijo"], "timestamp": "2026-01-01T00:00:00"}
        ]
        guardar_resultados(resultados)
        contenido = (tmp_path / "resultados.txt").read_text(encoding='utf-8')
        assert "COINCIDENCIAS" in contenido
