#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor automático - Búsqueda de Anubis Octavio Clavijo Valencia
Corre cada 24 horas en GitHub Actions o manualmente en local
"""

import requests
import os
import smtplib
import time
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup

# Carga .env si existe (solo en local, en GitHub usa Secrets)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ==========================================
# CONFIGURACIÓN
# ==========================================

NOMBRES_BUSCAR = [
    "Clavijo",
    "Klavijo",
    "Клавихо",
    "Anubis",
    "Анубис",
    "Valencia",
    "Валенсия",
    "Alkons",
    "Анубис Октавио",
    "Anubis Octavio"
]

URLS_MONITOREAR = [
    {
        "url": "https://200.zona.media",
        "nombre": "Mediazona Base de Datos 200"
    },
    {
        "url": "https://zona.media/article/2026/03/27/perdidas",
        "nombre": "Mediazona Estadísticas"
    }
]

EMAIL_DESTINO = os.environ.get('EMAIL_DESTINO', 'spikeblade@gmail.com')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'es-ES,es;q=0.9,ru;q=0.8,en;q=0.7',
}

# ==========================================
# FUNCIONES
# ==========================================

def obtener_texto_pagina(url, intentos=3):
    """
    Descarga la página y extrae solo el texto visible (sin HTML, scripts ni CSS).
    Reintenta hasta 3 veces si falla.
    """
    for intento in range(1, intentos + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Eliminar scripts y estilos antes de extraer texto
            for tag in soup(['script', 'style', 'meta', 'noscript']):
                tag.decompose()

            return soup.get_text(separator=' ', strip=True)

        except requests.RequestException as e:
            print(f"   Intento {intento}/{intentos} fallido: {e}")
            if intento < intentos:
                time.sleep(5)

    return None


def buscar_en_url(url_info):
    """
    Busca los términos en el texto visible de una URL.
    """
    url = url_info["url"]
    nombre = url_info["nombre"]

    print(f"Revisando: {nombre}")
    print(f"   URL: {url}")

    texto = obtener_texto_pagina(url)

    if texto is None:
        print(f"   ERROR: No se pudo acceder al sitio tras 3 intentos")
        return {
            "sitio": nombre,
            "url": url,
            "encontrado": False,
            "terminos": [],
            "error": "No se pudo acceder al sitio tras 3 intentos",
            "timestamp": utcnow().isoformat()
        }

    texto_lower = texto.lower()
    encontrados = []

    for termino in NOMBRES_BUSCAR:
        if termino.lower() in texto_lower:
            encontrados.append(termino)
            print(f"   *** ENCONTRADO: {termino}")

    if not encontrados:
        print(f"   No se encontraron terminos")

    return {
        "sitio": nombre,
        "url": url,
        "encontrado": len(encontrados) > 0,
        "terminos": encontrados,
        "timestamp": utcnow().isoformat()
    }


def enviar_email_alerta(resultados_positivos):
    """
    Envía email de alerta cuando hay coincidencias.
    Requiere SMTP_USER y SMTP_PASSWORD (en .env local o GitHub Secrets).
    """
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')

    if not smtp_user or not smtp_password:
        print("AVISO: Configura SMTP_USER y SMTP_PASSWORD para recibir alertas por email")
        return False

    mensaje = MIMEMultipart()
    mensaje['From'] = smtp_user
    mensaje['To'] = EMAIL_DESTINO
    mensaje['Subject'] = 'ALERTA - Posible informacion de Anubis encontrada'

    cuerpo = "ALERTA AUTOMATICA - Monitor de busqueda\n\n"
    cuerpo += "Se encontraron terminos relacionados con Anubis Octavio Clavijo Valencia:\n\n"

    for resultado in resultados_positivos:
        cuerpo += f"Sitio: {resultado['sitio']}\n"
        cuerpo += f"URL: {resultado['url']}\n"
        cuerpo += f"Terminos encontrados: {', '.join(resultado['terminos'])}\n"
        cuerpo += f"Fecha (UTC): {resultado['timestamp']}\n"
        cuerpo += "-" * 60 + "\n\n"

    cuerpo += "IMPORTANTE: Revisa manualmente los sitios para confirmar la informacion.\n"
    cuerpo += f"\nAlerta generada el {utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"

    mensaje.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(mensaje)
        print(f"Email enviado a {EMAIL_DESTINO}")
        return True
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False


def guardar_resultados(todos_resultados):
    """
    Guarda un resumen de la ejecucion en resultados.txt
    """
    timestamp = utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    with open('resultados.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("MONITOR - BUSQUEDA DE ANUBIS OCTAVIO CLAVIJO VALENCIA\n")
        f.write("=" * 70 + "\n")
        f.write(f"Fecha ejecucion: {timestamp}\n")
        f.write(f"Email alertas: {EMAIL_DESTINO}\n")
        f.write("=" * 70 + "\n\n")

        for resultado in todos_resultados:
            f.write(f"Sitio: {resultado['sitio']}\n")
            f.write(f"URL: {resultado['url']}\n")

            if 'error' in resultado:
                f.write(f"ERROR: {resultado['error']}\n")
            elif resultado['encontrado']:
                f.write(f"ENCONTRADO: {', '.join(resultado['terminos'])}\n")
            else:
                f.write("No encontrado\n")

            f.write("-" * 70 + "\n\n")

        encontrados = [r for r in todos_resultados if r['encontrado']]
        f.write("\n" + "=" * 70 + "\n")
        f.write("RESUMEN:\n")
        f.write("=" * 70 + "\n")
        f.write(f"Total sitios revisados: {len(todos_resultados)}\n")
        f.write(f"Sitios con resultados: {len(encontrados)}\n")

        if encontrados:
            f.write("\n*** SE ENCONTRARON COINCIDENCIAS - REVISAR MANUALMENTE ***\n")
        else:
            f.write("\nNo se encontraron coincidencias en esta ejecucion\n")

    print(f"\nResultados guardados en resultados.txt")


def main():
    print("=" * 70)
    print("MONITOR AUTOMATICO - BUSQUEDA DE ANUBIS OCTAVIO CLAVIJO VALENCIA")
    print("=" * 70)
    print(f"Inicio: {utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Terminos de busqueda: {len(NOMBRES_BUSCAR)}")
    print(f"Sitios a revisar: {len(URLS_MONITOREAR)}")
    print(f"Email alertas: {EMAIL_DESTINO}")
    print("=" * 70 + "\n")

    todos_resultados = []

    for url_info in URLS_MONITOREAR:
        resultado = buscar_en_url(url_info)
        todos_resultados.append(resultado)
        print()

    guardar_resultados(todos_resultados)

    resultados_positivos = [r for r in todos_resultados if r['encontrado']]

    print("\n" + "=" * 70)
    if resultados_positivos:
        print("*** ALERTA: SE ENCONTRARON COINCIDENCIAS ***")
        enviar_email_alerta(resultados_positivos)
    else:
        print("No se encontraron coincidencias en esta ejecucion")
    print("=" * 70)

    print(f"\nEjecucion completada: {utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")


if __name__ == "__main__":
    main()
