"""
Tests para monitor_github.py
Corre con: pytest test_monitor.py -v
"""

import json
import pytest
import requests as req
from unittest.mock import patch, MagicMock
from monitor_github import (
    buscar_en_url,
    obtener_texto_pagina,
    guardar_resultados,
    extraer_contexto,
    cargar_historial,
    guardar_historial,
    filtrar_nuevos,
    actualizar_historial,
)


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


# ==========================================
# obtener_texto_pagina
# ==========================================

class TestObtenerTextoPagina:
    def test_extrae_texto_visible(self):
        with patch('monitor_github.requests.get') as mock_get:
            mock_get.return_value = MagicMock(status_code=200, text=HTML_CON_NOMBRE)
            texto = obtener_texto_pagina("https://ejemplo.com")

        assert "Clavijo" in texto
        assert "var x = 1" not in texto
        assert "body{}" not in texto

    def test_no_encuentra_nombre_en_script(self):
        with patch('monitor_github.requests.get') as mock_get:
            mock_get.return_value = MagicMock(status_code=200, text=HTML_CON_NOMBRE_EN_SCRIPT)
            texto = obtener_texto_pagina("https://ejemplo.com")

        assert "Clavijo" not in texto

    def test_reintenta_si_falla(self):
        with patch('monitor_github.requests.get', side_effect=req.RequestException("timeout")) as mock_get:
            with patch('time.sleep'):
                resultado = obtener_texto_pagina("https://ejemplo.com", intentos=3)

        assert resultado is None
        assert mock_get.call_count == 3

    def test_retorna_none_si_status_no_es_200(self):
        with patch('monitor_github.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = req.HTTPError("404")
            mock_get.return_value = mock_response
            with patch('time.sleep'):
                resultado = obtener_texto_pagina("https://ejemplo.com", intentos=1)

        assert resultado is None


# ==========================================
# extraer_contexto
# ==========================================

class TestExtraerContexto:
    def test_extrae_texto_alrededor(self):
        texto = "texto antes " + "Clavijo" + " texto despues"
        contexto = extraer_contexto(texto, "Clavijo", ventana=50)

        assert "Clavijo" in contexto
        assert "antes" in contexto
        assert "despues" in contexto

    def test_agrega_puntos_suspensivos_si_recorta(self):
        texto = "A" * 300 + "Clavijo" + "B" * 300
        contexto = extraer_contexto(texto, "Clavijo", ventana=50)

        assert contexto.startswith("...")
        assert contexto.endswith("...")
        assert "Clavijo" in contexto

    def test_sin_puntos_si_es_inicio(self):
        texto = "Clavijo al inicio del texto con mas contenido"
        contexto = extraer_contexto(texto, "Clavijo", ventana=100)

        assert not contexto.startswith("...")

    def test_retorna_vacio_si_no_encuentra(self):
        contexto = extraer_contexto("texto sin el termino", "Clavijo")
        assert contexto == ""

    def test_insensible_a_mayusculas(self):
        contexto = extraer_contexto("CLAVIJO en mayusculas", "Clavijo")
        assert "CLAVIJO" in contexto


# ==========================================
# buscar_en_url
# ==========================================

class TestBuscarEnUrl:
    def test_encuentra_termino_e_incluye_contexto(self):
        url_info = {"url": "https://ejemplo.com", "nombre": "Sitio Test"}

        with patch('monitor_github.obtener_texto_pagina', return_value="texto antes Clavijo texto despues"):
            resultado = buscar_en_url(url_info)

        assert resultado["encontrado"] is True
        assert "Clavijo" in resultado["terminos"]
        assert "Clavijo" in resultado["contextos"]
        assert "Clavijo" in resultado["contextos"]["Clavijo"]

    def test_no_encuentra_termino_ausente(self):
        url_info = {"url": "https://ejemplo.com", "nombre": "Sitio Test"}

        with patch('monitor_github.obtener_texto_pagina', return_value="Ivan Petrov soldado"):
            resultado = buscar_en_url(url_info)

        assert resultado["encontrado"] is False
        assert resultado["terminos"] == []
        assert resultado["contextos"] == {}

    def test_busqueda_insensible_a_mayusculas(self):
        url_info = {"url": "https://ejemplo.com", "nombre": "Sitio Test"}

        with patch('monitor_github.obtener_texto_pagina', return_value="CLAVIJO en mayusculas"):
            resultado = buscar_en_url(url_info)

        assert resultado["encontrado"] is True

    def test_maneja_sitio_inaccesible(self):
        url_info = {"url": "https://ejemplo.com", "nombre": "Sitio Test"}

        with patch('monitor_github.obtener_texto_pagina', return_value=None):
            resultado = buscar_en_url(url_info)

        assert resultado["encontrado"] is False
        assert "error" in resultado

    def test_encuentra_multiples_terminos_con_contexto(self):
        url_info = {"url": "https://ejemplo.com", "nombre": "Sitio Test"}
        texto = "Anubis Octavio Clavijo Valencia soldado registrado"

        with patch('monitor_github.obtener_texto_pagina', return_value=texto):
            resultado = buscar_en_url(url_info)

        assert resultado["encontrado"] is True
        assert len(resultado["terminos"]) >= 3
        assert len(resultado["contextos"]) == len(resultado["terminos"])

    def test_encuentra_terminos_en_ruso(self):
        url_info = {"url": "https://ejemplo.com", "nombre": "Sitio Test"}

        with patch('monitor_github.obtener_texto_pagina', return_value="Клавихо боец"):
            resultado = buscar_en_url(url_info)

        assert resultado["encontrado"] is True
        assert "Клавихо" in resultado["terminos"]


# ==========================================
# historial
# ==========================================

class TestHistorial:
    def test_historial_vacio_si_no_existe_archivo(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        historial = cargar_historial()
        assert historial == set()

    def test_guarda_y_carga_historial(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        historial = {("Clavijo", "https://x.com"), ("Anubis", "https://y.com")}
        guardar_historial(historial)
        cargado = cargar_historial()
        assert cargado == historial

    def test_filtrar_nuevos_excluye_vistos(self):
        historial = {("Clavijo", "https://x.com")}
        resultados = [{
            "sitio": "Test", "url": "https://x.com",
            "encontrado": True, "terminos": ["Clavijo"],
            "contextos": {"Clavijo": "...texto..."}, "timestamp": "2026-01-01"
        }]
        nuevos = filtrar_nuevos(resultados, historial)
        assert nuevos == []

    def test_filtrar_nuevos_incluye_no_vistos(self):
        historial = set()
        resultados = [{
            "sitio": "Test", "url": "https://x.com",
            "encontrado": True, "terminos": ["Clavijo"],
            "contextos": {"Clavijo": "...texto..."}, "timestamp": "2026-01-01"
        }]
        nuevos = filtrar_nuevos(resultados, historial)
        assert len(nuevos) == 1
        assert "Clavijo" in nuevos[0]["terminos_nuevos"]

    def test_filtrar_nuevos_separa_terminos_parciales(self):
        # Clavijo ya visto, Anubis es nuevo
        historial = {("Clavijo", "https://x.com")}
        resultados = [{
            "sitio": "Test", "url": "https://x.com",
            "encontrado": True, "terminos": ["Clavijo", "Anubis"],
            "contextos": {}, "timestamp": "2026-01-01"
        }]
        nuevos = filtrar_nuevos(resultados, historial)
        assert len(nuevos) == 1
        assert nuevos[0]["terminos_nuevos"] == ["Anubis"]

    def test_actualizar_historial(self):
        historial = set()
        resultados = [{
            "url": "https://x.com", "terminos": ["Clavijo", "Anubis"],
            "encontrado": True, "sitio": "Test", "contextos": {}
        }]
        actualizar_historial(historial, resultados)
        assert ("Clavijo", "https://x.com") in historial
        assert ("Anubis", "https://x.com") in historial


# ==========================================
# guardar_resultados
# ==========================================

class TestGuardarResultados:
    def test_crea_archivo_resultados(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        resultados = [{
            "sitio": "Test", "url": "https://x.com", "encontrado": False,
            "terminos": [], "contextos": {}, "timestamp": "2026-01-01T00:00:00"
        }]
        guardar_resultados(resultados, [])
        assert (tmp_path / "resultados.txt").exists()

    def test_resumen_indica_hallazgos_nuevos(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        resultados = [{
            "sitio": "Test", "url": "https://x.com", "encontrado": True,
            "terminos": ["Clavijo"], "contextos": {"Clavijo": "ctx"},
            "timestamp": "2026-01-01T00:00:00"
        }]
        nuevos = [{"terminos_nuevos": ["Clavijo"]}]
        guardar_resultados(resultados, nuevos)
        contenido = (tmp_path / "resultados.txt").read_text(encoding='utf-8')
        assert "HALLAZGOS NUEVOS" in contenido

    def test_resumen_indica_ya_reportado(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        resultados = [{
            "sitio": "Test", "url": "https://x.com", "encontrado": True,
            "terminos": ["Clavijo"], "contextos": {"Clavijo": "ctx"},
            "timestamp": "2026-01-01T00:00:00"
        }]
        guardar_resultados(resultados, [])  # sin nuevos
        contenido = (tmp_path / "resultados.txt").read_text(encoding='utf-8')
        assert "ya reportadas" in contenido
